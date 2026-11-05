"""MCP mode against a real local JSON-RPC HTTP server (stdlib http.server in a thread, no mocks)."""
import base64
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "herdr-artifact"
WRAPPER = SKILL / "scripts" / "herdr-artifact"
MCP = SKILL / "scripts" / "herdr-artifact-mcp"
CHUNK = 524_288
CREDENTIAL = "cred-SECRET-0123456789"
SECRET_URL = "https://artifacts.example.org/s/TOKEN-ABCDEF/"
VECTOR = {  # packages/member-upload-vector.json in herdr-engineering (server derivation)
    "member": "member:alice", "artifact_id": "art_0123456789ab", "name": "report v2.html",
    "size_bytes": 1572881, "file_sha256": "c0fd9724584489658557089c4f69e0718cd168d9a3e7450e911a73a75a3d547b",
    "upload_id": "upl_b7a95189d8674125ad4f3663"}


def vector_bytes(size):
    return bytes(((i * 31 + (i >> 8)) & 255) for i in range(size))


def derive_upload_id(member, artifact_id, name, sha, size):
    owner = "m_" + hashlib.sha256(member.encode()).hexdigest()[:24]
    pre = "|".join((owner, artifact_id, name, sha, str(size)))
    return "upl_" + hashlib.sha256(pre.encode()).hexdigest()[:24]


