import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from dsv4doctor.cli import main


ROOT = Path(__file__).parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_valid_request_returns_zero(self):
        code, output, error = self.run_cli(
            "check", str(ROOT / "fixtures" / "valid_tool_loop.json"), "--format", "json"
        )

        self.assertEqual(code, 0, error)
        self.assertTrue(json.loads(output)["ok"])
        self.assertEqual(error, "")

    def test_request_errors_return_one(self):
        code, output, error = self.run_cli(
            "check", str(ROOT / "fixtures" / "invalid_tool_loop.json"), "--format", "json"
        )

        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["ok"])
        self.assertEqual(error, "")

    def test_text_output_reports_status_and_finding(self):
        code, output, error = self.run_cli(
            "check", str(ROOT / "fixtures" / "invalid_tool_loop.json")
        )

        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertIn("FAIL request", output)
        self.assertIn("errors=3", output)
        self.assertIn("REASONING_CONTENT_MISSING", output)
        self.assertIn("hint:", output)

    def test_sarif_preserves_finding_code_level_and_location(self):
        source = str(ROOT / "fixtures" / "invalid_tool_loop.json")
        code, output, error = self.run_cli("check", source, "--format", "sarif")

        payload = json.loads(output)
        result = next(item for item in payload["runs"][0]["results"] if item["ruleId"] == "TOOL_RESULT_ORPHAN")
        self.assertEqual(code, 1)
        self.assertEqual(error, "")
        self.assertEqual(payload["version"], "2.1.0")
        self.assertEqual(result["level"], "error")
        self.assertIn("messages[2]", result["message"]["text"])
        self.assertEqual(
            result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
            Path(source).as_posix(),
        )

    def test_check_dash_reads_json_from_stdin(self):
        payload = (ROOT / "fixtures" / "valid_tool_loop.json").read_text(encoding="utf-8")
        with patch("sys.stdin", io.StringIO(payload)):
            code, output, error = self.run_cli("check", "-", "--format", "json")

        self.assertEqual(code, 0, error)
        self.assertTrue(json.loads(output)["ok"])
        self.assertEqual(json.loads(output)["source"], "-")
        self.assertEqual(error, "")

    def test_warning_only_stream_requires_fail_on_warning(self):
        stream = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {"index": 0, "function": {"arguments": '{"x":'}}
                        ]
                    },
                    "finish_reason": "length",
                }
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.jsonl"
            path.write_text(json.dumps(stream) + "\n", encoding="utf-8")

            code, output, error = self.run_cli("stream", str(path), "--format", "json")
            self.assertEqual(code, 0, error)
            report = json.loads(output)
            self.assertTrue(report["ok"])
            self.assertEqual(report["summary"]["warnings"], 1)

            code, output, error = self.run_cli(
                "stream", str(path), "--format", "json", "--fail-on-warning"
            )
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(output)["summary"]["warnings"], 1)
            self.assertEqual(error, "")

    def test_invalid_json_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")

            code, output, error = self.run_cli("check", str(path))

        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("invalid JSON", error)

    def test_missing_input_returns_two(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            code, output, error = self.run_cli("check", str(path))

        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("cannot read", error)


if __name__ == "__main__":
    unittest.main()
