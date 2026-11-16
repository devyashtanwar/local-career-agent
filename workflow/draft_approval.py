"""Private persistent review records. This module never executes account actions.
Only a trusted host adapter may call this API; actor must come from Telegram
sender metadata, never from model-generated text or message body.
"""
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import time
import uuid
from validation.grounded_draft import render


def clock(value):
    value = time.time() if value is None else value
    if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid trusted host timestamp')
    return value


class ApprovalStore:
    def __init__(self, path, owner):
        if type(owner) is not str or not owner:
            raise ValueError('owner required')
        self.path = Path(path)
        self.owner = owner
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.parent.is_symlink() or self.path.parent.stat().st_mode & 0o077:
            raise ValueError('use a dedicated private directory')
        created = not self.path.exists()
        if created:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
            raise ValueError('approval database must be private')
        with closing(self.connect()) as db, db:
            if not created:
                names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if names != {'settings', 'approvals'}:
                    raise ValueError('existing database is not a review store')
                columns = [row[1] for row in db.execute('PRAGMA table_info(approvals)')]
                if columns != ['id','task','generation','digest','payload','status','created','expires','decided']:
                    raise ValueError('unsupported review schema')
                existing = db.execute("SELECT value FROM settings WHERE key='owner'").fetchone()
                if existing is None or existing[0] != owner:
                    raise ValueError('existing owner differs; explicit migration required')
            db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute('INSERT OR IGNORE INTO settings VALUES (?, ?)', ('owner', owner))
            if db.execute('SELECT value FROM settings WHERE key=?', ('owner',)).fetchone()[0] != owner:
                raise ValueError('existing owner differs; explicit migration required')
            db.execute('''CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY, task TEXT NOT NULL, generation INTEGER NOT NULL,
                digest TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL, decided REAL,
                UNIQUE(task, generation))''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def public(row):
        result = dict(row)
        result['action_authorized'] = False
        result['draft'] = json.loads(result.pop('payload'))['draft']
        return result

    def create(self, task, facts, selection, ttl=3600, now=None):
        now = clock(now)
        if type(task) is not str or not task.strip() or len(task) > 128:
            raise ValueError('invalid task identifier')
        if type(ttl) is not int or not 1 <= ttl <= 86400:
            raise ValueError('expiry must be 1 to 86400 seconds')
        draft = render(facts, selection)
        payload = json.dumps({'facts': facts, 'selection': selection, 'draft': draft}, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        request_id = str(uuid.uuid4())
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT * FROM approvals WHERE task=? ORDER BY generation DESC LIMIT 1', (task,)).fetchone()
            if latest and latest['digest'] == digest:
                raise ValueError('duplicate task revision')
            generation = latest['generation'] + 1 if latest else 1
            db.execute("UPDATE approvals SET status='superseded' WHERE task=? AND status IN ('pending','approved')", (task,))
            db.execute('INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?,NULL)',
                       (request_id, task, generation, digest, payload, 'pending', now, now + ttl))
            row = db.execute('SELECT * FROM approvals WHERE id=?', (request_id,)).fetchone()
        return self.public(row)

    def decide(self, request_id, actor, decision, now=None):
        now = clock(now)
        if actor != self.owner or type(actor) is not str:
            raise ValueError('unauthorized sender')
        if decision not in ('APPROVE', 'REJECT'):
            raise ValueError('exact decision required')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM approvals WHERE id=?', (request_id,)).fetchone()
            if row is None or row['status'] != 'pending':
                raise ValueError('unknown or no longer pending request')
            latest = db.execute('SELECT MAX(generation) FROM approvals WHERE task=?', (row['task'],)).fetchone()[0]
            if row['generation'] != latest:
                raise ValueError('stale request')
            if now < row['created']:
                raise ValueError('host clock moved backwards; operator review required')
            payload = json.loads(row['payload'])
            if hashlib.sha256(row['payload'].encode()).hexdigest() != row['digest']:
                raise ValueError('draft digest mismatch')
            if render(payload['facts'], payload['selection']) != payload['draft']:
                raise ValueError('draft no longer matches approved statements')
            status = 'expired' if now >= row['expires'] else ('approved' if decision == 'APPROVE' else 'rejected')
            db.execute('UPDATE approvals SET status=?, decided=? WHERE id=?', (status, now, request_id))
            row = db.execute('SELECT * FROM approvals WHERE id=?', (request_id,)).fetchone()
        return self.public(row)

    def decide_message(self, actor, text, now=None):
        """Trusted transport supplies actor; no LLM interpretation of replies."""
        import re
        if type(text) is not str:
            raise ValueError('exact reply required')
        match = re.fullmatch(r'(APPROVE|REJECT) ([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', text)
        if match is None:
            raise ValueError('reply must contain exact decision and request UUID')
        return self.decide(match[2], actor, match[1], now=now)
