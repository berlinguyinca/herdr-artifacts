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

## Publication policy

Public publication is separate from internal artifact creation. The artifact
version is immutable and pinned. Public requests require human approval,
expiry, audience policy, provider status, and revocation. No skill command may
activate public access implicitly.
