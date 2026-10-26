#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
skill_source="$repo_root/skill/herdr-artifact"
[ -f "$skill_source/SKILL.md" ] || { echo "missing skill source: $skill_source" >&2; exit 1; }

root=${HERDR_ARTIFACT_SKILL_ROOT:-}
if [ -n "$root" ]; then
  codex_dir="$root/codex/skills"
  claude_dir="$root/claude/skills"
  pi_dir="$root/pi/skills"
  opencode_dir="$root/opencode/skills"
else
  codex_home=${CODEX_HOME:-$HOME/.codex}
  codex_dir="$codex_home/skills"
  claude_dir=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
  pi_dir=${PI_SKILLS_DIR:-$HOME/.pi/agent/skills}
  opencode_dir=${OPENCODE_SKILLS_DIR:-$HOME/.config/opencode/skills}
fi

install_one() {
  destination="$1/herdr-artifact"
  mkdir -p "$(dirname "$destination")"
  if [ -e "$destination" ] || [ -L "$destination" ]; then
    if [ -L "$destination" ] && [ "$(readlink "$destination")" = "$skill_source" ]; then
      return 0
    fi
    echo "collision: leaving existing $destination unchanged" >&2
    return 0
  fi
  ln -s "$skill_source" "$destination"
  echo "installed $destination"
}

install_one "$codex_dir"
install_one "$claude_dir"
install_one "$pi_dir"
install_one "$opencode_dir"
