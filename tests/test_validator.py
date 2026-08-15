import json
import unittest
from pathlib import Path

from dsv4doctor.validator import validate_request


ROOT = Path(__file__).parents[1]


def fixture(name: str):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


class ValidatorTests(unittest.TestCase):
    def test_valid_tool_loop_passes(self):
        report = validate_request(fixture("valid_tool_loop.json"), source="valid_tool_loop.json")
        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.facts["tool_call_count"], 1)
        self.assertEqual(report.facts["pending_tool_call_count"], 0)

    def test_invalid_tool_loop_exposes_actionable_codes(self):
        report = validate_request(fixture("invalid_tool_loop.json"), source="invalid_tool_loop.json")
        codes = {finding.code for finding in report.errors}
        self.assertFalse(report.ok)
        self.assertIn("REASONING_CONTENT_MISSING", codes)
        self.assertIn("TOOL_ARGUMENTS_INVALID", codes)
        self.assertIn("TOOL_RESULT_ORPHAN", codes)

    def test_vllm_50861_public_request_reports_non_object_arguments(self):
        """Keep the complete vLLM #50861 request reproducer covered.

        The user and tool-result values are redacted from the public curl
        example; the protocol boundary is the JSON-array argument string.
        """
        report = validate_request(
            fixture("vllm_50861_non_object_arguments.json"),
            source="vllm_50861_non_object_arguments.json",
        )
        codes = {finding.code for finding in report.errors}
        self.assertFalse(report.ok)
        self.assertIn("TOOL_ARGUMENTS_NOT_OBJECT", codes)
        self.assertNotIn("TOOL_ARGUMENTS_INVALID", codes)

    def test_explicit_thinking_disabled_allows_missing_reasoning(self):
        payload = fixture("invalid_tool_loop.json")
        payload["extra_body"] = {"thinking": {"type": "disabled"}}
        report = validate_request(payload)
        codes = {finding.code for finding in report.errors}
        self.assertNotIn("REASONING_CONTENT_MISSING", codes)

    def test_strict_schema_checks_deepseek_constraints(self):
        payload = fixture("valid_tool_loop.json")
        payload["tools"][0]["function"]["strict"] = True
        payload["tools"][0]["function"]["parameters"]["additionalProperties"] = True
        report = validate_request(payload)
        codes = {finding.code for finding in report.errors}
        self.assertIn("STRICT_ADDITIONAL_PROPERTIES", codes)

    def test_bare_messages_are_supported(self):
        payload = fixture("valid_tool_loop.json")["messages"]
        report = validate_request(payload)
        self.assertTrue(report.ok, report.to_dict())
        self.assertIn("MAX_TOKENS_UNKNOWN", {finding.code for finding in report.findings})


if __name__ == "__main__":
    unittest.main()
