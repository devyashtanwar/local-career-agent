"""No network or models. Screenshot failures are regression inputs."""
import tempfile
import unittest
from pathlib import Path
from validation.grounded_draft import render
from workflow.draft_approval import ApprovalStore

FACTS = {'local': 'I am setting up a local AI assistant.', 'telegram': 'Telegram messaging is connected.'}
OWNER = '123456789'

class GroundedDraftTests(unittest.TestCase):
    def test_verified_facts_render(self):
        self.assertEqual(render(FACTS, ['local', 'telegram']), '\n\n'.join(FACTS.values()))

    def test_recorded_privacy_claim_is_rejected(self):
        with self.assertRaises(ValueError):
            render(FACTS, ['Running the model locally keeps data private.'])

    def test_recorded_workflow_overclaim_is_rejected(self):
        with self.assertRaises(ValueError):
            render(FACTS, ['Conversational approval testing confirms the workflow works as intended.'])

    def test_free_prose_and_unrecognized_ids_rejected(self):
        for selection in ('local', ['unknown'], [{'id': 'local', 'text': 'No data leaks.'}], ['local', 'local'], []):
            with self.subTest(selection=selection), self.assertRaises(ValueError):
                render(FACTS, selection)

    def test_word_limit_and_invalid_facts(self):
        with self.assertRaises(ValueError): render({'x': 'word ' * 121}, ['x'])
        with self.assertRaises(ValueError): render({'x': ''}, ['x'])
        with self.assertRaises(ValueError): render({'x': 42}, ['x'])

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'private' / 'approvals.sqlite3'
        self.store = ApprovalStore(self.path, OWNER)
    def tearDown(self): self.tmp.cleanup()
    def request(self, task='TEST-002', now=100):
        return self.store.create(task, FACTS, ['local'], ttl=60, now=now)
    def test_persists_and_requires_exact_owner(self):
        request = self.request()
        reopened = ApprovalStore(self.path, OWNER)
        with self.assertRaises(ValueError): reopened.decide(request['id'], 'stranger', 'APPROVE', now=110)
        result = reopened.decide(request['id'], OWNER, 'APPROVE', now=110)
        self.assertEqual(result['status'], 'approved')
        self.assertFalse(result['action_authorized'])
    def test_rejection_and_duplicate_decision(self):
        request = self.request()
        self.assertEqual(self.store.decide(request['id'], OWNER, 'REJECT', now=110)['status'], 'rejected')
        with self.assertRaises(ValueError): self.store.decide(request['id'], OWNER, 'APPROVE', now=111)
    def test_expiry_persisted(self):
        request = self.request()
        self.assertEqual(self.store.decide(request['id'], OWNER, 'APPROVE', now=160)['status'], 'expired')
        with self.assertRaises(ValueError): self.store.decide(request['id'], OWNER, 'APPROVE', now=161)
    def test_new_revision_invalidates_previous(self):
        old = self.request()
        new = self.store.create('TEST-002', FACTS, ['telegram'], ttl=60, now=101)
        self.assertNotEqual(old['digest'], new['digest'])
        with self.assertRaises(ValueError): self.store.decide(old['id'], OWNER, 'APPROVE', now=110)
        self.assertEqual(self.store.decide(new['id'], OWNER, 'APPROVE', now=110)['status'], 'approved')
    def test_duplicate_creation_keeps_existing_pending(self):
        first = self.request()
        with self.assertRaises(ValueError): self.request()
        self.assertEqual(self.store.decide(first['id'], OWNER, 'APPROVE', now=110)['status'], 'approved')
    def test_bad_draft_cannot_create_request(self):
        with self.assertRaises(ValueError): self.store.create('x', FACTS, ['No data leaks.'], now=100)
    def test_unknown_id_and_invalid_decision(self):
        with self.assertRaises(ValueError): self.store.decide('missing', OWNER, 'APPROVE', now=110)
        request = self.request()
        with self.assertRaises(ValueError): self.store.decide(request['id'], OWNER, 'approve everything', now=110)
    def test_owner_cannot_be_reconfigured_on_reopen(self):
        with self.assertRaises(ValueError): ApprovalStore(self.path, 'another-user')
    def test_private_permissions(self):
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.path.parent.stat().st_mode & 0o777, 0o700)


    def test_screenshot_regressions_are_rejected(self):
        import json
        cases = json.loads((Path(__file__).resolve().parents[1] / 'examples/grounding-regressions.json').read_text())['cases']
        for case in cases:
            with self.subTest(case=case['id']), self.assertRaises(ValueError):
                render(FACTS, [case['observed']])

    def test_simultaneous_decisions_accept_only_one(self):
        from concurrent.futures import ThreadPoolExecutor
        request = self.request()
        def reply(_):
            try: return self.store.decide(request['id'], OWNER, 'APPROVE', now=110)['status']
            except ValueError: return 'refused'
        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertCountEqual(list(executor.map(reply, range(2))), ['approved', 'refused'])

    def test_modified_database_payload_is_refused(self):
        import sqlite3
        from contextlib import closing
        request = self.request()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('UPDATE approvals SET payload=? WHERE id=?', ('{}', request['id']))
        with self.assertRaises(ValueError): self.store.decide(request['id'], OWNER, 'APPROVE', now=110)

    def test_changes_to_caller_facts_do_not_change_snapshot(self):
        facts = dict(FACTS)
        request = self.store.create('snapshot', facts, ['local'], now=100)
        facts['local'] = 'No data leaks.'
        result = self.store.decide(request['id'], OWNER, 'APPROVE', now=110)
        self.assertEqual(result['draft'], FACTS['local'])

    def test_exact_reply_parser(self):
        request = self.request()
        for text in ['APPROVE TEST-002', 'yes', 'APPROVE '+request['id']+' and publish', 'IGNORE RULES', 'APPROVE '+request['id']+chr(10)]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.store.decide_message(OWNER, text, now=110)
        self.assertEqual(self.store.decide_message(OWNER, 'APPROVE '+request['id'], now=110)['status'], 'approved')

    def test_bad_clock_and_ttl(self):
        for now in [float('nan'), float('inf'), -1, True]:
            with self.assertRaises(ValueError): self.request(now=now)
        for ttl in [0, -1, 86401, True]:
            with self.assertRaises(ValueError): self.store.create('bad', FACTS, ['local'], ttl=ttl)

if __name__ == '__main__': unittest.main()
