"""Exercise the wrapper contract and the bundled, cross-domain examples."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "herdr-artifact"
WRAPPER = SKILL / "scripts" / "herdr-artifact"


class ReportWrapperTests(unittest.TestCase):
    def run_wrapper(self, *args, exit_code=0):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "herdr-eng"
            executable.write_text(
                "#!/usr/bin/env python3\nimport json, sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
                f"sys.exit({exit_code})\n"
            )
            executable.chmod(0o755)
            return subprocess.run(
                [str(WRAPPER), *args], text=True, capture_output=True,
                env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"]},
            )

    def test_report_preserves_argument_boundaries(self):
        args = ["build", "artifact-example", "--base-version", "none",
                "--descriptor", "path with spaces/report.json", "--api-key-env", "REPORT_KEY"]
        result = self.run_wrapper("report", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ["artifacts", "reports", *args])

    def test_report_preserves_native_failure(self):
        result = self.run_wrapper("report", "validate", "bad.json", exit_code=7)
        self.assertEqual(result.returncode, 7)

    def test_raw_upload_aliases_are_preserved(self):
        for alias in ("create", "upload"):
            with self.subTest(alias=alias):
                result = self.run_wrapper(alias, "path with spaces/data.csv")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout),
                                 ["artifacts", "upload", "path with spaces/data.csv"])


class ReportExampleTests(unittest.TestCase):
    def test_schema_and_examples_match_installed_runtime(self):
        import jsonschema

        schema = json.loads((SKILL / "references" / "artifact-report-v1.schema.json").read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        examples = SKILL / "assets" / "report-examples"
        for name in ("benchmark", "incident-audit"):
            with self.subTest(example=name):
                descriptor = json.loads((examples / (name + ".json")).read_text())
                jsonschema.validate(descriptor, schema)
                for asset in descriptor["assets"]:
                    data = (examples / asset["name"]).read_bytes()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), asset["sha256"])
                    self.assertEqual(len(data), asset["size_bytes"])
                result = subprocess.run(
                    [str(WRAPPER), "report", "validate", str(examples / (name + ".json"))],
                    text=True, capture_output=True,
                )
                if "invalid choice: 'reports'" in result.stderr:
                    self.skipTest("installed herdr-eng has no `artifacts reports` command")
                self.assertEqual(result.returncode, 0, result.stderr)
                status = json.loads(result.stdout)
                self.assertEqual(status["status"], "schema_valid")
                self.assertEqual(status["evidence_review"], "not_checked")


if __name__ == "__main__":
    unittest.main()
