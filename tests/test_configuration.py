import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def implementation(self):
        script = ROOT / 'scripts/configure_openclaw.py'
        self.assertTrue(script.exists(), 'Portable configuration renderer is missing')
        spec = importlib.util.spec_from_file_location('configure_openclaw', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_home_paths_and_private_token_are_generated_locally(self):
        module = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            destination = module.configure(home, ROOT / 'config/openclaw.template.json')
            config = json.loads(destination.read_text())
            self.assertEqual(config['agents']['defaults']['workspace'], str(home / 'career-ai/workspace'))
            self.assertEqual(len(config['gateway']['auth']['token']), 64)
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
            self.assertEqual(destination.parent.stat().st_mode & 0o777, 0o700)
            self.assertTrue((home / 'career-ai/workspace/AGENTS.md').exists())
            self.assertFalse((home / 'career-ai/workspace/tests/candidate.json').exists())

    def test_existing_configuration_is_never_overwritten(self):
        module = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            destination = module.configure(home, ROOT / 'config/openclaw.template.json')
            original = destination.read_bytes()
            with self.assertRaises(FileExistsError):
                module.configure(home, ROOT / 'config/openclaw.template.json')
            self.assertEqual(destination.read_bytes(), original)

    def test_symlinked_state_directory_is_rejected(self):
        module = self.implementation()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d); outside = home / 'outside'; outside.mkdir()
            (home / '.openclaw').symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                module.configure(home, ROOT / 'config/openclaw.template.json')
            self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
