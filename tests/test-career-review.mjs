import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,chmodSync,rmSync,existsSync,readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import plugin from '../extensions/career-review/index.mjs';

test('Telegram command plugin: real adapter plus admission checks', async () => {
  const root=mkdtempSync(join(tmpdir(),'career-review-'));
  try {
    const owner='123456789', facts=join(root,'facts.json'), settings=join(root,'settings.json');
    writeFileSync(facts,JSON.stringify({local:'I am setting up a local AI assistant.'}),{mode:0o600});
    writeFileSync(settings,JSON.stringify({owner,facts,database:join(root,'state/reviews.sqlite3')}),{mode:0o600});
    let command;
    plugin.register({pluginConfig:{owner,repo:resolve('.'),python:process.env.CAREER_TEST_PYTHON||'python3',settingsFile:settings},registerCommand:c=>command=c});
    assert.equal(command.requireAuth,true);
    assert.deepEqual(command.channels,['telegram']);
    const ctx={channel:'telegram',isAuthorizedSender:true,senderId:owner,from:'telegram:'+owner,accountId:'default'};
    for (const patch of [{channel:'webchat'},{senderId:'other'},{isAuthorizedSender:false},{from:'telegram:group:-100'},{from:undefined},{accountId:'other'},{messageThreadId:1},{threadParentId:'x'}]) {
      const result=await command.handler({...ctx,...patch,args:'new gate local'});
      assert.match(result.text,/restricted/);
    }
    assert.equal(existsSync(join(root,'state/reviews.sqlite3')),false);
    const help=await command.handler({...ctx,args:'help'});assert.match(help.text,/no publishing/);
    const first=await command.handler({...ctx,args:'new LIVE-TEST local'});
    assert.match(first.text,/I am setting up a local AI assistant/);
    assert.match(first.text,/SHA-256: [a-f0-9]{64}/);
    const id=first.text.match(/Request: ([a-f0-9-]+)/)[1];
    const repeated=await command.handler({...ctx,args:'new LIVE-TEST local'});assert.equal(repeated.text,first.text);
    const approved=await command.handler({...ctx,args:'approve '+id});assert.match(approved.text,/Status: approved/);
    const replay=await command.handler({...ctx,args:'approve '+id});assert.match(replay.text,/no longer pending/);
    const status=await command.handler({...ctx,args:'status '+id});assert.match(status.text,/Status: approved/);
    const rejected=await command.handler({...ctx,args:'new REJECT-TEST local'});
    const rejectId=rejected.text.match(/Request: ([a-f0-9-]+)/)[1];
    assert.match((await command.handler({...ctx,args:'reject '+rejectId})).text,/Status: rejected/);
    for(const args of ['new x privacy','new x local;whoami','approve TEST-001','approve '+id+' and publish']) {
      assert.match((await command.handler({...ctx,args})).text,/Review refused/);
    }
  } finally {rmSync(root,{recursive:true,force:true});}
});

test('Manifest activates and owns the native slash command', () => {
 const manifest=JSON.parse(readFileSync(new URL('../extensions/career-review/openclaw.plugin.json',import.meta.url),'utf8'));
 assert.equal(manifest.activation.onStartup,true);
 assert.ok(manifest.commandAliases.some(command=>command.name==='careerreview' && command.kind==='runtime-slash'));
});
