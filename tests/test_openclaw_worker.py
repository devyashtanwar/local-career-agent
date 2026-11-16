"""Exercise the real subprocess boundary; no model download needed."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from workflow.ledger import Ledger, RunError
from workflow.openclaw_worker import execute, WorkerError

class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.workspace=self.base/'workspace'
        self.ledger=Ledger(self.base/'state',self.workspace)
        self.c=self.base/'candidate.json';self.r=self.base/'requirements.json'
        self.c.write_text(json.dumps({'skills':['React','Python'],'work_authorization':None}))
        self.r.write_text(json.dumps({'required_skills':['React.js','SQL']}))
        self.config=self.base/'config.json'
        self.policy=json.loads((Path(__file__).resolve().parents[1]/'config/openclaw.template.json').read_text().replace('$'+'{HOME}',str(Path.home())))
        self.policy['agents']['defaults']['workspace']=str(self.workspace)
        self.policy['agents']['entries']['main']['workspace']=str(self.workspace)
        self.config.write_text(json.dumps(self.policy));self.config.chmod(0o600)
        self.worker=self.base/'worker'
        self.result={'matching_skills':['React.js'],'missing_skills':['SQL'],'work_authorization':None,'needs_review':True}
    def run_id(self):return self.ledger.create('synthetic',self.c,self.r)['run_id']
    def script(self,body):
        self.worker.write_text('#!/usr/bin/env python3\nimport sys,json,os,time\nfrom pathlib import Path\np=json.loads(sys.argv[sys.argv.index("--message")+1])\n'+body+'\n')
        self.worker.chmod(0o700)
    def launch(self,run,timeout=5):
        return execute(self.ledger,run,self.worker,self.config,timeout=timeout,expected_policy=self.policy)
    def valid(self):self.script('Path(p["output"]).write_text('+repr(json.dumps(self.result))+')')
    def test_success_needs_review_and_fresh_session(self):
        self.script('assert "--local" in sys.argv\nassert sys.argv[sys.argv.index("--session-id")+1].startswith("career-")\nassert not os.environ.get("AWS_SECRET_ACCESS_KEY")\nPath(p["output"]).write_text('+repr(json.dumps(self.result))+')')
        run=self.run_id();old=os.environ.get('AWS_SECRET_ACCESS_KEY');os.environ['AWS_SECRET_ACCESS_KEY']='synthetic-secret'
        try:result=self.launch(run)
        finally:
            if old is None:os.environ.pop('AWS_SECRET_ACCESS_KEY',None)
            else:os.environ['AWS_SECRET_ACCESS_KEY']=old
        self.assertEqual(result['state'],'review_required');self.assertFalse(result['action_authorized'])
        with self.assertRaises(RunError):self.launch(run)
    def test_missing_file_rejected(self):
        self.script('pass');self.assertEqual(self.launch(self.run_id())['state'],'rejected')
    def test_incorrect_result_rejected(self):
        self.script('Path(p["output"]).write_text("{}")');self.assertEqual(self.launch(self.run_id())['state'],'rejected')
    def test_nonzero_never_accepts_valid_file(self):
        self.valid();self.worker.write_text(self.worker.read_text()+'sys.exit(3)\n')
        self.assertEqual(self.launch(self.run_id())['state'],'interrupted')
    def test_timeout_requires_explicit_recovery(self):
        self.script('time.sleep(20)');run=self.run_id();first=self.launch(run,0.1)
        self.assertEqual(first['state'],'interrupted')
        with self.assertRaises(RunError):self.launch(run)
        self.ledger.recover(run,'resume','test worker stopped by adapter');self.valid()
        second=self.launch(run);self.assertEqual(second['state'],'review_required')
        self.assertNotEqual(first['attempt_id'],second['attempt_id'])
    def test_config_drift_leaves_pending(self):
        self.valid();run=self.run_id();p=json.loads(self.config.read_text());p['models']['providers']['cloud']={};self.config.write_text(json.dumps(p))
        with self.assertRaises(WorkerError):self.launch(run)
        self.assertEqual(self.ledger.status(run)['state'],'pending')
    def test_untrusted_executable_rejected(self):
        self.valid();run=self.run_id();self.workspace.mkdir(exist_ok=True);self.worker=self.workspace/'worker';self.valid()
        with self.assertRaises(WorkerError):self.launch(run)
        self.assertEqual(self.ledger.status(run)['state'],'pending')
    def test_second_worker_lock_leaves_pending(self):
        import fcntl
        self.valid();run=self.run_id()
        with (self.ledger.root/'openclaw-worker.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(WorkerError):self.launch(run)
        self.assertEqual(self.ledger.status(run)['state'],'pending')


    def test_same_config_serializes_different_ledgers(self):
        from workflow.openclaw_worker import worker_lock
        self.valid();run=self.run_id()
        with worker_lock(self.config.parent):
            with self.assertRaises(WorkerError):self.launch(run)
        self.assertEqual(self.ledger.status(run)['state'],'pending')
    def test_operator_interrupt_stops_attempt(self):
        self.script(chr(10).join(['os.kill(os.getppid(),2)','time.sleep(20)']))
        self.assertEqual(self.launch(self.run_id())['state'],'interrupted')
    def test_superseded_during_worker_cannot_complete(self):
        self.script(chr(10).join(['sys.path.insert(0,'+repr(str(Path(__file__).resolve().parents[1]))+')','from workflow.ledger import Ledger','Path(p["output"]).write_text('+repr(json.dumps(self.result))+')','Ledger('+repr(str(self.ledger.root))+','+repr(str(self.workspace))+').create("synthetic",'+repr(str(self.c))+','+repr(str(self.r))+')']))
        run=self.run_id()
        with self.assertRaises(RunError):self.launch(run)
        self.assertEqual(self.ledger.status(run)['state'],'superseded')
        self.assertEqual(self.ledger.current('synthetic')['state'],'pending')

if __name__=='__main__':unittest.main()
