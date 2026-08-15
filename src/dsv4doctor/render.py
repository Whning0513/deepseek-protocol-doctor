from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Finding, Report


def render_text(report: Report) -> str:
    status = "PASS" if report.ok else "FAIL"
    lines = [
        f"{status} {report.kind} · {report.source}",
        f"errors={len(report.errors)} warnings={len(report.warnings)} findings={len(report.findings)}",
    ]
    if report.facts:
        lines.append("facts:")
        for key, value in report.facts.items():
            if key == "tool_calls" and isinstance(value, list):
                lines.append(f"  {key}: {len(value)} aggregated")
            elif isinstance(value, (dict, list)):
                lines.append(f"  {key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}")
            else:
                lines.append(f"  {key}: {value}")
    if report.findings:
        lines.append("findings:")
        for finding in report.findings:
            location = f" [{finding.path}]" if finding.path else ""
            lines.append(f"  {finding.severity.upper():7} {finding.code}{location}: {finding.message}")
            if finding.hint:
                lines.append(f"           hint: {finding.hint}")
    return "\n".join(lines)


def render_json(report: Report) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_sarif(report: Report) -> str:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding in report.findings:
        rules.setdefault(
            finding.code,
            {
                "id": finding.code,
                "shortDescription": {"text": finding.message},
                "help": {"text": finding.hint or finding.message},
            },
        )
        result: dict[str, Any] = {
            "ruleId": finding.code,
            "level": {"error": "error", "warning": "warning", "info": "note"}[finding.severity],
            "message": {"text": _sarif_message(finding)},
        }
        if report.source not in {"<input>", "<stream>", "-"}:
            result["locations"] = [
                {"physicalLocation": {"artifactLocation": {"uri": Path(report.source).as_posix()}}}
            ]
        results.append(result)
    payload = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "deepseek-protocol-doctor", "version": "0.1.2", "rules": list(rules.values())}},
                "results": results,
            }
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _sarif_message(finding: Finding) -> str:
    if finding.path:
        return f"{finding.path}: {finding.message}"
    return finding.message
