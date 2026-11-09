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
- An agent must show its human the share summary (file list, audience, expiry) before `approve`. A public link is
  readable by anyone who has it. The link is shown once. Deleting needs the human's yes (`delete --yes`); never pass
  `--yes` on your own.
- In MCP mode the credential file must be mode 0600 and is never printed or logged; `share` only creates a pending
  share and `share approve` is a separate command run after the human's yes.

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
5. Return logical artifact ID, job ID, and current status, then run the completion handoff
   below. Keep the artifact private unless the user separately requests `share-request`.

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
7. Hand the artifact back per the completion handoff: IDs, version-pinned links, context
   links, and the recorded checks — unprompted.

## Completion handoff (IDs and links, unprompted)

Every registered artifact or new version ends by handing back the IDs and the links that open it. Do this without
being asked. A bare artifact ID is not a handoff, and a version ID the operator has to assemble a URL from is not
either.

Report, in this order:

- artifact ID, then the current version ID — `herdr-eng artifacts show <A> --json` reports
  `current_version_id`; reread it instead of reusing the build response, and say which version each link pins;
- job ID and its persisted status (`herdr-eng artifacts reports status`), because `queued` is not an artifact yet;
- the preview URL for that exact version and the library listing URL;
- the context links attached (project, task, issue, room) and the project-scoped listing that proves someone else
  can find it;
- the checks recorded on that version (`rendered`, `evidence_checked`, `reviewed`) and which are still unsigned.

Build the URLs on the origin the API answered on — the configured control-plane URL, or the `--control-plane`
actually passed:

```text
<control-plane>/api/v1/artifacts/<artifact_id>/versions/<version_id>/preview
<control-plane>/api/v1/library
```

Never substitute another service's hostname because it resolves and answers `200`: a fronting single-page app
replies to unknown `/api/...` paths with a few kilobytes of HTML shell, which looks exactly like a served report.
Prove a link before calling it verified — fetch the preview and check that it is a real document (tens of kilobytes
up to the preview cap, not a couple of kilobytes of shell and not a short `400`/`404` body), and download one asset
with `reports download` and compare its SHA-256 with the upload response. Do not compare the preview's byte count
with the artifact's `size_bytes`: that number covers the stored payload and its supporting assets, not the bounded
preview.

Registry presence is not discoverability. Project-scoped views list nothing until the artifact is linked:
`herdr-eng artifacts link <A> --project <id> --link-kind origin`, then `herdr-eng artifacts for project <id>` to
show it there. Link it as part of finishing, not as a gap the operator discovers later.

Offer the same URLs on the operator's device through the `herdr-open` launcher
(`skills/herdr-open/scripts/open-client.py`: `discover --url ...`, then `show --select <id>`) and report transfer
and launch separately; an offer is not proof the page was seen. If the device cannot reach that address, resolve
the existing fabric service route rather than printing an unreachable link. A bearer share token never appears in
these links and is never written into a file — public exposure stays the separate approval workflow below.

## Share links (safety contract)

Sharing is owner-approved and never automatic. Use `herdr-eng artifacts share create` to make a pending share
(audience `lab` with an allow-list, or `public`), show the user the exposure summary, and run `share approve` only
after the user has seen it and said yes; pass `--yes` only on that explicit instruction. Never approve on your own,
never widen an audience, and never invent recipients. The URL is a bearer secret shown once at approval: give it
only to the user, do not log it or write it into files, and use `share revoke` if it leaks. See
`references/share-commands.md`.

## MCP mode (member artifacts)

Without `herdr-eng` (or when its control plane is unreachable), and with an `mcp:` block in
`~/.config/herdr/artifact.yaml`, `scripts/herdr-artifact` runs `scripts/herdr-artifact-mcp`: `create`, `publish`
(chunked, resumable), `share` (stops before approve), `share approve`, `links`, `list`, `revoke`, `delete --yes`.
`--mode mcp|cli` forces a mode. See `references/mcp-mode.md`.
