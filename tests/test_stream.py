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

    def test_null_tool_arguments_fragment_does_not_crash(self):
        """Keep the Open WebUI #27195 partial-fragment boundary observable."""
        payload = {
            "choices": [
                {
                    "delta": {
                        "tool_calls": [
                            {
                                "index": 0,
                                "function": {
                                    "name": "search_web",
                                    "arguments": None,
                                },
                            }
                        ]
                    }
                }
            ]
        }
        report = inspect_stream(
            [json.dumps(payload)], source="open-webui-27195-snippet"
        )
        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.facts["observed_tool_indices"], [0])
        self.assertEqual(report.facts["tool_calls"][0]["function"]["arguments"], "")
        self.assertEqual(
            [finding.code for finding in report.findings],
            ["SSE_TOOL_ARGUMENTS_NULL"],
        )
        self.assertEqual(report.findings[0].severity, "info")

    def test_vllm_ascend_null_delta_metadata_is_tolerated(self):
        """Keep the public vLLM-Ascend #12062 stream shape covered.

        The values are shortened and redacted from the public report; this is
        a parser guardrail, not a provider fixture. The report's local stream
        uses an initial tool-call identity delta, null identity fields on
        later argument deltas, and a final choices=[] usage chunk.
        """
        lines = [
            'data: {"choices":[{"index":0,"delta":{"content":null,"tool_calls":[{"id":"call_public_0","type":"function","index":0,"function":{"name":"lookup","arguments":""}}]},"finish_reason":null}]}',
            'data: {"choices":[{"index":0,"delta":{"content":null,"tool_calls":[{"id":null,"type":null,"index":0,"function":{"name":null,"arguments":"{\\"query\\":\\"redacted\\""}}]},"finish_reason":null}]}',
            'data: {"choices":[{"index":0,"delta":{"content":null,"tool_calls":[{"id":null,"type":null,"index":0,"function":{"name":null,"arguments":",\\"top_k\\":5}"}}]},"finish_reason":null}]}',
            'data: {"choices":[{"index":0,"delta":{"content":null},"finish_reason":"tool_calls"}]}',
            'data: {"choices":[],"usage":{"prompt_tokens":1,"total_tokens":2}}',
        ]

        report = inspect_stream(lines, source="vllm-ascend-12062-shape")

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.facts["finish_reasons"], ["tool_calls"])
        self.assertEqual(report.facts["tool_calls"][0]["id"], "call_public_0")
        self.assertEqual(report.facts["tool_calls"][0]["function"]["name"], "lookup")
        self.assertEqual(
            report.facts["tool_calls"][0]["function"]["arguments"],
            '{"query":"redacted","top_k":5}',
        )
        self.assertEqual(report.facts["empty_choices"], 1)
        self.assertEqual(
            [finding.code for finding in report.findings],
            ["SSE_EMPTY_CHOICES"],
        )


if __name__ == "__main__":
    unittest.main()
