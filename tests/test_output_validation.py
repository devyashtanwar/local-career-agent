"""Synthetic validation and retention tests; no models, network or credentials."""
import copy
import importlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
try:
    validator = importlib.import_module('validation.skill_match')
except ModuleNotFoundError:
    validator = None

CANDIDATE = {'skills': ['React'], 'work_authorization': None}
REQUIREMENTS = {'required_skills': ['React', 'TypeScript']}
GOOD = {'matching_skills': ['React'], 'missing_skills': ['TypeScript'],
        'work_authorization': None, 'needs_review': True}


class OutputValidationTests(unittest.TestCase):
    def code(self):
        self.assertIsNotNone(validator, 'Output validator has not been implemented')
        return validator

    def test_correct_result_is_valid_but_unknown_still_needs_review(self):
        r = self.code().evaluate(CANDIDATE, REQUIREMENTS, GOOD)
        self.assertTrue(r['validation_passed'])
        self.assertTrue(r['requires_review'])
        self.assertEqual(r['errors'], [])

    def test_recorded_omitted_skill_is_rejected(self):
        bad = json.loads((ROOT / 'examples/results/final-gateway-output-failed-validation.json').read_text())
        r = self.code().evaluate(CANDIDATE, REQUIREMENTS, bad)
        self.assertFalse(r['validation_passed'])
        self.assertIn('output.missing_skills_mismatch', r['errors'])
        self.assertTrue(r['requires_review'])

    def test_recorded_restart_output_is_rejected(self):
        bad = json.loads((ROOT / 'examples/results/restart-recovery-overwrite.json').read_text())
        self.assertFalse(self.code().evaluate(CANDIDATE, REQUIREMENTS, bad)['validation_passed'])

    def test_invented_skills_and_authorization_are_rejected(self):
        for changes in [dict(matching_skills=['React', 'TypeScript'], missing_skills=[]),
                        dict(work_authorization='authorized', needs_review=False)]:
            with self.subTest(changes=changes):
                self.assertFalse(self.code().evaluate(CANDIDATE, REQUIREMENTS, {**GOOD, **changes})['validation_passed'])

    def test_review_boolean_is_strict_and_unknown_cannot_clear_it(self):
        for value in [False, 1, 'true', None]:
            with self.subTest(value=value):
                self.assertFalse(self.code().evaluate(CANDIDATE, REQUIREMENTS, {**GOOD, 'needs_review': value})['validation_passed'])

    def test_extra_keys_wrong_types_and_duplicate_skills_are_rejected(self):
        cases = [[], {**GOOD, 'submit': True}, {**GOOD, 'matching_skills': 'React'},
                 {**GOOD, 'missing_skills': ['TypeScript', 'typescript']},
                 {**GOOD, 'matching_skills': ['React', 'React.js']},
                 {**GOOD, 'work_authorization': 1}, {**GOOD, 'missing_skills': [42]}]
        for bad in cases:
            with self.subTest(bad=bad):
                self.assertFalse(self.code().evaluate(CANDIDATE, REQUIREMENTS, bad)['validation_passed'])

    def test_aliases_and_order_are_explicit_not_fuzzy(self):
        r = self.code().evaluate({'skills': ['React.js'], 'work_authorization': None},
                                {'required_skills': ['TypeScript', ' react ']}, GOOD)
        self.assertTrue(r['validation_passed'])
        self.assertFalse(self.code().evaluate({'skills': ['React Native'], 'work_authorization': None}, REQUIREMENTS, GOOD)['validation_passed'])
        r = self.code().evaluate({'skills': ['C'], 'work_authorization': None},
                               {'required_skills': ['C++']},
                               {**GOOD, 'matching_skills': [], 'missing_skills': ['C++']})
        self.assertTrue(r['validation_passed'])

    def test_empty_profile_and_known_authorization(self):
        c = {'skills': [], 'work_authorization': 'requires sponsorship'}
        result = {**GOOD, 'matching_skills': [], 'missing_skills': ['React', 'TypeScript'],
                  'work_authorization': 'requires sponsorship', 'needs_review': False}
        r = self.code().evaluate(c, REQUIREMENTS, result)
        self.assertTrue(r['validation_passed'])
        self.assertFalse(r['requires_review'])

    def test_invalid_trusted_inputs_fail_closed(self):
        pairs = [({}, REQUIREMENTS), ({'skills': [], 'work_authorization': True}, REQUIREMENTS),
                 (CANDIDATE, {'required_skills': []}),
                 (CANDIDATE, {'required_skills': ['React', 'React.js']}),
                 ({'skills': ['React', 'react'], 'work_authorization': None}, REQUIREMENTS)]
        for candidate, requirements in pairs:
            with self.subTest(candidate=candidate, requirements=requirements):
                r = self.code().evaluate(candidate, requirements, GOOD)
                self.assertFalse(r['validation_passed'])
                self.assertTrue(r['requires_review'])

    def test_inputs_are_not_modified(self):
        values = [copy.deepcopy(x) for x in (CANDIDATE, REQUIREMENTS, GOOD)]
        original = copy.deepcopy(values)
        self.code().evaluate(*values)
        self.assertEqual(values, original)

    def test_json_rejects_duplicate_keys_nonfinite_and_fenced_text(self):
        for raw in [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                    b'\xff', bytes([96])*3+b'json\n{}\n'+bytes([96])*3, b'{} trailing', b'{']:
            with self.subTest(raw=raw):
                with self.assertRaises(self.code().ValidationInputError):
                    self.code().parse_json(raw)

    def inputs(self, directory, output):
        paths = []
        for name, value in [('candidate', CANDIDATE), ('requirements', REQUIREMENTS), ('output', output)]:
            p = directory / (name + '.json'); p.write_text(json.dumps(value)); paths.append(p)
        return paths

    def test_reports_are_unique_private_and_preserve_rejected_output(self):
        v = self.code()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); paths = self.inputs(root, {**GOOD, 'missing_skills': []})
            raw = paths[2].read_bytes(); original = [p.read_bytes() for p in paths]
            report_root = root / 'reports'
            first, first_dir = v.run_validation(*paths, report_root)
            first_bytes = (first_dir / 'report.json').read_bytes()
            second, second_dir = v.run_validation(*paths, report_root)
            self.assertFalse(first['validation_passed'])
            self.assertNotEqual(first_dir, second_dir)
            self.assertEqual((first_dir / 'report.json').read_bytes(), first_bytes)
            self.assertEqual((first_dir / 'model-output.bin').read_bytes(), raw)
            self.assertEqual([p.read_bytes() for p in paths], original)
            self.assertEqual(first_dir.stat().st_mode & 0o777, 0o700)
            self.assertEqual((first_dir / 'report.json').stat().st_mode & 0o777, 0o600)
            self.assertEqual((first_dir / 'model-output.bin').stat().st_mode & 0o777, 0o600)
            self.assertEqual(len(first['input_sha256']['candidate']), 64)
            self.assertFalse((first_dir / 'candidate.json').exists())

    def test_malformed_output_is_retained_and_missing_input_rejected(self):
        v = self.code()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); paths = self.inputs(root, GOOD); paths[2].write_bytes(b'{broken')
            r, folder = v.run_validation(*paths, root / 'reports')
            self.assertFalse(r['validation_passed'])
            self.assertEqual((folder / 'model-output.bin').read_bytes(), b'{broken')
            paths[0].unlink()
            r, folder = v.run_validation(*paths, root / 'reports')
            self.assertFalse(r['validation_passed'])
            self.assertTrue(r['requires_review'])

    def test_symlink_oversize_and_model_writable_report_location_rejected(self):
        v = self.code()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); paths = self.inputs(root, GOOD)
            link = root / 'link.json'; link.symlink_to(paths[2])
            r, _ = v.run_validation(paths[0], paths[1], link, root / 'reports')
            self.assertFalse(r['validation_passed'])
            paths[2].write_bytes(b' ' * (v.MAX_BYTES + 1))
            r, _ = v.run_validation(*paths, root / 'reports')
            self.assertFalse(r['validation_passed'])
            with self.assertRaises(ValueError):
                v.run_validation(*paths, root / 'workspace' / 'reports', forbidden_root=root / 'workspace')


    def test_overflowing_json_number_is_rejected(self):
        with self.assertRaises(self.code().ValidationInputError):
            self.code().parse_json(b'{"value":1e400}')

    def test_agent_workspace_cannot_supply_its_own_trusted_facts(self):
        v = self.code()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); workspace = root / 'workspace'; workspace.mkdir()
            paths = self.inputs(workspace, GOOD)
            r, folder = v.run_validation(*paths, root / 'reports', forbidden_root=workspace)
            self.assertFalse(r['validation_passed'])
            self.assertIn('candidate.untrusted_location', r['errors'])
            self.assertIn('requirements.untrusted_location', r['errors'])

    def test_cli_exit_codes_review_and_persistence_failure(self):
        import subprocess
        import sys
        self.code()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); paths = self.inputs(root, GOOD)
            command = [sys.executable, '-m', 'validation.skill_match', '--candidate', str(paths[0]),
                       '--requirements', str(paths[1]), '--output', str(paths[2]), '--reports', str(root / 'reports')]
            good = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(good.returncode, 0, good.stderr)
            response = json.loads(good.stdout)
            self.assertTrue(response['requires_review'])
            self.assertFalse(response['action_authorized'])
            paths[2].write_text(json.dumps({**GOOD, 'missing_skills': []}))
            bad = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(bad.returncode, 2, bad.stderr)
            obstruction = root / 'not-a-folder'; obstruction.write_text('existing')
            failed = subprocess.run(command[:-1] + [str(obstruction)], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(failed.stdout, '')
            self.assertEqual(obstruction.read_text(), 'existing')

if __name__ == '__main__':
    unittest.main()
