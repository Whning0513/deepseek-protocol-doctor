import json
import unittest
from pathlib import Path

from dsv4doctor.stream import inspect_stream


ROOT = Path(__file__).parents[1]


class StreamTests(unittest.TestCase):
    def test_interleaved_tool_deltas_are_aggregated_by_index(self):
        lines = (ROOT / "fixtures" / "stream_interleaved.jsonl").read_text(encoding="utf-8").splitlines()
        report = inspect_stream(lines, source="stream_interleaved.jsonl")
        self.assertTrue(report.ok, report.to_dict())
        self.assertTrue(report.facts["interleaved_tool_indices"])
        self.assertEqual([call["index"] for call in report.facts["tool_calls"]], [0, 1])
        self.assertEqual(report.facts["tool_calls"][0]["function"]["arguments"], '{"q":"x"}')
        self.assertEqual(report.facts["tool_calls"][1]["function"]["arguments"], '{"q":"y"}')
        self.assertEqual(report.facts["empty_choices"], 1)

    def test_bad_json_line_is_error(self):
        report = inspect_stream(["data: not-json"], source="bad.jsonl")
        self.assertFalse(report.ok)
        self.assertIn("SSE_JSON_INVALID", {finding.code for finding in report.errors})

    def test_jsonl_payloads_without_data_prefix_work(self):
        payload = {"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}
        report = inspect_stream([json.dumps(payload), "[DONE]"], source="inline")
        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.facts["content"], "ok")
        self.assertTrue(report.facts["done_seen"])


if __name__ == "__main__":
    unittest.main()
