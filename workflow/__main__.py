"""Explicit local workflow controls; no worker or account action is auto-started."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from workflow.ledger import Ledger,RunError


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root',type=Path,default=Path.home()/'career-ai/workflow-state')
    parser.add_argument('--workspace',type=Path,default=Path.home()/'career-ai/workspace')
    commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create');create.add_argument('--job',required=True)
    create.add_argument('--candidate',type=Path,required=True);create.add_argument('--requirements',type=Path,required=True)
    for name in ('claim','complete','interrupt','recover','status','events'):
        command=commands.add_parser(name);command.add_argument('run_id')
        if name in ('complete','interrupt'):command.add_argument('--attempt',required=True)
        if name in ('interrupt','recover'):command.add_argument('--reason',required=True)
        if name=='recover':command.add_argument('--decision',choices=['resume','cancel'],required=True)
    current=commands.add_parser('current');current.add_argument('job')
    args=parser.parse_args(argv)
    try:
        ledger=Ledger(args.state_root,args.workspace)
        if args.command=='create':result=ledger.create(args.job,args.candidate,args.requirements)
        elif args.command=='claim':result=ledger.claim(args.run_id)
        elif args.command=='complete':result=ledger.complete(args.run_id,args.attempt)
        elif args.command=='interrupt':result=ledger.interrupt(args.run_id,args.attempt,args.reason)
        elif args.command=='recover':result=ledger.recover(args.run_id,args.decision,args.reason)
        elif args.command=='status':result=ledger.status(args.run_id)
        elif args.command=='current':result=ledger.current(args.job)
        else:result={'events':ledger.events(args.run_id),'action_authorized':False}
    except RunError as error:
        print(json.dumps({'error':str(error),'action_authorized':False}))
        return 2
    except (OSError,sqlite3.Error):
        print(json.dumps({'error':'ledger unavailable; no action authorized','action_authorized':False}))
        return 1
    print(json.dumps(result,indent=2))
    return 2 if result.get('state')=='rejected' else 0


if __name__=='__main__':sys.exit(main())
