"""Run isolation, fencing and explicit recovery using synthetic local inputs."""
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
try:
    module = importlib.import_module('workflow.ledger')
except ModuleNotFoundError:
    module = None
GOOD = {'matching_skills':['React'], 'missing_skills':['TypeScript'],
        'work_authorization':None, 'needs_review':True}


class RunRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name); self.workspace = self.base/'worker'
        self.candidate = self.base/'candidate.json'
        self.requirements = self.base/'requirements.json'
        self.candidate.write_text(json.dumps({'skills':['React'],'work_authorization':None}))
        self.requirements.write_text(json.dumps({'required_skills':['React','TypeScript']}))

    def ledger(self):
        self.assertIsNotNone(module, 'Run ledger has not been implemented')
        return module.Ledger(self.base/'state', self.workspace)

    def create(self, ledger, job='role-1'):
        return ledger.create(job, self.candidate, self.requirements)

    def output(self, attempt, value=GOOD):
        Path(attempt['output_path']).write_text(json.dumps(value))

    def test_unique_attempt_paths_and_current_result(self):
        ledger = self.ledger(); run = self.create(ledger); a = ledger.claim(run['run_id'])
        self.output(a); result = ledger.complete(run['run_id'], a['attempt_id'])
        self.assertEqual(result['state'],'review_required')
        self.assertTrue(result['validation']['validation_passed'])
        self.assertFalse(result['action_authorized'])
        second = self.create(ledger); b = ledger.claim(second['run_id'])
        self.assertNotEqual(a['output_path'], b['output_path'])
        self.assertEqual(ledger.current('role-1')['run_id'],second['run_id'])
        self.assertIsNone(ledger.current('role-1')['validation'])

    def test_late_old_run_cannot_replace_newer_result(self):
        ledger = self.ledger(); old = self.create(ledger); a = ledger.claim(old['run_id'])
        new = self.create(ledger); b = ledger.claim(new['run_id'])
        self.output(b); ledger.complete(new['run_id'],b['attempt_id'])
        self.output(a, {**GOOD,'missing_skills':[]})
        with self.assertRaises(module.RunError):ledger.complete(old['run_id'],a['attempt_id'])
        current = ledger.current('role-1')
        self.assertEqual(current['run_id'],new['run_id'])
        self.assertTrue(current['validation']['validation_passed'])

    def test_restart_never_automatically_resumes_claimed_work(self):
        ledger = self.ledger(); run = self.create(ledger); a = ledger.claim(run['run_id'])
        restarted = self.ledger()
        self.assertEqual(restarted.status(run['run_id'])['state'],'running')
        with self.assertRaises(module.RunError):restarted.claim(run['run_id'])
        with self.assertRaises(module.RunError):restarted.recover(run['run_id'],'resume','not interrupted')
        restarted.interrupt(run['run_id'],a['attempt_id'],'operator confirmed worker stopped')
        self.assertEqual(self.ledger().status(run['run_id'])['state'],'interrupted')
        with self.assertRaises(module.RunError):self.ledger().claim(run['run_id'])
        restarted.recover(run['run_id'],'resume','reviewed saved inputs')
        b = restarted.claim(run['run_id']); self.assertNotEqual(a['attempt_id'],b['attempt_id'])
        self.assertNotEqual(a['output_path'],b['output_path'])
        self.output(a)
        with self.assertRaises(module.RunError):restarted.complete(run['run_id'],a['attempt_id'])
        self.output(b); self.assertTrue(restarted.complete(run['run_id'],b['attempt_id'])['validation']['validation_passed'])
        self.assertIn('recovery_resume',[x['event'] for x in restarted.events(run['run_id'])])

    def test_cancel_and_empty_or_replayed_decisions_fail_closed(self):
        ledger = self.ledger(); run = self.create(ledger); a = ledger.claim(run['run_id'])
        ledger.interrupt(run['run_id'],a['attempt_id'],'worker stopped')
        for decision,reason in [('resume',''),('automatic','because')]:
            with self.assertRaises(module.RunError):ledger.recover(run['run_id'],decision,reason)
        ledger.recover(run['run_id'],'cancel','operator cancelled')
        for action in [lambda:ledger.claim(run['run_id']),
                       lambda:ledger.recover(run['run_id'],'resume','replayed click'),
                       lambda:ledger.complete(run['run_id'],a['attempt_id'])]:
            with self.assertRaises(module.RunError):action()
        self.assertEqual(ledger.status(run['run_id'])['state'],'cancelled')

    def test_only_one_concurrent_worker_can_claim(self):
        ledger = self.ledger(); run = self.create(ledger); barrier=threading.Barrier(2)
        def claim():
            local=self.ledger(); barrier.wait()
            try:return local.claim(run['run_id'])['attempt_id']
            except module.RunError:return None
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(lambda _:claim(),range(2)))
        self.assertEqual(sum(x is not None for x in results),1)

    def test_completion_is_once_only_and_snapshot_survives_worker_edits(self):
        ledger=self.ledger(); run=self.create(ledger); a=ledger.claim(run['run_id']);self.output(a)
        raw=Path(a['output_path']).read_bytes();ledger.complete(run['run_id'],a['attempt_id'])
        self.output(a,{**GOOD,'missing_skills':[]})
        with self.assertRaises(module.RunError):ledger.complete(run['run_id'],a['attempt_id'])
        self.assertEqual(ledger.evidence(run['run_id'])['raw'],raw)
        with sqlite3.connect(ledger.db_path) as db:
            with self.assertRaises(sqlite3.IntegrityError):db.execute('UPDATE results SET raw=?',(b'changed',))

    def test_trusted_inputs_are_snapshotted_before_worker_tampering(self):
        ledger=self.ledger();run=self.create(ledger);a=ledger.claim(run['run_id'])
        self.candidate.write_text(json.dumps({'skills':['React','TypeScript'],'work_authorization':'yes'}))
        Path(a['request_path']).write_text('{}')
        self.output(a,{**GOOD,'matching_skills':['React','TypeScript'],'missing_skills':[],
                       'work_authorization':'yes','needs_review':False})
        r=ledger.complete(run['run_id'],a['attempt_id'])
        self.assertEqual(r['state'],'rejected')
        self.assertIsNone(r['validation']['expected']['work_authorization'])
        self.assertIn('output.missing_skills_mismatch',r['validation']['errors'])

    def test_stale_recovery_request_cannot_reactivate_superseded_run(self):
        ledger=self.ledger();old=self.create(ledger);a=ledger.claim(old['run_id'])
        ledger.interrupt(old['run_id'],a['attempt_id'],'stopped');new=self.create(ledger)
        with self.assertRaises(module.RunError):ledger.recover(old['run_id'],'resume','stale decision')
        self.assertEqual(ledger.current('role-1')['run_id'],new['run_id'])

    def test_both_recorded_failures_are_retained_and_rejected(self):
        ledger=self.ledger()
        for name in ['final-gateway-output-failed-validation.json','restart-recovery-overwrite.json']:
            run=self.create(ledger,name);a=ledger.claim(run['run_id'])
            raw=(ROOT/'examples/results'/name).read_bytes();Path(a['output_path']).write_bytes(raw)
            r=ledger.complete(run['run_id'],a['attempt_id'])
            self.assertEqual(r['state'],'rejected');self.assertEqual(ledger.evidence(run['run_id'])['raw'],raw)

    def test_parent_symlink_and_oversize_output_never_read_or_promoted(self):
        ledger=self.ledger();run=self.create(ledger);a=ledger.claim(run['run_id'])
        folder=Path(a['output_path']).parent;folder.rename(folder.with_name(folder.name+'-old'))
        outside=self.base/'outside';outside.mkdir();(outside/'result.json').write_text(json.dumps(GOOD))
        folder.symlink_to(outside,target_is_directory=True)
        r=ledger.complete(run['run_id'],a['attempt_id']);self.assertEqual(r['state'],'rejected')
        self.assertIsNone(ledger.evidence(run['run_id'])['raw'])
        run=self.create(ledger);a=ledger.claim(run['run_id']);Path(a['output_path']).write_bytes(b' ' * 65537)
        self.assertEqual(ledger.complete(run['run_id'],a['attempt_id'])['state'],'rejected')

    def test_state_and_trusted_inputs_cannot_be_agent_writable(self):
        ledger=self.ledger();self.workspace.mkdir(exist_ok=True)
        copied=self.workspace/'candidate.json';copied.write_bytes(self.candidate.read_bytes())
        with self.assertRaises(module.RunError):ledger.create('bad',copied,self.requirements)
        with self.assertRaises(module.RunError):module.Ledger(self.workspace/'state',self.workspace)
        self.assertEqual(ledger.db_path.stat().st_mode & 0o777,0o600)
        self.assertEqual(ledger.db_path.parent.stat().st_mode & 0o777,0o700)

    def test_process_death_and_sqlite_rollback_require_explicit_recovery(self):
        ledger=self.ledger();run=self.create(ledger)
        script='from workflow.ledger import Ledger; import json,os,sys; l=Ledger(sys.argv[1],sys.argv[2]); print(json.dumps(l.claim(sys.argv[3])),flush=True); os._exit(17)'
        child=subprocess.run([sys.executable,'-c',script,str(self.base/'state'),str(self.workspace),run['run_id']],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(child.returncode,17);a=json.loads(child.stdout)
        reopened=self.ledger();self.assertEqual(reopened.status(run['run_id'])['state'],'running')
        with self.assertRaises(module.RunError):reopened.claim(run['run_id'])
        crash='import sqlite3,os,sys; d=sqlite3.connect(sys.argv[1]); d.execute("BEGIN IMMEDIATE"); d.execute("UPDATE runs SET state=\'pending\'"); os._exit(19)'
        killed=subprocess.run([sys.executable,'-c',crash,str(ledger.db_path)],cwd=ROOT)
        self.assertEqual(killed.returncode,19)
        self.assertEqual(self.ledger().status(run['run_id'])['state'],'running')
        reopened.interrupt(run['run_id'],a['attempt_id'],'process death verified')
        reopened.recover(run['run_id'],'resume','explicit operator decision')
        self.assertNotEqual(reopened.claim(run['run_id'])['attempt_id'],a['attempt_id'])


    def test_missing_or_wrong_attempt_cannot_interrupt_or_complete(self):
        ledger=self.ledger();run=self.create(ledger);a=ledger.claim(run['run_id']);self.output(a)
        for token in [None,'', 'wrong-attempt']:
            with self.subTest(token=token):
                with self.assertRaises(module.RunError):ledger.interrupt(run['run_id'],token,'wrong worker')
                with self.assertRaises(module.RunError):ledger.complete(run['run_id'],token)
                self.assertEqual(ledger.status(run['run_id'])['state'],'running')

    def test_wrong_workspace_and_corrupt_database_are_not_silently_reused(self):
        ledger=self.ledger()
        with self.assertRaises(module.RunError):module.Ledger(self.base/'state',self.base/'different-worker')
        other=self.base/'corrupt';other.mkdir(mode=0o700)
        p=other/'ledger.sqlite3';p.write_bytes(b'not a database');p.chmod(0o600)
        with self.assertRaises(module.RunError):module.Ledger(other,self.workspace)
        self.assertEqual(p.read_bytes(),b'not a database')

    def test_completion_transaction_rolls_back_if_audit_cannot_be_written(self):
        ledger=self.ledger();run=self.create(ledger);a=ledger.claim(run['run_id']);self.output(a)
        with sqlite3.connect(ledger.db_path) as db:
            db.execute("CREATE TRIGGER fail_completion BEFORE INSERT ON events WHEN NEW.event='completed' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.Error):ledger.complete(run['run_id'],a['attempt_id'])
        self.assertEqual(self.ledger().status(run['run_id'])['state'],'running')
        with self.assertRaises(module.RunError):ledger.evidence(run['run_id'])

    def test_cli_recovery_is_explicit_and_late_completion_fails(self):
        self.ledger()
        prefix=[sys.executable,'-m','workflow','--state-root',str(self.base/'state'),
                '--workspace',str(self.workspace)]
        def call(*args,exit_code=0):
            r=subprocess.run(prefix+list(args),cwd=ROOT,capture_output=True,text=True,timeout=10)
            self.assertEqual(r.returncode,exit_code,r.stderr+' '+r.stdout)
            data=json.loads(r.stdout);self.assertFalse(data['action_authorized']);return data
        run=call('create','--job','cli-role','--candidate',str(self.candidate),'--requirements',str(self.requirements))
        a=call('claim',run['run_id']);call('claim',run['run_id'],exit_code=2)
        call('interrupt',run['run_id'],'--attempt',a['attempt_id'],'--reason','worker termination confirmed')
        call('recover',run['run_id'],'--decision','resume','--reason','operator reviewed')
        b=call('claim',run['run_id']);self.output(a)
        call('complete',run['run_id'],'--attempt',a['attempt_id'],exit_code=2)
        self.output(b);r=call('complete',run['run_id'],'--attempt',b['attempt_id'])
        self.assertEqual(r['state'],'review_required')
        call('complete',run['run_id'],'--attempt',b['attempt_id'],exit_code=2)
        self.assertEqual(call('current','cli-role')['run_id'],run['run_id'])

    def test_existing_empty_or_unrelated_database_is_never_initialized(self):
        self.ledger()
        for name,empty in [('empty',True),('unrelated',False)]:
            root=self.base/name;root.mkdir(mode=0o700);p=root/'ledger.sqlite3'
            if empty:p.write_bytes(b'')
            else:
                with sqlite3.connect(p) as db:
                    db.execute('CREATE TABLE private_data(value TEXT)');db.execute('PRAGMA user_version=1')
            p.chmod(0o600)
            with self.assertRaises(module.RunError):module.Ledger(root,self.workspace)
            if empty:self.assertEqual(p.read_bytes(),b'')
            else:
                with sqlite3.connect(p) as db:
                    names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    self.assertEqual(names,{'private_data'})

if __name__=='__main__':unittest.main()
