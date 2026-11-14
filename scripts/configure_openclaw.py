#!/usr/bin/env python3
"""Create a fresh user-local configuration. Never replace an existing setup."""
import argparse
import json
import os
from pathlib import Path
import secrets


def configure(home, template):
    home = Path(home)
    if not home.is_absolute():
        raise ValueError('Home must be an absolute path')
    state = home / '.openclaw'
    workspace = home / 'career-ai/workspace'
    for path in (state, home / 'career-ai', workspace):
        if path.is_symlink():
            raise ValueError('Refusing a symlinked configuration or workspace directory')
    destination = state / 'openclaw.json'
    if destination.exists() or destination.is_symlink():
        raise FileExistsError('Existing OpenClaw configuration left untouched; merge changes manually')
    config = json.loads(Path(template).read_text().replace('${HOME}', str(home)))
    config['gateway']['auth']['token'] = secrets.token_hex(32)
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    workspace.mkdir(parents=True, mode=0o700, exist_ok=True)
    for name in ('inbox', 'profile', 'drafts', 'review', 'evidence', 'tests'):
        (workspace / name).mkdir(mode=0o700, exist_ok=True)
    rules = Path(template).with_name('AGENTS.md').read_text()
    rules_path = workspace / 'AGENTS.md'
    if not rules_path.exists() and not rules_path.is_symlink():
        with rules_path.open('x') as stream:
            stream.write(rules)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(destination, flags, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(json.dumps(config, indent=2) + '\n')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Write fresh configuration and workspace')
    args = parser.parse_args()
    if not args.apply:
        print('Preview only. With --apply: create ~/.openclaw/openclaw.json and ~/career-ai/workspace; never overwrite an existing config. No services start.')
    else:
        try:
            destination = configure(Path.home(), Path(__file__).resolve().parents[1] / 'config/openclaw.template.json')
            print('Created private configuration:', destination)
            print('Token remains on this machine. Validate using the pinned OpenClaw CLI before starting.')
        except (OSError, ValueError) as error:
            parser.exit(1, str(error) + '\n')