class Stub:
    def __init__(self):
        self.calls, self.headers, self.chunks = [], [], {}
        self.fail_chunk = None          # index answered with HTTP 500
        self.rate_limit = 0             # next N chunk posts answered with HTTP 429
        self.pending_results = 0
        self.member = VECTOR["member"]
        self.override = {}              # tool name -> document to answer instead
        self.max_ranges = None          # truncate missing_ranges like the server (truncated when len >= max)
        self.delay_first = {}           # tool name -> seconds to stall the first call
        self.redirect_to = None
        stub = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                stub.headers.append(dict(self.headers))
                p = body["params"]
                name, args = p["name"], p["arguments"]
                stub.calls.append((name, args))
                if stub.redirect_to:
                    return self.reply(302, b"", {"Location": stub.redirect_to})
                if stub.delay_first.get(name):
                    time.sleep(stub.delay_first.pop(name))
                if name == "artifact_upload_chunk":
                    if stub.rate_limit > 0:
                        stub.rate_limit -= 1
                        return self.reply(429, b"{}", {"Retry-After": "0"})
                    if stub.fail_chunk == args["index"]:
                        return self.reply(500, b"{}")
                out = stub.override.get(name) or stub.tool(name, args)
                text = "UNTRUSTED CONTENT\n\n" + json.dumps(out)
                res = {"jsonrpc": "2.0", "id": body["id"],
                       "result": {"content": [{"type": "text", "text": text}], "isError": False}}
                self.reply(200, json.dumps(res).encode())

            def reply(self, code, data, extra=None):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (extra or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/mcp" % self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def names(self):
        return [n for n, _ in self.calls]

    def tool(self, name, a):
        if name == "artifact_create":
            return {"ticket": "ict_" + "0" * 24, "status": "done", "result": "created",
                    "artifact_id": "art_0123456789ab"}
        if name == "artifact_upload_status":
            uid = derive_upload_id(self.member, a["artifact_id"], a["name"], a["file_sha256"], a["size_bytes"])
            total = -(-a["size_bytes"] // CHUNK)
            have = {i for (u, i) in self.chunks if u == uid}
            miss, start = [], None
            for i in range(total + 1):
                absent = i < total and i not in have
                if absent and start is None:
                    start = i
                elif not absent and start is not None:
                    miss.append([start, i - 1])
                    start = None
            trunc = False
            if self.max_ranges is not None:
                miss = miss[:self.max_ranges]
                trunc = len(miss) >= self.max_ranges
            return {"upload_id": uid, "total": total, "missing_ranges": miss, "complete": not miss, "truncated": trunc}
        if name == "artifact_upload_chunk":
            uid = derive_upload_id(self.member, a["artifact_id"], a["name"], a["file_sha256"], a["size_bytes"])
            data = base64.b64decode(a["data_b64"], validate=True)
            assert hashlib.sha256(data).hexdigest() == a["sha256"]
            self.chunks[(uid, a["index"])] = data
            return {"ok": True}
        if name == "artifact_publish":
            return {"ticket": "ict_" + "1" * 24, "status": "pending"} if self.pending_results else \
                {"ticket": "ict_" + "1" * 24, "status": "done", "result": "created", "version_id": "ver_1"}
        if name == "artifact_result":
            if self.pending_results > 0:
                self.pending_results -= 1
                return {"ticket": a["ticket"], "status": "pending"}
            return {"ticket": a["ticket"], "status": "done", "result": "created", "version_id": "ver_1"}
        if name == "artifact_share_create":
            return {"ticket": "ict_" + "2" * 24, "status": "done", "result": "created", "share_id": "shr_1",
                    "audience": a["audience"], "summary": {"files": [{"name": "index.html", "size_bytes": 10}, {"name": "a.css", "size_bytes": 5}],
                                "audience": a["audience"], "expires_at": "2026-12-01T00:00:00+00:00", "warnings": []}}
        if name == "artifact_share_approve":
            return {"ticket": "ict_" + "3" * 24, "status": "done", "result": "live",
                    "secret": {"url": SECRET_URL, "notice": "shown once"}}
        if name == "artifact_share_list":
            return {"links": [{"share_id": "shr_1", "audience": "lab"}]}
        if name == "artifacts_mine":
            return {"artifacts": [{"artifact_id": "art_0123456789ab", "title": "t"}]}
        if name == "artifact_share_revoke":
            return {"status": "done", "result": "revoked"}
        if name == "artifact_delete":
            return {"status": "done", "result": "deleted"}
        if name == "artifact_result" and a["ticket"] == "ict_" + "9" * 24:
            return {"ticket": a["ticket"], "status": "done", "result": "created"}
        raise AssertionError(name)


class Env:
    def __init__(self, stub, mode=0o600, extra=""):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / ".config" / "herdr").mkdir(parents=True)
        self.work = Path(self.tmp.name) / "work"
        self.work.mkdir()
        self.cred = self.home / "cred"
        self.cred.write_text(CREDENTIAL + "\n")
        self.cred.chmod(mode)
        (self.home / ".config" / "herdr" / "artifact.yaml").write_text(
            "mcp:\n  url: %s\n  credential_file: %s\n  device: dev-1\n%s" % (stub.url, self.cred, extra))

    def run(self, *args, script=MCP, path_prepend=None):
        env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        if script == WRAPPER or path_prepend:  # a hermetic PATH: the host's own herdr-eng must not leak in
            env["PATH"] = (path_prepend + os.pathsep if path_prepend else "") + "/usr/bin:/bin"
        return subprocess.run([str(script), *args], text=True, capture_output=True, cwd=self.work, env=env, timeout=60)

    def logs(self):
        found = []
        for p in Path(self.tmp.name).rglob("*"):
            if p.is_file():
                found.append((p, p.read_bytes()))
        return found


class McpModeTests(unittest.TestCase):
    def setUp(self):
        self.stub = Stub()
        self.addCleanup(self.stub.close)
        self.env = Env(self.stub)
        self.addCleanup(self.env.tmp.cleanup)

    def write(self, name, size):
        p = self.env.work / name
        p.write_bytes(vector_bytes(size))
        return p

    def test_three_chunks_with_correct_hashes_and_derived_upload_id(self):
        size = int(1.3 * 1024 * 1024)
        data = vector_bytes(size)
        (self.env.work / "big.bin").write_bytes(data)
        r = self.env.run("publish", "big.bin", "--artifact", "art_0123456789ab", "-m", "v1")
        self.assertEqual(r.returncode, 0, r.stderr)
        sends = [a for n, a in self.stub.calls if n == "artifact_upload_chunk"]
        self.assertEqual([a["index"] for a in sends], [0, 1, 2])
        sha = hashlib.sha256(data).hexdigest()
        for a in sends:
            self.assertEqual(a["total"], 3)
            self.assertEqual(a["file_sha256"], sha)
            piece = data[a["index"] * CHUNK:(a["index"] + 1) * CHUNK]
            self.assertEqual(a["sha256"], hashlib.sha256(piece).hexdigest())
        uid = derive_upload_id(VECTOR["member"], "art_0123456789ab", "big.bin", sha, size)
        pub = [a for n, a in self.stub.calls if n == "artifact_publish"][0]
        self.assertEqual(pub["files"], [{"name": "big.bin", "upload_id": uid}])
        self.assertEqual(pub["message"], "v1")
        self.assertIn("ver_1", r.stdout)

    def test_shared_vector_hash_and_upload_id(self):
        self.write("report v2.html", VECTOR["size_bytes"])
        r = self.env.run("publish", "report v2.html", "--artifact", VECTOR["artifact_id"], "-m", "x")
        self.assertEqual(r.returncode, 0, r.stderr)
        sends = [a for n, a in self.stub.calls if n == "artifact_upload_chunk"]
        self.assertEqual(len(sends), 4)
        self.assertEqual(sends[0]["file_sha256"], VECTOR["file_sha256"])
        pub = [a for n, a in self.stub.calls if n == "artifact_publish"][0]
        self.assertEqual(pub["files"][0]["upload_id"], VECTOR["upload_id"])

    def test_credentials_headers(self):
        self.env.run("list")
        h = self.stub.headers[0]
        self.assertEqual(h["Authorization"], "Agent " + CREDENTIAL)
        self.assertEqual(h["X-Herdr-Device"], "dev-1")

    def test_resume_after_failure_sends_only_missing_chunks(self):
        self.write("big.bin", 3 * CHUNK - 5)
        self.stub.fail_chunk = 1
        r = self.env.run("publish", "big.bin", "--artifact", "art_0123456789ab", "-m", "v")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("artifact_publish", self.stub.names())
        self.assertNotIn(CREDENTIAL, r.stdout + r.stderr)
        self.stub.fail_chunk = None
        self.stub.calls.clear()
        r = self.env.run("publish", "big.bin", "--artifact", "art_0123456789ab", "-m", "v")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([a["index"] for n, a in self.stub.calls if n == "artifact_upload_chunk"], [1, 2])
        self.assertIn("artifact_publish", self.stub.names())

    def test_backoff_on_429(self):
        self.write("small.txt", 100)
        self.stub.rate_limit = 2
        r = self.env.run("publish", "small.txt", "--artifact", "art_0123456789ab", "-m", "v")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.names().count("artifact_upload_chunk"), 3)

    def test_publish_polls_pending_ticket(self):
        self.write("small.txt", 100)
        self.stub.pending_results = 2
        r = self.env.run("publish", "small.txt", "--artifact", "art_0123456789ab", "-m", "v")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.names().count("artifact_result"), 3)
        self.assertIn("ver_1", r.stdout)

    def test_publish_without_artifact_creates_one(self):
        self.write("page.html", 50)
        r = self.env.run("publish", "page.html", "-m", "first")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.names()[0], "artifact_create")

    def test_publish_sends_base_and_entry(self):
        self.write("page.html", 50)
        self.env.run("publish", "page.html", "--artifact", "art_0123456789ab", "--base", "ver_0",
                     "--entry", "page.html", "-m", "m")
        pub = [a for n, a in self.stub.calls if n == "artifact_publish"][0]
        self.assertEqual((pub["base_version_id"], pub["entry"]), ("ver_0", "page.html"))

    def test_share_public_sends_public_and_stops_before_approve(self):
        r = self.env.run("share", "art_0123456789ab", "ver_1", "--audience", "public", "--days", "7")
        self.assertEqual(r.returncode, 0, r.stderr)
        name, args = self.stub.calls[-1]
        self.assertEqual(name, "artifact_share_create")
        self.assertEqual(args["audience"], "public")
        self.assertEqual(args["expires_in_days"], 7)
        self.assertNotIn("artifact_share_approve", self.stub.names())
        for needle in ("index.html", "a.css", "public", "7"):
            self.assertIn(needle, r.stdout)
        self.assertNotIn(SECRET_URL, r.stdout + r.stderr)

    def test_share_lab_group_and_emails(self):
        self.env.run("share", "a1", "v1", "--group", "lab", "--email", "b@x.org", "--email", "c@x.org")
        _, args = self.stub.calls[-1]
        self.assertEqual((args["audience"], args["allow_groups"], args["allow_emails"]),
                         ("lab", ["lab"], ["b@x.org", "c@x.org"]))

    def test_share_requires_an_audience(self):
        r = self.env.run("share", "a1", "v1")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.stub.calls, [])

    def test_approve_url_once_on_stdout_and_in_no_file(self):
        r = self.env.run("share", "approve", "art_0123456789ab", "shr_1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.count(SECRET_URL), 1)
        self.assertNotIn("TOKEN-ABCDEF", r.stderr)
        self.assertEqual(self.stub.calls[-1][1]["confirm"], True)
        for p, data in self.env.logs():
            self.assertNotIn(b"TOKEN-ABCDEF", data, p)
            if p != self.env.cred:
                self.assertNotIn(CREDENTIAL.encode(), data, p)

    def test_credential_not_0600_refused(self):
        for mode in (0o644, 0o640, 0o604):
            self.env.cred.chmod(mode)
            r = self.env.run("list")
            self.assertEqual(r.returncode, 2, mode)
            self.assertIn("0600", r.stderr)
            self.assertNotIn(CREDENTIAL, r.stdout + r.stderr)
        self.assertEqual(self.stub.calls, [])

    def test_delete_requires_yes(self):
        r = self.env.run("delete", "art_0123456789ab")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.stub.calls, [])
        r = self.env.run("delete", "art_0123456789ab", "--yes")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.calls[-1], ("artifact_delete", {"artifact_id": "art_0123456789ab", "confirm": True}))

    def test_simple_commands_map_to_tools(self):
        cases = [(("list",), "artifacts_mine"), (("links",), "artifact_share_list"),
                 (("links", "a1"), "artifact_share_list"), (("revoke", "a1", "s1"), "artifact_share_revoke"),
                 (("create", "--title", "T", "--filename", "i.html", "--profile", "web"), "artifact_create")]
        for args, tool in cases:
            self.stub.calls.clear()
            r = self.env.run(*args)
            self.assertEqual(r.returncode, 0, (args, r.stderr))
            self.assertEqual(self.stub.names(), [tool])

    def test_oversize_file_prints_web_ui_address(self):
        self.env = Env(self.stub, extra="  max_bytes: 1000\n  public_host: artifacts.example.org\n")
        self.addCleanup(self.env.tmp.cleanup)
        self.write("huge.bin", 5000)
        r = self.env.run("publish", "huge.bin", "--artifact", "art_0123456789ab", "-m", "m")
        self.assertEqual(r.returncode, 3)
        self.assertIn("https://artifacts.example.org/", r.stdout + r.stderr)
        self.assertEqual(self.stub.calls, [])

    def test_missing_config_is_a_clean_error(self):
        (self.env.home / ".config" / "herdr" / "artifact.yaml").unlink()
        r = self.env.run("list")
        self.assertEqual(r.returncode, 2)
        self.assertIn("artifact.yaml", r.stderr)


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.stub = Stub()
        self.addCleanup(self.stub.close)
        self.env = Env(self.stub)
        self.addCleanup(self.env.tmp.cleanup)

    def reconfigure(self, url=None, extra=""):
        (self.env.home / ".config" / "herdr" / "artifact.yaml").write_text(
            "mcp:\n  url: %s\n  credential_file: %s\n  device: dev-1\n%s" % (url or self.stub.url, self.env.cred, extra))

    def test_rejected_result_is_a_failure_for_every_command(self):
        (self.env.work / "p.txt").write_bytes(b"hello")
        rej = {"ticket": "ict_" + "4" * 24, "status": "done", "result": "rejected", "reason": "nope"}
        cases = [("artifact_create", ("create", "--title", "T", "--filename", "i.html", "--profile", "web")),
                 ("artifact_publish", ("publish", "p.txt", "--artifact", "a1", "-m", "m")),
                 ("artifact_share_create", ("share", "a1", "v1", "--audience", "public")),
                 ("artifact_share_approve", ("share", "approve", "a1", "s1")),
                 ("artifact_share_revoke", ("revoke", "a1", "s1")),
                 ("artifact_delete", ("delete", "a1", "--yes"))]
        for tool, args in cases:
            self.stub.override = {tool: rej}
            r = self.env.run(*args)
            self.assertEqual(r.returncode, 1, (tool, r.stdout, r.stderr))
            self.assertIn("nope", r.stderr)
            self.assertNotIn("STOP", r.stdout)

    def test_unexpected_result_value_is_a_failure(self):
        self.stub.override = {"artifact_delete": {"status": "done", "result": "weird"}}
        self.assertEqual(self.env.run("delete", "a1", "--yes").returncode, 1)

    def test_share_without_share_id_does_not_print_stop_block(self):
        self.stub.override = {"artifact_share_create": {"status": "done", "result": "created", "summary": {}}}
        r = self.env.run("share", "a1", "v1", "--audience", "public")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("STOP", r.stdout)

    def test_already_approved_has_no_link_and_fails(self):
        self.stub.override = {"artifact_share_approve": {"status": "done", "result": "already_approved", "share_id": "s1"}}
        r = self.env.run("share", "approve", "a1", "s1")
        self.assertEqual(r.returncode, 1)
        self.assertNotIn("http", r.stdout)

    def test_malicious_urls_refused_before_any_request(self):
        for url in ("http://127.0.0.1.evil.example/mcp", "http://localhost@evil.example/mcp",
                    "http://localhost.evil.example/mcp", "ftp://127.0.0.1/mcp", "http://evil.example/mcp",
                    "https://user:pw@evil.example/mcp", "https:///mcp"):
            self.reconfigure(url=url)
            r = self.env.run("list")
            self.assertEqual(r.returncode, 2, url)
            self.assertNotIn(CREDENTIAL, r.stdout + r.stderr)

    def test_loopback_http_forms_are_allowed(self):
        for host in ("http://127.0.0.1:1/mcp", "http://localhost:1/mcp", "http://[::1]:1/mcp"):
            self.reconfigure(url=host)
            r = self.env.run("list")
            self.assertNotEqual(r.returncode, 2, host)   # accepted by validation; the connection itself fails (1)

    def test_redirect_is_refused_and_authorization_does_not_follow(self):
        other = Stub()
        self.addCleanup(other.close)
        self.stub.redirect_to = other.url
        r = self.env.run("list")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(other.calls, [])
        self.assertIn("redirect", r.stderr.lower())

    def test_retry_after_timeout_reuses_the_idempotency_key(self):
        self.reconfigure(extra="  timeout_seconds: 1\n")
        self.stub.delay_first = {"artifact_create": 2.5}
        r = self.env.run("create", "--title", "T", "--filename", "i.html", "--profile", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        keys = [a["idempotency_key"] for n, a in self.stub.calls if n == "artifact_create"]
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0], keys[1])
        self.assertRegex(keys[0], r"^[\x21-\x7e]{8,128}$")

    def test_each_logical_write_gets_a_key_and_a_fresh_one_per_run(self):
        (self.env.work / "p.txt").write_bytes(b"hello")
        self.env.run("publish", "p.txt", "--artifact", "a1", "-m", "m")
        self.env.run("publish", "p.txt", "--artifact", "a1", "-m", "m")
        keys = [a["idempotency_key"] for n, a in self.stub.calls if n == "artifact_publish"]
        self.assertEqual(len(set(keys)), 2)
        self.stub.calls.clear()
        self.env.run("share", "a1", "v1", "--audience", "public")
        self.env.run("share", "approve", "a1", "s1")
        for n, a in self.stub.calls:
            self.assertIn("idempotency_key", a, n)

    def test_approve_is_not_retried_after_an_ambiguous_timeout(self):
        self.reconfigure(extra="  timeout_seconds: 1\n")
        self.stub.delay_first = {"artifact_share_approve": 2.5}
        r = self.env.run("share", "approve", "a1", "s1")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.stub.names().count("artifact_share_approve"), 1)
        self.assertIn("links", r.stderr)
        self.assertIn("may have", r.stderr)

    def test_truncated_missing_ranges_resume_in_rounds(self):
        data = vector_bytes(6 * CHUNK)
        (self.env.work / "six.bin").write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()
        uid = derive_upload_id(VECTOR["member"], "a1", "six.bin", sha, len(data))
        for i in (1, 3):
            self.stub.chunks[(uid, i)] = b"x"
        self.stub.max_ranges = 1
        r = self.env.run("publish", "six.bin", "--artifact", "a1", "-m", "m")
        self.assertEqual(r.returncode, 0, r.stderr)
        sent = [a["index"] for n, a in self.stub.calls if n == "artifact_upload_chunk"]
        self.assertEqual(sent, [0, 2, 4, 5])
        self.assertGreaterEqual(self.stub.names().count("artifact_upload_status"), 4)

    def test_symlinked_credential_file_refused(self):
        real = self.env.home / "real.cred"
        real.write_text(CREDENTIAL)
        real.chmod(0o600)
        self.env.cred.unlink()
        self.env.cred.symlink_to(real)
        r = self.env.run("list")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.stub.calls, [])

    def test_bad_max_bytes_and_public_host_are_config_errors(self):
        for extra in ("  max_bytes: abc\n", "  max_bytes: 0\n", "  max_bytes: -5\n",
                      "  public_host: evil.example/x?y\n", "  timeout_seconds: 0\n"):
            self.reconfigure(extra=extra)
            r = self.env.run("list")
            self.assertEqual(r.returncode, 2, extra)

    def test_days_zero_is_refused_and_server_expiry_is_printed(self):
        r = self.env.run("share", "a1", "v1", "--audience", "public", "--days", "0")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.stub.calls, [])
        r = self.env.run("share", "a1", "v1", "--audience", "public")
        self.assertIn("2026-12-01T00:00:00+00:00", r.stdout)

    def test_result_subcommand_polls_a_ticket(self):
        r = self.env.run("result", "ict_" + "9" * 24)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.names(), ["artifact_result"])


