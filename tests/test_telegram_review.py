import json
from pathlib import Path
import tempfile
import unittest
from workflow.telegram_review import handle

class TelegramReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.facts = root/'facts.json'
        self.facts.write_text(json.dumps({'local':'I am setting up a local AI assistant.'}))
        self.settings={'owner':'123456789','database':str(root/'state'/'reviews.sqlite3'),'facts':str(self.facts)}
    def tearDown(self): self.temp.cleanup()
    def run_command(self, text): return handle(self.settings, '123456789', text)
    def test_wrong_sender_cannot_create(self):
        with self.assertRaises(ValueError): handle(self.settings, 'other', 'new x local')
        self.assertFalse(Path(self.settings['database']).exists())
    def test_identical_new_is_idempotent_and_does_not_extend_expiry(self):
        first=self.run_command('new TEST-003 local')['request']
        second=self.run_command('new TEST-003 local')['request']
        self.assertEqual(first,second)
    def test_full_review_and_duplicate_decision(self):
        request=self.run_command('new TEST-003 local')['request']
        self.assertIn(request['digest'],self.run_command('status '+request['id'])['text'])
        result=self.run_command('reject '+request['id'])
        self.assertEqual(result['request']['status'],'rejected')
        self.assertFalse(result['action_authorized'])
        with self.assertRaises(ValueError): self.run_command('approve '+request['id'])
    def test_approval_keeps_exact_draft_and_no_authority(self):
        request=self.run_command('new TEST-004 local')['request']
        result=self.run_command('approve '+request['id'])
        self.assertEqual(result['request']['draft'],request['draft'])
        self.assertFalse(result['action_authorized'])
    def test_unsupported_text_rejected(self):
        for args in ['new x privacy', 'new x local;whoami', 'approve TEST-002', 'publish anything']:
            with self.subTest(args=args), self.assertRaises(ValueError): self.run_command(args)
    def test_help_does_not_create_database(self):
        self.assertIn('no publishing',self.run_command('help')['text'])
        self.assertFalse(Path(self.settings['database']).exists())
