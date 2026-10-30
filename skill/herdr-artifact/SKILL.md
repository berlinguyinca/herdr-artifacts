---
name: herdr-artifact
description: Create, inspect, edit, validate, version, materialize, and request publication of Herdr artifacts, including evidence-based investigation reports, through the shared fabric registry.
---

# HerdR Artifact Skill

The preferred user-facing command is `/herdr::artifact`. The standalone
`herdr-artifact` skill name remains a compatibility alias for harnesses that
do not support namespaced commands.

Use the authenticated HerdR control-plane API as the artifact authority. RustFS
holds immutable bytes; PostgreSQL holds logical IDs, versions, provenance,
reviews, bindings, and publication state.

## Safety contract

- Artifacts and versions are private by default.
- Never send S3 credentials, source worktree paths, or raw binary payloads into
  collaboration event streams.
- Every edit commits with `base_version_id`; a stale head is a conflict, never
  an automatic overwrite.
- Preserve editable source, manifests, dependencies, rendered outputs, and
  validation reports.
- `share-request` creates a pending human approval request. It never activates
  public access itself.
- Public URLs must pin an immutable version and are revocable/expiring.

## Command contract

The implementation may be exposed through `herdr-eng artifacts` or an external
compatible wrapper. Commands must return structured JSON and use the same API:

```text
create       register a logical artifact and initial source manifest
checkout     materialize an immutable version into an authorized workspace
inspect      show metadata, provenance, bindings, and current head
edit         create a new version from an explicit base version
validate     run format/profile validation and preserve its report
publish      commit a version with --base-version; never means public share
history      list immutable versions and review state
diff         compare two authorized immutable versions
materialize  place a verified version on a specific authorized host/session
bundle       export a deterministic collection of pinned version IDs
share-request request approval for an unlisted/guest/public publication
generate     create an artifact from the current session/mission context
```

Supported profiles are `web`, `document`, `diagram`, `visualization`,
`presentation`, and `report`. Unsupported profiles must return a structured
`unsupported_format` result rather than silently falling back.

Check the installed wrapper/CLI and authenticated API capabilities before using
this command contract. The command list describes the intended interface; it does
not prove that a particular installed wrapper implements every operation or that
a renderer supports rich HTML, linked assets, or large inputs. Report capability
gaps explicitly rather than inventing a command or claiming an artifact exists.

## Investigation and comparison reports

For research, benchmarking, audits, simulations, or other evidence-based reports,
read [the generic report workflow](references/report-workflow.md). Use it both
when generating a report and when importing an existing report package.

For descriptor-based reports, use [native report commands and examples](references/report-commands.md).
`scripts/herdr-artifact report ...` delegates to `herdr-eng artifacts reports`;
check its installed `--help` before use. The reference covers scoped asset uploads,
worker builds, categorized diffs, attributed check stages, version-pinned feedback,
and private previews/downloads. The bundled schema and two synthetic examples
support authoring; local validation does not register a report or verify evidence.

The reusable layer preserves evidence, explains visualizations, connects findings
to their supporting results, records limitations, and proposes follow-up work.
Domain calculations, units, metrics, thresholds, cohorts, and decision policies
belong in the report's analysis adapter and recorded configuration, not in this
skill. Qualitative investigations do not need invented numerical scores.

An existing rendered report is an input to preserve, not a reason to regenerate
its evidence from session summaries. Separate analysis provenance from later
explanation/render revisions. Keep substantive data and source in authorized
artifact storage; publish only bounded metadata and references in collaboration
events. Follow the existing privacy, worker, versioning, and publication contracts.

## Natural-language generation

When the user says “generate an artifact about the current session”, “turn
this into an HTML report”, or equivalent:

1. Resolve the available authenticated principal, session, mission, host, and agent
   context from the harness or explicit arguments. Omit unknown optional IDs; if
   the actual API requires unavailable identity or authorization, report that
   blocker. Never invent missing IDs.
2. Build bounded source input from authorized session/mission records only;
   exclude credentials, hidden reasoning, private prompts, and unrelated rooms.
3. Submit an `artifact-job` through a verified authenticated control-plane path.
   Use `generate` only when the installed client implements it as an entry point
   to that job mechanism; otherwise discover the supported job API or report the
   capability gap. Rendering runs through the existing worker/scheduler boundary,
   not inside the browser or skill process.
4. Preserve editable source, input references, generated manifest, output
   blobs, validation report, renderer/toolchain revision, host, session, and
   mission provenance.
5. Return logical artifact ID, job ID, and current status. Keep the artifact
   private unless the user separately requests `share-request`.

The skill may use React/TypeScript/HTML templates and deterministic renderers,
but it must not vendor or copy proprietary upstream Claude/Anthropic skill
materials. Reproduce the useful source-preservation, bundling, rendering, and
validation workflow through native HerdR APIs.

## Edit workflow

1. Search the registry before creating a duplicate artifact.
2. Checkout a pinned version into an isolated temporary workspace.
3. Preserve source/manifests and run validation/render checks.
4. Commit with the exact `base_version_id` and an idempotency key.
5. Attach the artifact/version to existing mission, session, room, issue, or
   commit relationships using their explicit IDs.
6. Request sharing separately if a human wants an external publication.

## Share links (safety contract)

Sharing is owner-approved and never automatic. Use `herdr-eng artifacts share create` to make a pending share
(audience `lab` with an allow-list, or `public`), show the user the exposure summary, and run `share approve` only
after the user has seen it and said yes; pass `--yes` only on that explicit instruction. Never approve on your own,
never widen an audience, and never invent recipients. The URL is a bearer secret shown once at approval: give it
only to the user, do not log it or write it into files, and use `share revoke` if it leaks. See
`references/share-commands.md`.
