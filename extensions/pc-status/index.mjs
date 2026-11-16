import {execFile} from 'node:child_process';
export default {
 id:'pc-status',name:'Read-only PC status',
 register(api){
  const cfg=api.pluginConfig;
  if(!cfg||!Array.isArray(cfg.allowedUsers)||!cfg.allowedUsers.length||cfg.allowedUsers.some(id=>typeof id!=='string'||!/^[0-9]+$/.test(id)))throw new Error('Status allowlist required');
  api.registerCommand({name:'pcstatus',description:'Read-only GPU, RAM, disk and service status',acceptsArgs:true,requireAuth:true,channels:['telegram'],handler:async ctx=>{
   if(ctx.channel!=='telegram'||ctx.isAuthorizedSender!==true||!cfg.allowedUsers.includes(ctx.senderId)||![ctx.senderId,'telegram:'+ctx.senderId].includes(ctx.from)||(ctx.accountId!==undefined&&ctx.accountId!=='default')||ctx.messageThreadId!==undefined||ctx.threadParentId!==undefined)return {text:'PC status is restricted to authorized private Telegram chats.'};
   if((ctx.args??'')==='help')return {text:'Send /pcstatus with no arguments. It reads fixed host metrics only; it cannot run commands or change services.'};
   if((ctx.args??'')!=='')return {text:'Use /pcstatus without arguments. Arbitrary commands are not supported.'};
   try{
    const text=await new Promise((resolve,reject)=>{execFile(cfg.python,['-m','operations.pc_status'],{cwd:cfg.repo,timeout:10000,maxBuffer:16384,shell:false},(error,stdout)=>{
     if(error)return reject(new Error('collector failed'));
     try{const data=JSON.parse(stdout);if(data.action_authorized!==false||typeof data.text!=='string')throw new Error('invalid report');resolve(data.text);}catch{reject(new Error('invalid report'));}
    });});return {text};
   }catch{return {text:'PC status collector unavailable. No system changes performed.'};}
  }});
 }
};
