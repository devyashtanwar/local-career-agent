#!/usr/bin/env bash
# Download and extract official pinned user-owned binaries; no daemon or service starts.
set -euo pipefail
[[ "$(uname -s)" == Linux && "$(uname -m)" == x86_64 && "$EUID" != 0 ]] || { echo 'Use a normal user on x86_64 Linux.' >&2; exit 1; }
for program in curl sha256sum tar newuidmap newgidmap; do command -v "$program" >/dev/null; done
directory="$HOME/career-ai/rootless-docker"
mkdir -p "$directory"
cd "$directory"
fetch() {
  local name="$1" expected="$2"
  if [[ ! -f "$name" ]]; then
    curl --fail --location --proto '=https' --proto-redir '=https' --connect-timeout 20 --retry 3 \
      "https://download.docker.com/linux/static/stable/x86_64/$name" -o "$name.part"
    printf '%s  %s\n' "$expected" "$name.part" | sha256sum --check --status
    mv "$name.part" "$name"
  fi
  printf '%s  %s\n' "$expected" "$name" | sha256sum --check --status
  tar -xzf "$name"
}
# Observed artifact hashes from the initial official-source download; not vendor signatures.
fetch docker-29.9.3.tgz 3fb5d1f13014c18cc54945bc177c58a9056a482dada031e17d12cf2e6922c973
fetch docker-rootless-extras-29.9.3.tgz c41b7194dca722fe929bc0225fc87f3166c97e67d50a521533b0b23f3c79a466
export PATH="$directory/docker:$directory/docker-rootless-extras:$PATH"
dockerd-rootless-setuptool.sh check
echo 'Binaries prepared; no service installed. Start the foreground launcher explicitly when ready.'
