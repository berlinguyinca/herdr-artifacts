# herdr-artifacts

Canonical cross-harness artifact skill and client contract for HerdR.

`/herdr::artifact` (with `herdr-artifact` retained as a compatibility alias)
lets Codex, Claude Code, Pi, and OpenCode agents create,
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
directories. Existing skill installations are never overwritten; collisions are
reported and the namespaced `/herdr::artifact` route remains the safe contract.
Use `HERDR_ARTIFACT_SKILL_ROOT` to select a different destination root, or set
`CODEX_HOME`, `CLAUDE_SKILLS_DIR`, `PI_SKILLS_DIR`, and
`OPENCODE_SKILLS_DIR` explicitly.

## Use

```text
Generate an artifact about the current session as a private HTML report.
Create a web artifact from this source and preserve the editable source.
Show artifact history for artifact_123.
Request an unlisted public link for version_7; do not publish automatically.
Create a private investigation report comparing these alternatives; explain each chart and propose follow-up experiments.
Import this existing report with its evidence, editable source, and provenance; keep analysis separate from explanation revisions.
```

## Evidence-based reports

The skill includes a [generic investigation-report workflow](skill/herdr-artifact/references/report-workflow.md):
readable findings, evidence links, chart explanations, comparison qualifications,
limitations, and concrete next checks. It applies across research, benchmarking,
audits, simulations, and operational investigations. Domain calculations and
decision policies remain in analysis adapters and recorded configuration.

The workflow also covers importing existing reports and revising explanations
without pretending the analysis was rerun. Evidence, editable source, outputs,
interpretation, and validation belong to a reproducible artifact version.

The wrapper exposes `herdr-artifact report ...` as a thin route to native
`herdr-eng artifacts reports ...`. See the
[command reference](skill/herdr-artifact/references/report-commands.md) for descriptor
authoring, scoped uploads, worker builds, semantic diffs, attributed checks,
version-pinned feedback, and private previews/downloads. It includes the v1 schema
and runnable synthetic benchmark and qualitative audit examples.

```sh
skill/herdr-artifact/scripts/herdr-artifact report --help
skill/herdr-artifact/scripts/herdr-artifact report validate skill/herdr-artifact/assets/report-examples/incident-audit.json
```

Local `validate` checks structure and references only. Builds require a compatible
authenticated control plane, report migration and worker. The skill does not
deploy these services or register a report merely by validating its source.

The command contract is broader than the small compatibility wrapper. Check the
installed CLI/API and renderer before assuming multi-file imports, rich HTML,
large-asset support, or private dashboard previews are available. Skill guidance
does not itself add those runtime capabilities or register existing local reports.

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

## Verify the integration

With `herdr-eng` on PATH and the runtime's existing `jsonschema` test dependency
available, run `python3 -m unittest discover -s tests -v`. The tests
exercise argument/exit forwarding, preserve raw-upload aliases, validate both
example descriptors through the native CLI and schema, and verify asset hashes.
