#!/usr/bin/env bash
export DO_NOT_TRACK=1 OPENCLAW_NO_AUTO_UPDATE=1
export PATH="$HOME/career-ai/rootless-docker/docker:$HOME/career-ai/rootless-docker/docker-rootless-extras:$HOME/.local/share/mise/installs/node/lts/bin:$HOME/.lmstudio/bin:$PATH"
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
unset DOCKER_CONTEXT
