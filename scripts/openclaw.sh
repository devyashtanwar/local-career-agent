#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
docker info --format '{{json .SecurityOptions}}' | grep -q 'name=rootless' || { echo 'Start run-rootless-docker.sh in a visible terminal first.' >&2; exit 1; }
exec "$HOME/career-ai/openclaw/runtime/bin/openclaw" "$@"
