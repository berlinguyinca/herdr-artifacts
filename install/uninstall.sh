#!/bin/sh
set -eu

for root in "${CODEX_HOME:-$HOME/.codex}/skills" "${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}" "${PI_SKILLS_DIR:-$HOME/.pi/agent/skills}" "${OPENCODE_SKILLS_DIR:-$HOME/.config/opencode/skills}"; do
  target="$root/herdr-artifact"
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$(CDPATH= cd -- "$(dirname -- "$0")/../skill/herdr-artifact" && pwd)" ]; then
    rm "$target"
    echo "removed $target"
  fi
done
