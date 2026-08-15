import json
import unittest
from pathlib import Path

from dsv4doctor.stream import inspect_stream
from dsv4doctor.validator import validate_request


ROOT = Path(__file__).parents[1]
MANIFEST_PATH = ROOT / "fixtures" / "manifest.json"
ALLOWED_EVIDENCE = {
    "synthetic",
    "public_reproducer",
    "public_provider_capture",
}
FORMAT_BY_SUFFIX = {".json": "json", ".jsonl": "jsonl", ".sse": "sse"}


class FixtureRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_entries_are_offline_checkable(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        entries = self.manifest["entries"]
        self.assertGreaterEqual(len(entries), 6)
        paths = [entry["path"] for entry in entries]
        self.assertEqual(len(paths), len(set(paths)))

        for entry in entries:
            with self.subTest(path=entry["path"]):
                relative = Path(entry["path"])
                self.assertFalse(relative.is_absolute())
                self.assertEqual(relative.parts[0], "fixtures")
                path = ROOT / relative
                self.assertTrue(path.is_file())
                self.assertEqual(FORMAT_BY_SUFFIX[path.suffix], entry["format"])
                self.assertIn(entry["evidence"], ALLOWED_EVIDENCE)
                self._assert_provenance(entry)

                if entry["kind"] == "request":
                    report = validate_request(
                        json.loads(path.read_text(encoding="utf-8")),
                        source=entry["path"],
                    )
                else:
                    report = inspect_stream(
                        path.read_text(encoding="utf-8").splitlines(),
                        source=entry["path"],
                    )

                expected = entry["expected"]
                self.assertEqual(report.ok, expected["ok"])
                self.assertEqual(
                    sorted(f.code for f in report.errors),
                    sorted(expected["errors"]),
                )
                self.assertEqual(
                    sorted(f.code for f in report.warnings),
                    sorted(expected["warnings"]),
                )
                self.assertEqual(
                    sorted(f.code for f in report.findings if f.severity == "info"),
                    sorted(expected["infos"]),
                )
                for key, value in expected.get("facts", {}).items():
                    self.assertEqual(self._fact_value(report, key), value)

    def test_provider_capture_pairs_share_a_fixed_source(self):
        captures = {}
        for entry in self.manifest["entries"]:
            if entry["evidence"] != "public_provider_capture":
                continue
            capture_id = entry["capture_id"]
            source = entry["source"]
            captures.setdefault(capture_id, set()).add(
                (source["ref"], source["checked_on"])
            )
        self.assertEqual(
            captures,
            {
                "flowdown-fireworks-deepseek-v4-tool-call": {
                    ("c482f8432e411c09a71c803bc24295970c86d0ce", "2026-08-15")
                }
            },
        )

    def _assert_provenance(self, entry):
        evidence = entry["evidence"]
        if evidence == "synthetic":
            self.assertNotIn("source", entry)
            self.assertNotIn("redactions", entry)
            return

        source = entry.get("source")
        self.assertIsInstance(source, dict)
        self.assertTrue(source["url"].startswith("https://"))
        self.assertRegex(source["checked_on"], r"^2026-\d{2}-\d{2}$")
        self.assertTrue(entry.get("redactions"))
        if evidence == "public_provider_capture":
            self.assertTrue(entry.get("capture_id"))
            self.assertRegex(source["ref"], r"^[0-9a-f]{40}$")

    @staticmethod
    def _fact_value(report, key):
        if key == "tool_names":
            return [call["function"]["name"] for call in report.facts["tool_calls"]]
        return report.facts[key]


if __name__ == "__main__":
    unittest.main()
