#!/usr/bin/env bash
# User-local install only. Does not start a gateway or connect any account.
set -euo pipefail
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 && "$EUID" != 0 ]] || { echo 'Use a normal user on x86_64 Linux.' >&2; exit 1; }
node -e 'const [a,b,c]=process.versions.node.split(".").map(Number); if (!((a===24 && (b>16 || (b===16 && c>=0))) || (a===26 && b>=1))) { console.error("Pinned OpenClaw requires Node >=24.16 <25 or >=26.1 <27; tested on 24.22.1"); process.exit(1); }'
export DO_NOT_TRACK=1 OPENCLAW_NO_AUTO_UPDATE=1
directory="$HOME/career-ai/openclaw"
mkdir -p "$directory/runtime"
npm install --global --prefix "$directory/runtime" openclaw@2026.11.3 --allow-scripts=openclaw --no-fund --no-audit
for name in env.sh openclaw.sh run-gateway.sh run-rootless-docker.sh; do
  install -m 700 "$(dirname "$0")/$name" "$directory/$name"
done
"$directory/runtime/bin/openclaw" --version
echo 'Installed. Configuration, isolation and explicit foreground startup are separate steps; see docs/setup.md.'
