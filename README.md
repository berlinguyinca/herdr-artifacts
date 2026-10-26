# herdr-artifacts

Canonical cross-harness artifact skill and client contract for HerdR.

`herdr-artifact` lets Codex, Claude Code, Pi, and OpenCode agents create,
inspect, edit, validate, version, materialize, bundle, diff, and request
publication of artifacts through the HerdR Artifact Registry. Bytes remain in
RustFS/S3-compatible storage; PostgreSQL owns metadata, permissions, versions,
provenance, reviews, and publication state.

Private is the default. `share-request` only creates a pending human approval
request; it never activates public access.

## Install all harnesses

From a clone:

```bash
./install/install.sh
```

The installer links the skill into Codex, Claude Code, Pi, and OpenCode skill
directories. Existing non-symlink installations are backed up before linking.
Use `HERDR_ARTIFACT_SKILL_ROOT` to select a different destination root, or set
`CODEX_HOME`, `CLAUDE_SKILLS_DIR`, `PI_SKILLS_DIR`, and
`OPENCODE_SKILLS_DIR` explicitly.

## Use

```text
Generate an artifact about the current session as a private HTML report.
Create a web artifact from this source and preserve the editable source.
Show artifact history for artifact_123.
Request an unlisted public link for version_7; do not publish automatically.
```

## Relationship to herdr-engineering

`berlinguyinca/herdr-engineering` provides the registry, API, worker, storage,
dashboard, and gateway. This repository provides the reusable agent-facing
skill and wrapper. The engineering repository may vendor or install this skill
at `skills/herdr-artifact` during development, but the standalone repository is
the canonical distribution source.

## Upstream inspiration

The workflow is independently implemented from general concepts such as source
preservation, deterministic bundling, rendering, and validation. Anthropic
skill source, prompts, assets, and generated project files are not vendored.
