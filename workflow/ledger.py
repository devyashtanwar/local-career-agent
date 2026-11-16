"""Local run ledger with fenced attempts; never approves external actions."""
from contextlib import contextmanager
import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import uuid
from validation.skill_match import MAX_BYTES, ValidationInputError, evaluate, parse_json, read_bounded


class RunError(ValueError):
    pass


SCHEMA = '''
CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(job_key TEXT PRIMARY KEY,generation INTEGER NOT NULL,current_run TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs(
 run_id TEXT PRIMARY KEY,job_key TEXT NOT NULL REFERENCES jobs(job_key),generation INTEGER NOT NULL,
 candidate BLOB NOT NULL,requirements BLOB NOT NULL,c_sha TEXT NOT NULL,r_sha TEXT NOT NULL,
 state TEXT NOT NULL,attempt_id TEXT);
CREATE TABLE IF NOT EXISTS attempts(attempt_id TEXT PRIMARY KEY,run_id TEXT NOT NULL REFERENCES runs(run_id),state TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS results(run_id TEXT PRIMARY KEY REFERENCES runs(run_id),attempt_id TEXT NOT NULL,
 raw BLOB,sha TEXT,validation TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,run_id TEXT NOT NULL REFERENCES runs(run_id),
 event TEXT NOT NULL,detail TEXT NOT NULL,created TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS results_no_update BEFORE UPDATE ON results BEGIN SELECT RAISE(ABORT,'immutable result'); END;
CREATE TRIGGER IF NOT EXISTS results_no_delete BEFORE DELETE ON results BEGIN SELECT RAISE(ABORT,'immutable result'); END;
CREATE TRIGGER IF NOT EXISTS facts_no_update BEFORE UPDATE OF candidate,requirements,c_sha,r_sha,job_key,generation ON runs
 BEGIN SELECT RAISE(ABORT,'immutable facts'); END;
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append only events'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append only events'); END;
'''
SELECT_RUN = '''SELECT r.*,j.current_run AS active_run,j.generation AS active_generation,
 s.validation,s.sha AS output_sha FROM runs r JOIN jobs j ON j.job_key=r.job_key
 LEFT JOIN results s ON s.run_id=r.run_id '''


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def reason(value):
    if type(value) is not str or not value.strip() or len(value)>512 or any(ord(c)<32 for c in value):
        raise RunError('A nonempty bounded operator reason is required')
    return value.strip()


