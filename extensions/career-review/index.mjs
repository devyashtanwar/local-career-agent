import { execFile } from 'node:child_process';

export default {
  id: 'career-review',
  name: 'Career draft review',
  description: 'Owner-only deterministic draft reviews; no model tools.',
  configSchema: {jsonSchema: {
    type: 'object', additionalProperties: false,
    properties: {owner: {type: 'string', pattern: '^[0-9]+$'}, repo: {type:'string'}, python: {type:'string'}, settingsFile: {type:'string'}},
    required: ['owner','repo','python','settingsFile']
  }},
  register(api) {
    const cfg = api.pluginConfig;
    if (!cfg || !/^[0-9]+$/.test(cfg.owner)) throw new Error('Review owner configuration required');
    api.registerCommand({
      name: 'careerreview',
      description: 'Review exact career drafts: help, new, status, approve, reject',
      acceptsArgs: true, requireAuth: true, channels: ['telegram'],
      handler: async ctx => {
        const privateIds = [cfg.owner, 'telegram:'+cfg.owner];
        if (ctx.channel !== 'telegram' || ctx.isAuthorizedSender !== true ||
            ctx.senderId !== cfg.owner || !privateIds.includes(ctx.from) ||
            (ctx.accountId !== undefined && ctx.accountId !== 'default') ||
            ctx.messageThreadId !== undefined || ctx.threadParentId !== undefined) {
          return {text:'Career reviews are restricted to the authorized private Telegram chat.'};
        }
        const args = ctx.args ?? '';
        if (typeof args !== 'string' || args.length > 1000) return {text:'Invalid review command.'};
        try {
          const text = await new Promise((resolve, reject) => {
            const child = execFile(cfg.python, ['-m','workflow.telegram_review','--settings',cfg.settingsFile],
              {cwd:cfg.repo, timeout:10000, maxBuffer:16384, shell:false}, (error, stdout) => {
                if (error) return reject(new Error('Review adapter failed'));
                try {
                  const result = JSON.parse(stdout);
                  if (result.action_authorized !== false || typeof result.text !== 'string') throw new Error('Invalid adapter result');
                  resolve(result.text);
                } catch {reject(new Error('Review adapter response invalid'));}
              });
            child.stdin.on('error', () => {});
            child.stdin.end(JSON.stringify({actor:ctx.senderId, args}));
          });
          return {text};
        } catch {
          return {text:'Review unavailable. No action was authorized. Ask the operator to inspect the local adapter.'};
        }
      }
    });
  }
};
