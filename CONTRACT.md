# HerdR Artifact Client Contract

## Internal API

The skill targets the authenticated HerdR control plane:

- `POST /api/v1/artifacts` — compatibility raw upload.
- `GET /api/v1/artifacts` — ACL-filtered catalog with `q`, `type`, `status`,
  `created_by`, `offset`, and `limit` filters.
- `GET /api/v1/artifacts/{id}` — metadata/detail.
- `GET /api/v1/artifacts/{id}/versions` — immutable history.
- `POST /api/v1/artifacts/{id}/versions` — CAS version commit using
  `base_version_id` and an idempotency key.
- `POST /api/v1/artifact-jobs` — scheduled rendering/build request.
- `POST /api/v1/artifact-reviews` and
  `POST /api/v1/artifact-reviews/{id}/complete` — review lifecycle.
- `POST /api/v1/publications/requests` — pending publication request.
- `POST /api/v1/publications/{id}/approve|revoke` — named human actions.

Version commits must preserve source manifests, output manifests, validation,
toolchain, agent, host, session, mission, and job provenance. Stale CAS heads
return `409`; unauthorized resources do not disclose existence.

## Harness context

Agents should resolve current `session_id`, `mission_id`, `host_id`, and
principal from their harness/runtime context. Missing context is represented as
unknown or omitted; IDs are never guessed from titles, directories, or
hostname aliases.

## Report packages

Report authoring is domain-neutral: the reader output, editable source, evidence,
interpretation, provenance, and validation must remain traceable through supported
source/output manifests and pinned references. Domain algorithms and policies are
provided by analysis adapters, not hardcoded into the shared skill.

Explanation-only revisions retain the original analysis evidence and provenance
and record their own rendering/interpretation sources. A successful format check
is not a claim that the analysis or proposed actions are independently validated.

Verify capabilities against the installed client/API: the compatibility wrapper
does not implement the entire command contract, and advertising the `report`
profile does not imply rich HTML, multi-file import, large-blob handling, or a
working private preview. Prepared local packages and confirmed registered versions
are distinct statuses. The native descriptor extension below provides the concrete
wire format for supported report operations.

## Native report API extension

The `report` wrapper route delegates to `herdr-eng artifacts reports`. With a
compatible runtime, the descriptor wire format is the bundled
[v1 schema](skill/herdr-artifact/references/artifact-report-v1.schema.json), plus
runtime size, reference, manifest-binding and authorization checks. Commands and
examples are documented in the [native report reference](skill/herdr-artifact/references/report-commands.md).

- `POST /api/v1/artifact-reports` creates a private logical report.
- `POST /api/v1/artifacts/{id}/blobs` streams a scoped supporting asset.
- `POST /api/v1/artifact-reports/{id}/jobs` queues a descriptor-based worker build;
  `GET /api/v1/artifact-reports/{id}/jobs/{job}` reads persisted status.
- `GET /api/v1/artifacts/{id}/versions?summary=true` provides bounded metadata per
  version without embedding all descriptors or feedback.
- Under `/api/v1/artifacts/{id}/versions/{version}`, `GET /report`, `GET /diff?base_version_id=...`,
  `GET|POST /checks`, and `GET|POST /feedback` operate on an exact immutable version.
- `GET /preview` returns bounded inert HTML; `GET /assets/{asset_id}` explicitly
  downloads verified supporting bytes. Reading the preview does not fetch assets.

Checks and feedback are attributed append-only records. A rendered report is not
automatically evidence-checked or reviewed. Public access is never implied.

## Publication policy

Public publication is separate from internal artifact creation. The artifact
version is immutable and pinned. Public requests require human approval,
expiry, audience policy, provider status, and revocation. No skill command may
activate public access implicitly.