class Ledger:
    def __init__(self, root, workspace):
        root=Path(root).expanduser();workspace=Path(workspace).expanduser()
        if root.is_symlink() or workspace.is_symlink():
            raise RunError('State/workspace cannot be symlinks')
        self.root=root.resolve();self.workspace=workspace.resolve()
        if self.root==self.workspace or self.workspace in self.root.parents:
            raise RunError('State must be outside the agent workspace')
        self.root.mkdir(parents=True,mode=0o700,exist_ok=True)
        if self.root.stat().st_mode & 0o077:
            raise RunError('Use a private mode-700 state directory')
        self.db_path=self.root/'ledger.sqlite3'
        created=False
        try:
            fd=os.open(self.db_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            os.close(fd);created=True
        except FileExistsError:
            info=self.db_path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_size==0:
                raise RunError('Existing database is empty, unsafe or not private; inspect it manually')
        try:
            with self._connection() as db:
                version=db.execute('PRAGMA user_version').fetchone()[0]
                if created:
                    db.executescript('BEGIN IMMEDIATE;'+SCHEMA)
                    db.execute('INSERT INTO metadata VALUES(?,?)',('kind','career-run-ledger-v1'))
                    db.execute('INSERT INTO metadata VALUES(?,?)',('workspace',str(self.workspace)))
                    db.execute('PRAGMA user_version=1');db.commit()
                elif version!=1:
                    raise RunError('Unsupported or unrelated ledger; no automatic reset')
                metadata=dict(db.execute('SELECT key,value FROM metadata'))
                if metadata.get('kind')!='career-run-ledger-v1':raise RunError('Unrelated database')
                if metadata.get('workspace')!=str(self.workspace):raise RunError('Ledger is bound to a different workspace')
                if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RunError('Ledger integrity check failed')
        except sqlite3.Error as error:
            raise RunError('Cannot initialize a healthy ledger') from error

    @contextmanager
    def _connection(self):
        db=sqlite3.connect(self.db_path,timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        try:
            db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA temp_store=MEMORY')
            yield db
        finally:
            db.close()

    @contextmanager
    def _transaction(self):
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def _row(self,db,run_id):
        row=db.execute(SELECT_RUN+'WHERE r.run_id=?',(run_id,)).fetchone()
        if row is None:raise RunError('Unknown run')
        return row

    def _check(self,row,state,attempt_id=None):
        if row['active_run']!=row['run_id'] or row['active_generation']!=row['generation']:
            raise RunError('Superseded run cannot change current work')
        if row['state']!=state:raise RunError('Run is not '+state)
        if attempt_id is not None and row['attempt_id']!=attempt_id:
            raise RunError('Attempt is no longer current')

    def _require_attempt(self,attempt_id):
        if type(attempt_id) is not str or len(attempt_id)!=32 or any(c not in '0123456789abcdef' for c in attempt_id):
            raise RunError('A valid current attempt ID is required')

    def _event(self,db,run_id,event,detail=''):
        db.execute('INSERT INTO events(run_id,event,detail,created) VALUES(?,?,?,?)',
                   (run_id,event,detail,datetime.datetime.now(datetime.timezone.utc).isoformat()))

    def _path(self,run_id,attempt_id):
        return self.workspace/'runs'/run_id/attempt_id

    def _view(self,row):
        attempt=row['attempt_id'];path=self._path(row['run_id'],attempt) if attempt else None
        return {'run_id':row['run_id'],'job_key':row['job_key'],'generation':row['generation'],
                'state':row['state'],'attempt_id':attempt,'is_current':row['active_run']==row['run_id'],
                'candidate_sha256':row['c_sha'],'requirements_sha256':row['r_sha'],
                'output_path':str(path/'result.json') if path else None,
                'request_path':str(path/'request.json') if path else None,
                'output_sha256':row['output_sha'],
                'validation':json.loads(row['validation']) if row['validation'] else None,
                'action_authorized':False}

    def _trusted(self,path):
        resolved=Path(path).resolve()
        if resolved==self.workspace or self.workspace in resolved.parents:
            raise RunError('Trusted facts cannot come from agent-writable storage')
        try:return read_bounded(path)
        except (OSError,ValidationInputError) as error:raise RunError('Cannot read bounded trusted facts') from error

    def create(self,job_key,candidate_path,requirements_path):
        job_key=reason(job_key)
        candidate=self._trusted(candidate_path);requirements=self._trusted(requirements_path)
        try:
            c=parse_json(candidate);r=parse_json(requirements);report=evaluate(c,r,{})
        except ValidationInputError as error:raise RunError('Invalid trusted JSON') from error
        if any(x.startswith(('candidate.','requirements.')) for x in report['errors']):
            raise RunError('Invalid trusted facts')
        run_id=uuid.uuid4().hex
        with self._transaction() as db:
            old=db.execute('SELECT generation FROM jobs WHERE job_key=?',(job_key,)).fetchone()
            generation=old[0]+1 if old else 1
            db.execute('INSERT INTO jobs VALUES(?,?,?) ON CONFLICT(job_key) DO UPDATE SET generation=excluded.generation,current_run=excluded.current_run',
                       (job_key,generation,run_id))
            prior=db.execute("SELECT run_id,attempt_id FROM runs WHERE job_key=? AND state IN ('pending','running','interrupted')",(job_key,)).fetchall()
            for item in prior:
                db.execute("UPDATE runs SET state='superseded' WHERE run_id=?",(item['run_id'],))
                if item['attempt_id']:db.execute("UPDATE attempts SET state='superseded' WHERE attempt_id=?",(item['attempt_id'],))
                self._event(db,item['run_id'],'superseded','newer generation created')
            db.execute('INSERT INTO runs(run_id,job_key,generation,candidate,requirements,c_sha,r_sha,state,attempt_id) VALUES(?,?,?,?,?,?,?,?,?)',
                       (run_id,job_key,generation,candidate,requirements,digest(candidate),digest(requirements),'pending',None))
            self._event(db,run_id,'created','trusted inputs snapshotted')
            return self._view(self._row(db,run_id))

    @contextmanager
    def _attempt_fd(self,run_id,attempt_id,create=False):
        if create:self.workspace.mkdir(parents=True,mode=0o700,exist_ok=True)
        flags=os.O_RDONLY|os.O_DIRECTORY|getattr(os,'O_NOFOLLOW',0)
        fd=os.open(self.workspace,flags)
        try:
            for part in ('runs',run_id,attempt_id):
                if create:
                    try:os.mkdir(part,mode=0o700,dir_fd=fd)
                    except FileExistsError:
                        if part==attempt_id:raise
                child=os.open(part,flags,dir_fd=fd);os.close(fd);fd=child
            yield fd
        finally:os.close(fd)

    def claim(self,run_id):
        with self._transaction() as db:
            row=self._row(db,run_id);self._check(row,'pending');attempt=uuid.uuid4().hex
            c=parse_json(row['candidate']);r=parse_json(row['requirements'])
            request={'run_id':run_id,'attempt_id':attempt,'generation':row['generation'],
                     'candidate_sha256':row['c_sha'],'requirements_sha256':row['r_sha'],
                     'candidate':{'skills':c['skills'],'work_authorization':c['work_authorization']},
                     'requirements':{'required_skills':r['required_skills']},
                     'instruction':'Write only the four-field skill-match JSON to result.json in this attempt directory.'}
            try:
                with self._attempt_fd(run_id,attempt,True) as fd:
                    handle=os.open('request.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=fd)
                    with os.fdopen(handle,'wb') as stream:
                        stream.write((json.dumps(request,indent=2)+'\n').encode());stream.flush();os.fsync(stream.fileno())
            except OSError as error:raise RunError('Worker output directory cannot be safely created') from error
            db.execute('INSERT INTO attempts VALUES(?,?,?)',(attempt,run_id,'running'))
            db.execute("UPDATE runs SET state='running',attempt_id=? WHERE run_id=?",(attempt,run_id))
            self._event(db,run_id,'claimed',attempt)
            return self._view(self._row(db,run_id))

    def _output(self,run_id,attempt_id):
        with self._attempt_fd(run_id,attempt_id) as directory:
            flags=os.O_RDONLY|getattr(os,'O_NOFOLLOW',0)|getattr(os,'O_NONBLOCK',0)
            fd=os.open('result.json',flags,dir_fd=directory)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_BYTES:raise ValidationInputError('oversize or special output')
                raw=stream.read(MAX_BYTES+1)
                if len(raw)>MAX_BYTES:raise ValidationInputError('oversize output')
                return raw

    def complete(self,run_id,attempt_id):
        self._require_attempt(attempt_id)
        with self._transaction() as db:
            row=self._row(db,run_id);self._check(row,'running',attempt_id)
            raw=None
            try:
                raw=self._output(run_id,attempt_id)
                try:report=evaluate(parse_json(row['candidate']),parse_json(row['requirements']),parse_json(raw))
                except ValidationInputError:
                    report={'validation_passed':False,'requires_review':True,'errors':['output.invalid_json']}
            except (OSError,ValidationInputError):
                report={'validation_passed':False,'requires_review':True,'errors':['output.unreadable_or_oversize']}
            report.update(action_authorized=False,run_id=run_id,attempt_id=attempt_id,
                          input_sha256={'candidate':row['c_sha'],'requirements':row['r_sha'],
                                        'output':digest(raw) if raw is not None else None})
            state=('review_required' if report['requires_review'] else 'validated') if report['validation_passed'] else 'rejected'
            db.execute('INSERT INTO results VALUES(?,?,?,?,?)',(run_id,attempt_id,raw,digest(raw) if raw is not None else None,json.dumps(report)))
            db.execute('UPDATE runs SET state=? WHERE run_id=?',(state,run_id))
            db.execute('UPDATE attempts SET state=? WHERE attempt_id=?',(state,attempt_id))
            self._event(db,run_id,'completed',state)
            return self._view(self._row(db,run_id))

    def interrupt(self,run_id,attempt_id,operator_reason):
        self._require_attempt(attempt_id)
        text=reason(operator_reason)
        with self._transaction() as db:
            row=self._row(db,run_id);self._check(row,'running',attempt_id)
            db.execute("UPDATE runs SET state='interrupted' WHERE run_id=?",(run_id,))
            db.execute("UPDATE attempts SET state='interrupted' WHERE attempt_id=?",(attempt_id,))
            self._event(db,run_id,'interrupted',text)
            return self._view(self._row(db,run_id))

    def recover(self,run_id,decision,operator_reason):
        text=reason(operator_reason)
        if decision not in ('resume','cancel'):raise RunError('Choose resume or cancel explicitly')
        with self._transaction() as db:
            row=self._row(db,run_id);self._check(row,'interrupted')
            state='pending' if decision=='resume' else 'cancelled'
            db.execute('UPDATE runs SET state=?,attempt_id=NULL WHERE run_id=?',(state,run_id))
            self._event(db,run_id,'recovery_'+decision,text)
            return self._view(self._row(db,run_id))

    def status(self,run_id):
        with self._connection() as db:return self._view(self._row(db,run_id))

    def current(self,job_key):
        with self._connection() as db:
            row=db.execute(SELECT_RUN+'WHERE j.job_key=? AND r.run_id=j.current_run',(job_key,)).fetchone()
            if row is None:raise RunError('Unknown job')
            return self._view(row)

    def evidence(self,run_id):
        with self._connection() as db:
            row=db.execute('SELECT raw,validation FROM results WHERE run_id=?',(run_id,)).fetchone()
            if row is None:raise RunError('No committed result')
            return {'raw':row['raw'],'validation':json.loads(row['validation'])}

    def events(self,run_id):
        with self._connection() as db:
            self._row(db,run_id)
            return [dict(row) for row in db.execute('SELECT event,detail,created FROM events WHERE run_id=? ORDER BY seq',(run_id,))]
