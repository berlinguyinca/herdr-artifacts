"""The skill must hand back openable IDs and links, unprompted, whenever it registers an artifact."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "herdr-artifact"
SKILL_MD = (SKILL / "SKILL.md").read_text()
REPORT_COMMANDS = (SKILL / "references" / "report-commands.md").read_text()


class SkillHandoffTests(unittest.TestCase):
    def test_skill_declares_a_completion_handoff_section(self):
        self.assertRegex(SKILL_MD, r"(?m)^## Completion handoff")

    def test_handoff_names_the_ids_the_operator_has_to_type(self):
        for needle in ("artifact ID", "version ID", "current_version_id", "job ID"):
            with self.subTest(needle=needle):
                self.assertIn(needle, SKILL_MD)

    def test_handoff_gives_the_version_pinned_urls(self):
        self.assertIn("/api/v1/artifacts/<artifact_id>/versions/<version_id>/preview", SKILL_MD)
        self.assertIn("/api/v1/library", SKILL_MD)

    def test_handoff_requires_links_offered_on_the_operators_device(self):
        self.assertIn("open-client.py", SKILL_MD)
        self.assertIn("--url", SKILL_MD)

    def test_handoff_warns_that_registry_presence_is_not_discoverability(self):
        self.assertIn("artifacts link", SKILL_MD)
        self.assertIn("artifacts for project", SKILL_MD)

    def test_handoff_requires_proving_the_link_before_calling_it_verified(self):
        self.assertIn("single-page", SKILL_MD)
        self.assertIn("SHA-256", SKILL_MD)

    def test_generation_and_edit_workflows_point_at_the_handoff(self):
        self.assertRegex(SKILL_MD, r"current status, then run the completion handoff")
        self.assertRegex(SKILL_MD, r"(?m)^7\. .*completion handoff")


class ReportCommandReferenceTests(unittest.TestCase):
    def test_reference_documents_handoff_routes(self):
        self.assertIn("/api/v1/artifacts/<A>/versions/<V>/preview", REPORT_COMMANDS)
        self.assertIn("/api/v1/library", REPORT_COMMANDS)

    def test_reference_documents_the_check_reference_syntax(self):
        self.assertIn("`evidence:evidence-1`", REPORT_COMMANDS)
        self.assertIn("HTTP 400", REPORT_COMMANDS)

    def test_reference_documents_current_head_lookup(self):
        self.assertIn("current_version_id", REPORT_COMMANDS)
        self.assertIn("version_base_mismatch", REPORT_COMMANDS)


if __name__ == "__main__":
    unittest.main()
