"""Safety and API-contract tests; no model, GPU, credentials or internet needed."""
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

SCRIPT = pathlib.Path(__file__).with_name('setup_pc.py')


class SetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = None
        if SCRIPT.exists():
            spec = importlib.util.spec_from_file_location('setup_pc', SCRIPT)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)

    def code(self):
        self.assertIsNotNone(self.module, 'Setup implementation has not been written yet')
        return self.module

    def test_refuses_other_hosts_before_installing(self):
        m = self.code()
        for system, arch, distro in [('Darwin', 'arm64', 'macos'), ('Linux', 'x86_64', 'ubuntu'), ('Linux', 'aarch64', 'arch')]:
            with self.subTest(system=system, arch=arch, distro=distro):
                with self.assertRaises(m.SetupError):
                    m.validate_host(system, arch, distro, 1000)
        m.validate_host('Linux', 'x86_64', 'arch', 1000)

    def test_readiness_checks_explicitly_disable_reasoning(self):
        m = self.code()
        payloads = []
        def fake_api(path, payload):
            payloads.append(payload)
            if 'tools' in payload:
                message = {'tool_calls':[{'type':'function','function':{'name':'queue_review','arguments':'{"field":"work_authorization"}'}}]}
            else:
                message = {'content':json.dumps({'matching_skills':['React'],'missing_skills':['TypeScript']})}
            return {'choices':[{'message':message,'finish_reason':'stop'}],'usage':{'completion_tokens':23}}
        with patch.object(m, 'api', side_effect=fake_api):
            results = m.smoke('synthetic')
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r['passed'] for r in results))
        self.assertTrue(all(p.get('reasoning_effort') == 'none' for p in payloads))

    def test_registered_key_is_resolved_from_exact_artifact(self):
        m = self.code()
        self.assertTrue(callable(getattr(m, 'resolve_model_key', None)), 'Registry resolver missing')
        entries = [{'type':'llm','path':'publisher/repo/model-Q4.gguf','modelKey':'registered-alias'}]
        self.assertEqual(m.resolve_model_key(entries, 'publisher/repo/model-Q4.gguf'), 'registered-alias')
        with self.assertRaises(m.SetupError):
            m.resolve_model_key(entries, 'publisher/repo/model-Q8.gguf')
        entries.append({'type':'llm','path':'publisher/repo/model-Q8.gguf','modelKey':'registered-alias'})
        with self.assertRaises(m.SetupError):
            m.resolve_model_key(entries, 'publisher/repo/model-Q4.gguf')

    def test_accepts_omarchy(self):
        m = self.code()
        try:
            m.validate_host('Linux', 'x86_64', 'omarchy', 1000)
        except m.SetupError as error:
            self.fail('Native Omarchy must be accepted: ' + str(error))

    def test_refuses_root_and_old_driver(self):
        m = self.code()
        with self.assertRaises(m.SetupError):
            m.validate_host('Linux', 'x86_64', 'arch', 0)
        with self.assertRaises(m.SetupError):
            m.validate_gpu('NVIDIA GeForce RTX 3060', 12288, '535.104.05', 11000)
        m.validate_gpu('NVIDIA GeForce RTX 3060', 12288, '580.126.09', 11000)

    def test_refuses_busy_gpu(self):
        m = self.code()
        with self.assertRaises(m.SetupError):
            m.validate_gpu('NVIDIA GeForce RTX 3060', 12288, '580.126.09', 2000)

    def test_corrupt_download_is_not_accepted_or_deleted(self):
        m = self.code()
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'model.gguf'
            p.write_bytes(b'corrupt')
            with self.assertRaises(m.SetupError):
                m.verify_file(p, hashlib.sha256(b'valid').hexdigest(), 5)
            self.assertEqual(p.read_bytes(), b'corrupt')

    def test_valid_artifact_can_be_reused(self):
        m = self.code()
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'model.gguf'
            p.write_bytes(b'valid')
            m.verify_file(p, hashlib.sha256(b'valid').hexdigest(), 5)

    def test_listener_check_rejects_public_and_ipv6_wildcard(self):
        m = self.code()
        for address in ['0.0.0.0:1234', '[::]:1234', '*:1234', '100.64.0.2:1234']:
            with self.subTest(address=address):
                with self.assertRaises(m.SetupError):
                    m.validate_listeners('LISTEN 0 4096 ' + address + ' 0.0.0.0:*', 1234)
        m.validate_listeners('LISTEN 0 4096 127.0.0.1:1234 0.0.0.0:*', 1234)
        with self.assertRaises(m.SetupError):
            m.validate_listeners('', 1234)

    def test_capability_checks_reject_fabricated_skill_and_bad_tool(self):
        m = self.code()
        good = {'choices': [{'message': {'content': json.dumps({'matching_skills': ['React'], 'missing_skills': ['TypeScript']})}}]}
        self.assertTrue(m.check_answer('extraction', good))
        bad = {'choices': [{'message': {'content': json.dumps({'matching_skills': ['React', 'TypeScript'], 'missing_skills': []})}}]}
        self.assertFalse(m.check_answer('extraction', bad))
        tool = {'choices': [{'message': {'tool_calls': [{'type': 'function', 'function': {'name': 'queue_review', 'arguments': '{"field":"work_authorization"}'}}]}}]}
        self.assertTrue(m.check_answer('tool_call', tool))
        tool['choices'][0]['message']['tool_calls'][0]['function']['arguments'] = '{"field":"salary"}'
        self.assertFalse(m.check_answer('tool_call', tool))
        self.assertFalse(m.check_answer('extraction', {'choices': []}))

    def test_local_api_transport(self):
        m = self.code()
        self.assertTrue(callable(getattr(m, 'api', None)), 'Local API transport is not implemented')
        received = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                if self.path.endswith('/redirect'):
                    self.send_response(302)
                    self.send_header('Location', 'https://example.com/private')
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"choices":[{"message":{"content":"synthetic"}}]}')

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            original = m.BASE_URL
            m.BASE_URL = 'http://127.0.0.1:' + str(server.server_port) + '/v1'
            try:
                with patch.dict('os.environ', {'http_proxy': 'http://127.0.0.1:1', 'HTTP_PROXY': 'http://127.0.0.1:1', 'no_proxy': '', 'NO_PROXY': ''}):
                    response = m.api('/chat/completions', {'model': 'synthetic', 'messages': []})
                self.assertEqual(response['choices'][0]['message']['content'], 'synthetic')
                self.assertEqual(received[0], {'model': 'synthetic', 'messages': []})
                with self.assertRaises(m.SetupError):
                    m.api('/redirect', {'synthetic': True})
                self.assertEqual(len(received), 2)
            finally:
                m.BASE_URL = original
                server.shutdown()
                worker.join()

    def test_failed_startup_cleans_own_resources_and_does_not_publish_config(self):
        m = self.code()
        self.assertTrue(callable(getattr(m, 'start_model', None)), 'Failure recovery is not implemented')
        for fault in ['load', 'server', 'api', 'capabilities']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as d:
                calls = []

                def cli(args, **kwargs):
                    calls.append(args)
                    if args[1:] == ['server', 'status', '--json', '--quiet']:
                        return '{"running":false}'
                    if args[1] == 'load' and '--estimate-only' not in args and fault == 'load':
                        raise m.SetupError('synthetic load failure')
                    if args[1:3] == ['server', 'start'] and fault == 'server':
                        raise m.SetupError('synthetic start failure')
                    if args == ['ss', '-ltn']:
                        return 'LISTEN 0 4096 127.0.0.1:1234 0.0.0.0:*'
                    return ''

                def checks(_):
                    if fault == 'api':
                        raise m.SetupError('synthetic API failure')
                    return [{'test': 'extraction', 'passed': False}]

                report = {}
                with patch.object(m, 'run', side_effect=cli), patch.object(m, 'smoke', side_effect=checks):
                    with self.assertRaises(m.SetupError):
                        m.start_model('lms', 'model-key', 'career-test', pathlib.Path(d), report)
                self.assertFalse((pathlib.Path(d) / 'local-model.env').exists())
                self.assertIn(['lms', 'unload', 'career-test'], calls)
                self.assertEqual(['lms', 'server', 'stop'] in calls, fault != 'load')

    def test_existing_server_is_preserved(self):
        m = self.code()
        self.assertTrue(callable(getattr(m, 'start_model', None)), 'Failure recovery is not implemented')
        calls = []

        def cli(args, **kwargs):
            calls.append(args)
            return '{"running":true,"port":9000}'

        with tempfile.TemporaryDirectory() as d, patch.object(m, 'run', side_effect=cli):
            with self.assertRaises(m.SetupError):
                m.start_model('lms', 'model-key', 'career-test', pathlib.Path(d), {})
        self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
