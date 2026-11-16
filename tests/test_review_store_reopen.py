import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from workflow.draft_approval import ApprovalStore

class StoreRecoveryTests(unittest.TestCase):
    def test_existing_empty_database_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'unrelated.sqlite3'
            path.touch(mode=0o600)
            before = path.read_bytes()
            with self.assertRaises(ValueError): ApprovalStore(path, '123456789')
            self.assertEqual(path.read_bytes(), before)

    def test_new_process_reopens_and_decides_same_request_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'store.sqlite3'
            owner = '123456789'
            store = ApprovalStore(path, owner)
            request = store.create('process-recovery', {'local': 'I am setting up a local AI assistant.'}, ['local'], now=100)
            code = "from workflow.draft_approval import ApprovalStore; import sys,json; print(json.dumps(ApprovalStore(sys.argv[1],sys.argv[2]).decide(sys.argv[3],sys.argv[2],'APPROVE',now=110)))"
            result = subprocess.run([sys.executable, '-c', code, str(path), owner, request['id']], text=True, capture_output=True, check=True)
            self.assertEqual(json.loads(result.stdout)['status'], 'approved')
            with self.assertRaises(ValueError): store.decide(request['id'], owner, 'APPROVE', now=111)