class WrapperDispatchTests(unittest.TestCase):
    def setUp(self):
        self.stub = Stub()
        self.addCleanup(self.stub.close)
        self.env = Env(self.stub)
        self.addCleanup(self.env.tmp.cleanup)
        self.bin = Path(self.env.tmp.name) / "bin"
        self.bin.mkdir()

    def fake_eng(self, code=0):
        p = self.bin / "herdr-eng"
        p.write_text("#!/bin/sh\necho CLI-RAN \"$@\"\nexit %d\n" % code)
        p.chmod(0o755)

    def test_mcp_when_herdr_eng_absent(self):
        r = self.env.run("list", script=WRAPPER)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.stub.names(), ["artifacts_mine"])

    def test_cli_when_herdr_eng_works(self):
        self.fake_eng(0)
        r = self.env.run("create", "x.csv", script=WRAPPER, path_prepend=str(self.bin))
        self.assertIn("CLI-RAN artifacts upload x.csv", r.stdout)
        self.assertEqual(self.stub.calls, [])

    def test_mcp_when_herdr_eng_unconfigured(self):
        self.fake_eng(1)
        r = self.env.run("list", script=WRAPPER, path_prepend=str(self.bin))
        self.assertEqual(self.stub.names(), ["artifacts_mine"], r.stderr)

    def test_forced_modes(self):
        self.fake_eng(0)
        self.env.run("--mode", "mcp", "list", script=WRAPPER, path_prepend=str(self.bin))
        self.assertEqual(self.stub.names(), ["artifacts_mine"])
        self.fake_eng(1)
        r = self.env.run("--mode", "cli", "create", "x.csv", script=WRAPPER, path_prepend=str(self.bin))
        self.assertIn("CLI-RAN artifacts upload x.csv", r.stdout)

    def test_chosen_mode_is_printed_on_stderr(self):
        r = self.env.run("list", script=WRAPPER)
        self.assertIn("mode: mcp", r.stderr)
        r = self.env.run("--mode", "cli", "create", "x.csv", script=WRAPPER)
        self.assertIn("mode: cli", r.stderr)

    def test_missing_timeout_binary_does_not_break_selection(self):
        # a PATH holding only herdr-eng and the tools the wrapper needs, but no `timeout`
        tools = Path(self.env.tmp.name) / "tools"
        tools.mkdir()
        for t in ("sh", "grep", "dirname", "readlink", "python3", "cat"):
            (tools / t).symlink_to(subprocess.check_output(["which", t], text=True).strip())
        self.fake_eng(1)
        env = {"HOME": str(self.env.home), "PATH": str(self.bin) + os.pathsep + str(tools)}
        r = subprocess.run([str(WRAPPER), "list"], text=True, capture_output=True, env=env, cwd=self.env.work, timeout=60)
        self.assertEqual(self.stub.names(), ["artifacts_mine"], r.stderr)

    def test_bad_mode_is_usage_error(self):
        r = self.env.run("--mode", "bogus", "list", script=WRAPPER)
        self.assertEqual(r.returncode, 2)

    def test_no_mcp_block_means_cli(self):
        (self.env.home / ".config" / "herdr" / "artifact.yaml").write_text("other: 1\n")
        self.fake_eng(1)
        r = self.env.run("report", "validate", "x", script=WRAPPER, path_prepend=str(self.bin))
        self.assertIn("CLI-RAN artifacts reports validate x", r.stdout)

    def test_mcp_without_config_block_forced_is_error(self):
        (self.env.home / ".config" / "herdr" / "artifact.yaml").write_text("other: 1\n")
        r = self.env.run("--mode", "mcp", "list", script=WRAPPER)
        self.assertEqual(r.returncode, 2)

    def test_all_four_harnesses_run_the_same_script(self):
        root = Path(self.env.tmp.name) / "skills"
        r = subprocess.run([str(ROOT / "install" / "install.sh")], text=True, capture_output=True,
                           env={**os.environ, "HERDR_ARTIFACT_SKILL_ROOT": str(root)})
        self.assertEqual(r.returncode, 0, r.stderr)
        scripts = set()
        for harness in ("codex", "claude", "pi", "opencode"):
            link = root / harness / "skills" / "herdr-artifact"
            wrapper = link / "scripts" / "herdr-artifact"
            self.assertTrue(wrapper.is_file(), harness)
            scripts.add(os.path.realpath(wrapper))
            out = self.env.run("--mode", "mcp", "list", script=wrapper)
            self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(scripts, {os.path.realpath(WRAPPER)})
        self.assertEqual(self.stub.names(), ["artifacts_mine"] * 4)


if __name__ == "__main__":
    unittest.main()
