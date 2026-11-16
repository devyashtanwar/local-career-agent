import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import plugin from '../extensions/pc-status/index.mjs';
test('Native status command rejects extra authority and reads real host without the LLM',async()=>{
 let command;plugin.register({pluginConfig:{allowedUsers:['123456789'],repo:resolve('.'),python:'python3'},registerCommand:c=>command=c});
 assert.equal(command.requireAuth,true);assert.deepEqual(command.channels,['telegram']);
 const ctx={channel:'telegram',isAuthorizedSender:true,senderId:'123456789',from:'telegram:123456789',accountId:'default'};
 for(const patch of [{channel:'webchat'},{isAuthorizedSender:false},{senderId:'other'},{from:'telegram:group:-123'},{from:undefined},{accountId:'other'},{messageThreadId:1},{threadParentId:'x'}]){
  assert.match((await command.handler({...ctx,...patch})).text,/restricted/);
 }
 for(const args of ['nvidia-smi','; touch /tmp/should-not-exist','restart',' '])assert.match((await command.handler({...ctx,args})).text,/without arguments/);
 assert.match((await command.handler({...ctx,args:'help'})).text,/fixed host metrics/);
 const status=await command.handler(ctx);assert.ok(status.text.startsWith('PC status (read-only)'));assert.match(status.text,/Services:/);assert.match(status.text,/No system changes performed/);
});
test('Status manifest declares startup activation and command ownership',()=>{
 const m=JSON.parse(readFileSync(new URL('../extensions/pc-status/openclaw.plugin.json',import.meta.url),'utf8'));
 assert.equal(m.activation.onStartup,true);assert.ok(m.commandAliases.some(c=>c.name==='pcstatus'&&c.kind==='runtime-slash'));
});
