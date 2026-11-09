# Native report commands

Use this reference with the [report workflow](report-workflow.md) when the installed
runtime exposes `herdr-eng artifacts reports --help`. The skill's executable
`scripts/herdr-artifact report ...` delegates arguments and exit status directly
to that native group. A missing command is a runtime capability gap; installing
this skill alone does not install the registry, worker, or database migration.

Every remote subcommand accepts `--control-plane URL` and `--api-key-env NAME`.
Use the configured trusted control-plane URL and a credential already provided
through the named environment variable (`HERDR_API_KEY` by default). Pass the
variable's name, never its value. Omitted URLs use native host configuration.
Do not read credentials into prompts, reports, or command output.

## Commands and meaning

In this table, `A`, `V`, `BASE`, and `JOB` mean actual IDs returned by the registry.
`D` is a descriptor JSON path. These symbols are placeholders, not usable IDs.

| Command after `herdr-artifact report` | Result |
| --- | --- |
| `validate D` | Local descriptor shape/reference check; evidence remains `not_checked` |
| `create --title TITLE` | Register a private logical report; no built version yet |
| `upload-asset A FILE --name RELATIVE_NAME --mime TYPE` | Stream a supporting asset into this artifact's scope; retain the returned JSON |
| `build A --base-version BASE --descriptor D --assets UPLOADS_JSON` | Queue worker rendering from descriptor and scoped uploads; use `none` only for the initial version |
| `status A JOB` | Read persisted job status; queued/running is not a completed version |
| `versions A` | Lightweight immutable version history |
| `inspect A V` | Descriptor, attributed check states, first feedback page, asset metadata and private preview reference |
| `diff A V --base-version BASE` | Categorized differences against a version in the same artifact |
| `feedback A V --target-kind finding --target-id ID --body TEXT` | Append feedback to that exact finding/version; also supports `figure` or `report` |
| `feedback-list A V --limit 10 --offset 0` | Bounded page, total and `has_more`; default 10, maximum 20 |
| `check A V --stage STAGE --status passed\|failed --notes TEXT --evidence-ref REF` | Record the authenticated actor's actual check and supporting descriptor references |
| `preview A V --output preview.html` | Save a bounded metadata-only HTML preview |
| `download A V ASSET_ID --output FILE` | Explicitly download a supporting asset and verify its pinned size and SHA-256 |

For whole-report feedback omit `--target-id`. A finding/figure ID must exist in
that version. Read subsequent feedback pages while `has_more` is true, advancing
the offset by the number of returned entries. Feedback is not copied onto future
versions or silently moved when a finding is removed.

## Descriptor and assets

Use the bundled [v1 JSON schema](artifact-report-v1.schema.json) for authoring and
the native `validate` command for additional size and cross-reference checks.
Keep question, evidence, finding, figure, and asset IDs stable across revisions.
Findings link to questions and evidence; figures link to a separately stored asset
and explain their interpretation. `analysis` records the method, configuration,
code revision and source hashes when known.

The descriptor is capped at 512 KiB. Each asset upload is capped at 1 GiB. Use a
safe relative name and a bare MIME type such as `text/csv`, without parameters.
The descriptor asset's `name`, `media_type`, `sha256`, and `size_bytes` must match
the upload response. Keep the response's storage reference in the uploads JSON
array passed to `--assets`; do not invent or copy another artifact's storage key.
An asset-free qualitative descriptor can omit `--assets`.

The examples are synthetic and local, not registered artifacts:

- [Benchmark descriptor](../assets/report-examples/benchmark.json), with
  [CSV summaries](../assets/report-examples/evidence/summaries.csv) and
  [SVG figure](../assets/report-examples/figures/means.svg). The digests and sizes
  match the included files. Device differences and missing variability prevent a
  causal conclusion even though the candidate's displayed mean is lower.
- [Incident-audit descriptor](../assets/report-examples/incident-audit.json), with
  qualitative observations and follow-ups, no figures or fabricated scores.

From the skill directory, these commands validate both examples without network
access or registration:

```sh
scripts/herdr-artifact report validate assets/report-examples/benchmark.json
scripts/herdr-artifact report validate assets/report-examples/incident-audit.json
```

To build your own report, create the logical artifact, upload each authorized
supporting file to that returned artifact ID, assemble the upload results as a
JSON array, and replace descriptor asset metadata with those exact results.
Submit `build` with the current base version, follow `status` to completion, then
inspect the returned version. A stale base requires rereading the current head
and reconciling the revision, not forcing an overwrite.

## Interpret differences and checks

Diff categories are `data`, `analysis`, `editorial`, and `presentation`. Several
categories can change together. They classify descriptor changes; they do not
prove that an analysis was rerun or that new evidence validates a claim. Inspect
the category counts and truncation/omission notices before treating displayed
details as exhaustive. Preserve original analysis provenance for editorial edits.

The independent check stages are `rendered`, `evidence_checked`, and `reviewed`.
Worker format checks establish rendering only. Record evidence checking after
checking the evidence, and review after checking the findings and limitations;
do not derive either from successful HTML generation. A passed evidence/review
check requires references such as `evidence:evidence-1`, `finding:finding-1`, or
`figure:figure-1`. A passed review requires current passed rendering and evidence
checks. Later upstream checks can mark an older downstream signoff `stale`.
Attribution records who made an attestation, not proof of a second human reviewer.

## Hand back what the operator can open

After a build completes, the operator needs IDs and URLs, not a summary. Show:

```text
<control-plane>/api/v1/artifacts/<A>/versions/<V>/preview   # the report itself
<control-plane>/api/v1/library                              # the shared library listing
```

Use the origin the API answered on (host configuration, or the `--control-plane` you passed). Two hosts on one
network both answer `/api/...`: the registry, and an unrelated single-page app that returns `200` plus a small HTML
shell for any unknown path. Size the difference out before trusting a link — a real preview is kilobytes to
megabytes, a foreign shell is a couple, and a missing version is a short `400`/`404` body.

Read the current version from `herdr-eng artifacts show <A> --json` (`current_version_id`); `report versions A`
rows carry no status or title, so they order history but do not name the head. Submit each follow-on `build` with
`--base-version` equal to that current head; a stale base returns HTTP 412 `version_base_mismatch` and means
rereading and reconciling, never forcing.

Registration is not discoverability. `herdr-eng artifacts for project <id>` (and the matching dashboard view) is
empty until `herdr-eng artifacts link <A> --project <id> --link-kind origin` records the relationship, and the
library feed reflects fleet sharing policy, not a per-artifact list — this server has no member/ACL route, so
`/api/v1/library/members` answers not-found.

For `check`, `--evidence-ref` accepts only references that exist in that version's descriptor: `evidence:evidence-1`,
`finding:finding-1`, `figure:figure-1`. A bare `evidence-1`, an asset reference, or an `artifact://` URI is rejected
with HTTP 400. A passed `evidence_checked` or `reviewed` needs at least one reference, and a passed `reviewed`
requires current passed `rendered` and `evidence_checked` — so record `rendered` first, then `evidence_checked`.

The private dashboard fetches a preview when requested, without downloading
supporting data. The preview is capped at 256 KiB, includes coverage notices, and
links to separate assets rather than executing arbitrary source or rich report
HTML. Use explicit downloads to inspect full evidence/figures. A saved preview's
asset links require the authenticated registry origin; it is not an offline
bundle. Public sharing remains a separate approval workflow.
