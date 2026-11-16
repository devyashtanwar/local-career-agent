"""Deterministic validation for the v1 skill-match result, never action approval."""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import uuid

MAX_BYTES = 65536
VERSION = 'skill-match-v1'
FIELDS = {'matching_skills', 'missing_skills', 'work_authorization', 'needs_review'}
# Reviewed full-name equivalents only. React Native, C/C++ and unrelated skills stay distinct.
ALIASES = {'react.js': 'react', 'reactjs': 'react'}


class ValidationInputError(ValueError):
    pass


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValidationInputError('duplicate_json_key')
            result[key] = value
        return result

    def reject_constant(value):
        raise ValidationInputError('nonfinite_json_number')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValidationInputError('nonfinite_json_number')
        return number

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_constant=reject_constant, parse_float=finite_float)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise ValidationInputError('invalid_json') from error


def skill_keys(value):
    if type(value) is not list or len(value) > 256:
        raise ValidationInputError('invalid_skill_list')
    keys = []
    for item in value:
        if (type(item) is not str or not item.strip() or len(item) > 128
                or any(ord(c) < 32 for c in item)):
            raise ValidationInputError('invalid_skill_name')
        key = item.strip().casefold()
        key = ALIASES.get(key, key)
        if key in keys:
            raise ValidationInputError('duplicate_skill')
        keys.append(key)
    return keys


def valid_authorization(value):
    return value is None or (type(value) is str and bool(value.strip())
                            and len(value) <= 256 and not any(ord(c) < 32 for c in value))


def evaluate(candidate, requirements, output):
    report = {'validator_version': VERSION, 'validation_passed': False,
              'requires_review': True, 'action_authorized': False, 'errors': []}
    errors = report['errors']
    try:
        if type(candidate) is not dict or not {'skills', 'work_authorization'} <= candidate.keys():
            raise ValidationInputError('missing_candidate_fields')
        known = set(skill_keys(candidate['skills']))
        if not valid_authorization(candidate['work_authorization']):
            raise ValidationInputError('invalid_candidate_authorization')
    except ValidationInputError:
        errors.append('candidate.invalid_facts')
        return report
    try:
        if type(requirements) is not dict or 'required_skills' not in requirements:
            raise ValidationInputError('missing_requirements')
        required = skill_keys(requirements['required_skills'])
        if not required:
            raise ValidationInputError('empty_requirements')
    except ValidationInputError:
        errors.append('requirements.invalid_facts')
        return report
    expected_match = set(required) & known
    expected_missing = set(required) - known
    authorization = candidate['work_authorization']
    report['expected'] = {
        'matching_skills': [s.strip() for s, k in zip(requirements['required_skills'], required) if k in expected_match],
        'missing_skills': [s.strip() for s, k in zip(requirements['required_skills'], required) if k in expected_missing],
        'work_authorization': authorization,
        'needs_review': authorization is None,
    }
    if type(output) is not dict or set(output) != FIELDS:
        errors.append('output.schema_fields')
        return report
    for name, expected in [('matching_skills', expected_match), ('missing_skills', expected_missing)]:
        try:
            actual = set(skill_keys(output[name]))
            if actual != expected:
                errors.append('output.' + name + '_mismatch')
        except ValidationInputError:
            errors.append('output.' + name + '_invalid')
    if not valid_authorization(output['work_authorization']) or output['work_authorization'] != authorization:
        errors.append('output.authorization_mismatch')
    if type(output['needs_review']) is not bool or output['needs_review'] is not (authorization is None):
        errors.append('output.review_flag_mismatch')
    report['validation_passed'] = not errors
    report['requires_review'] = bool(errors) or authorization is None
    return report


def read_bounded(path):
    # Reject symlinks, devices and FIFOs rather than following/blocking on them.
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
            raise ValidationInputError('not_a_bounded_regular_file')
        raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValidationInputError('file_too_large')
        return raw


def write_private(path, raw):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def run_validation(candidate_path, requirements_path, output_path, report_root, forbidden_root=None):
    report_root = Path(report_root).expanduser().resolve()
    if forbidden_root is None:
        forbidden_root = Path.home() / 'career-ai/workspace'
    forbidden_root = Path(forbidden_root).expanduser().resolve()
    if report_root == forbidden_root or forbidden_root in report_root.parents:
        raise ValueError('Reports must be outside the agent workspace')
    report_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex
    folder = report_root / run_id
    folder.mkdir(mode=0o700, exist_ok=False)
    values, hashes, errors = {}, {}, []
    for name, path in [('candidate', candidate_path), ('requirements', requirements_path), ('output', output_path)]:
        try:
            resolved = Path(path).resolve()
            if name != 'output' and (resolved == forbidden_root or forbidden_root in resolved.parents):
                errors.append(name + '.untrusted_location')
                continue
            raw = read_bounded(path)
            hashes[name] = hashlib.sha256(raw).hexdigest()
            if name == 'output':
                write_private(folder / 'model-output.bin', raw)
            try:
                values[name] = parse_json(raw)
            except ValidationInputError:
                errors.append(name + '.invalid_json')
        except (OSError, ValidationInputError):
            errors.append(name + '.unreadable_or_oversize')
    if errors:
        report = {'validator_version': VERSION, 'validation_passed': False,
                  'requires_review': True, 'action_authorized': False, 'errors': errors}
    else:
        report = evaluate(values['candidate'], values['requirements'], values['output'])
    report.update(run_id=run_id, input_sha256=hashes)
    write_private(folder / 'report.json', (json.dumps(report, indent=2) + '\n').encode())
    return report, folder


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--requirements', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reports', type=Path, default=Path.home() / 'career-ai/validation-runs')
    args = parser.parse_args(argv)
    try:
        report, folder = run_validation(args.candidate, args.requirements, args.output, args.reports)
    except (OSError, ValueError) as error:
        # No successful decision is returned when evidence cannot be persisted.
        print('Validation unavailable: cannot safely create evidence. No action authorized.', file=sys.stderr)
        return 1
    print(json.dumps({'validation_passed': report['validation_passed'],
                      'requires_review': report['requires_review'],
                      'action_authorized': False, 'errors': report['errors'],
                      'report_directory': str(folder)}, indent=2))
    return 0 if report['validation_passed'] else 2


if __name__ == '__main__':
    sys.exit(main())
