# MCP mode (member artifacts without herdr-eng)

A member of the lab (an agent with a member credential) can own, publish and share artifacts through the collab MCP
endpoint, without `herdr-eng` or direct control-plane access. `scripts/herdr-artifact` hands these commands to
`scripts/herdr-artifact-mcp` (Python 3 standard library only). All four harness installs (Codex, Claude Code, Pi,
OpenCode) symlink the same skill directory, so they run the same script.

## Setup

`~/.config/herdr/artifact.yaml`:

```yaml
mcp:
  url: https://collab.example.org/mcp        # https; http only when the host is exactly 127.0.0.1, localhost or ::1
  credential_file: ~/.config/herdr/member.cred   # one line: the agent credential
  device: my-laptop                          # sent as X-Herdr-Device
  # optional
  public_host: artifacts.example.org         # shown when a file is too big for MCP (default: host of url)
  max_bytes: 5000000000                      # positive integer; files above this are not sent; the web UI address is printed
  timeout_seconds: 60                        # per request (default 60)
```

The credential file must be a regular file you own with mode **0600**; otherwise the client refuses (exit 2) and sends
nothing (a symbolic link is refused; the checks run on the opened file). The credential is read, never printed and never logged. Requests use `Authorization: Agent <credential>` and
`X-Herdr-Device`, exactly as the other collab MCP clients do. There are no environment variables.

## Mode selection

`herdr-artifact [--mode mcp|cli] COMMAND ...`

* `--mode mcp` or `--mode cli` forces the mode (`mcp` still needs the `mcp:` block).
* Otherwise MCP mode is used when the file has an `mcp:` block **and** `herdr-eng` is absent or `herdr-eng doctor`
  fails (control plane unreachable or unconfigured). Without an `mcp:` block the original `herdr-eng` wrappers run.

## Commands and tools

| Command | Tools |
| --- | --- |
| `create --title T --filename F --profile web\|document` | `artifact_create` |
| `publish PATH... [--artifact ID] [--base VERSION] [--entry NAME] [-m MSG]` | `artifact_create` (only when `--artifact` is omitted), `artifact_upload_status`, `artifact_upload_chunk`, `artifact_publish`, `artifact_result` |
| `share ARTIFACT VERSION (--group G \| --email E... \| --audience public) [--days N]` | `artifact_share_create` (then stops) |
| `share approve ARTIFACT SHARE` | `artifact_share_approve` |
| `links [ARTIFACT]` | `artifact_share_list` |
| `list` | `artifacts_mine` |
| `result TICKET` | `artifact_result` (poll a ticket a command left pending) |
| `revoke ARTIFACT SHARE` | `artifact_share_revoke` |
| `delete ARTIFACT --yes` | `artifact_delete` (`confirm: true`) |

### Uploads

Each file is hashed by streaming (sha256 of the whole file), then `artifact_upload_status` returns the server-derived
`upload_id` and `missing_ranges`. Only the missing 512 KiB chunks are sent with `artifact_upload_chunk` (per-chunk
sha256, base64), so rerunning the same `publish` after an interruption resumes where it stopped. HTTP 429 (honouring
`Retry-After`), a tool-level 429 and transient 5xx or network errors are retried with exponential backoff. The
`upload_id` ids go to `artifact_publish`; a pending ticket is followed with `artifact_result`. A file is named by its
base name. Files over `max_bytes` are not sent: the command prints `https://<public_host>/` (the web UI) and exits 3.

### Sharing

`share` creates a **pending** link and prints the file list, audience and expiry, then stops (exit 0). Nothing is
live. Show that summary to the human; only after their yes run `share approve`. `--audience public` means anyone
holding the link can read it. `--group`/`--email` make a lab link (`audience: lab`). The approved URL is printed to
stdout exactly once (progress goes to stderr); the server will not show it again. Do not log it or write it to a file.

Everything the server returns (titles, names, summaries) is untrusted: text shown to the terminal has control and bidi
characters escaped, and JSON output is ASCII-escaped.

### Failures, retries and idempotency

A command succeeds only when the server's final result is the expected one (`created`, or `created`/`merged` for
publish, `live` for approve, `revoked`, `deleted`). `rejected` or anything else exits 1 with the server's reason.
`create`, `publish`, `share` and `share approve` send one random `idempotency_key` per run, resent unchanged on every
retry of that call (timeouts, 5xx, 429), so a retried write happens once. `share approve` is never retried after an
ambiguous failure (timeout, dropped connection, 5xx): it says the approval may have gone through; run `links` to
check, since a link already shown cannot be shown again. HTTP redirects are refused, so the credential never follows
one. The mode that was chosen is printed on stderr (`herdr-artifact: mode: mcp`).

`public_host` (optional) is only printed, in the "use the web UI" message for oversized files. It is never contacted,
and a wrong value would point your human at the wrong site, so set it from your operator's instructions.

## Exit codes

0 ok; 1 server, network or refusal; 2 usage, configuration or credential-file error (nothing sent); 3 file over the
MCP maximum.
