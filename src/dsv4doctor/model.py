from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class Finding:
    """One stable, machine-readable diagnostic."""

    code: str
    severity: Severity
    message: str
    path: str | None = None
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.path:
            value["path"] = self.path
        if self.hint:
            value["hint"] = self.hint
        return value


@dataclass
class Report:
    """The common result shape shared by the JSON, text, and SARIF renderers."""

    kind: str
    source: str
    findings: list[Finding] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def add(
        self,
        code: str,
        severity: Severity,
        message: str,
        *,
        path: str | None = None,
        hint: str | None = None,
    ) -> None:
        self.findings.append(Finding(code, severity, message, path, hint))

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": "deepseek-protocol-doctor",
            "version": "0.1.2",
            "kind": self.kind,
            "source": self.source,
            "ok": self.ok,
            "summary": {
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "infos": sum(f.severity == "info" for f in self.findings),
            },
            "facts": self.facts,
            "findings": [finding.to_dict() for finding in self.findings],
        }
