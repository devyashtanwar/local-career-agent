"""Trusted command adapter. No polling, networking, model calls or account actions."""
import argparse
import datetime
import json
from pathlib import Path
import re
import sys
from workflow.draft_approval import ApprovalStore

HELP = ('Career draft review (no publishing).\n'
        'new TASK local,model,telegram,test,development\n'
        'status REQUEST-UUID\napprove REQUEST-UUID\nreject REQUEST-UUID\n'
        'Only approved statement IDs are accepted. Approval records review only.')
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def latest(store, task=None, request_id=None):
    from contextlib import closing
    with closing(store.connect()) as db:
        if task is not None:
            row = db.execute('SELECT * FROM approvals WHERE task=? ORDER BY generation DESC LIMIT 1', (task,)).fetchone()
        else:
            row = db.execute('SELECT * FROM approvals WHERE id=?', (request_id,)).fetchone()
    if row is None: raise ValueError('unknown request')
    return store.public(row)


def format_review(request):
    expiry = datetime.datetime.fromtimestamp(request['expires'], datetime.timezone.utc).isoformat()
    status = request['status']
    if status == 'pending' and request['expires'] <= __import__('time').time(): status = 'expired (awaiting persisted decision)'
    return ('Career draft review\nTask: '+request['task']+'\nRevision: '+str(request['generation'])+
            '\nRequest: '+request['id']+'\nStatus: '+status+'\nExpires (UTC): '+expiry+
            '\nSHA-256: '+request['digest']+'\n\n'+request['draft']+
            '\n\n/careerreview approve '+request['id']+
            '\n/careerreview reject '+request['id']+
            '\n\nReview only. Nothing is published or submitted.')


def handle(settings, actor, args):
    if type(actor) is not str or actor != settings['owner']:
        raise ValueError('unauthorized sender')
    if type(args) is not str or len(args) > 1000: raise ValueError('invalid command')
    if args in ('', 'help'): return {'text': HELP, 'action_authorized': False}
    store = ApprovalStore(settings['database'], settings['owner'])
    new = re.fullmatch(r'new ([A-Za-z0-9_-]{1,64}) ([A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*)', args)
    if new:
        facts = json.loads(Path(settings['facts']).read_text())
        selection = new[2].split(',')
        try: request = store.create(new[1], facts, selection)
        except ValueError as error:
            if str(error) != 'duplicate task revision': raise
            request = latest(store, task=new[1])
        return {'text': format_review(request), 'request': request, 'action_authorized': False}
    query = re.fullmatch('(status|approve|reject) ('+UUID+')', args)
    if query:
        if query[1] == 'status': request = latest(store, request_id=query[2])
        else: request = store.decide_message(actor, query[1].upper()+' '+query[2])
        return {'text': format_review(request), 'request': request, 'action_authorized': False}
    raise ValueError('invalid command; use /careerreview help')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings', required=True)
    options = parser.parse_args()
    settings_path = Path(options.settings)
    if settings_path.is_symlink() or settings_path.stat().st_mode & 0o077:
        raise ValueError('settings must be a private regular file')
    settings = json.loads(settings_path.read_text())
    message = json.loads(sys.stdin.read(4097))
    if type(message) is not dict or set(message) != {'actor', 'args'}: raise ValueError('invalid envelope')
    try: result = handle(settings, message['actor'], message['args'])
    except ValueError as error: result = {'text': 'Review refused: '+str(error), 'action_authorized': False}
    print(json.dumps(result))

if __name__ == '__main__': main()
