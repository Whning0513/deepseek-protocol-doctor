from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .model import Report


def _iter_payload_lines(lines: Iterable[str]) -> Iterable[tuple[int, str]]:
    """Yield logical SSE/JSONL payloads with their first source line.

    OpenAI captures usually put one JSON object on each ``data:`` line, but
    SSE also permits one event's data to be split across several lines.  A
    malformed first fragment is buffered until it becomes valid JSON or the
    event ends at a blank line.
    """
    buffered: list[str] = []
    start_line: int | None = None

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.rstrip("\r\n").strip()
        if not stripped:
            if buffered:
                yield start_line or line_number, "\n".join(buffered)
                buffered = []
                start_line = None
            continue
        if stripped.startswith(":") or stripped.startswith(("event:", "id:", "retry:")):
            continue

        if stripped.startswith("data:"):
            data = stripped[5:]
            if data.startswith(" "):
                data = data[1:]
            if data.strip() == "[DONE]":
                if buffered:
                    yield start_line or line_number, "\n".join(buffered)
                    buffered = []
                    start_line = None
                yield line_number, "[DONE]"
                continue
            if buffered:
                buffered.append(data)
                candidate = "\n".join(buffered)
                try:
                    json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                yield start_line or line_number, candidate
                buffered = []
                start_line = None
                continue
            try:
                json.loads(data)
            except json.JSONDecodeError:
                buffered = [data]
                start_line = line_number
            else:
                yield line_number, data
            continue

        if buffered:
            yield start_line or line_number, "\n".join(buffered)
            buffered = []
            start_line = None
        yield line_number, stripped

    if buffered:
        yield start_line or 1, "\n".join(buffered)


def inspect_stream(lines: Iterable[str], *, source: str = "<stream>") -> Report:
    """Inspect an OpenAI-compatible SSE capture without making a network call."""

    report = Report(kind="stream", source=source)
    content_parts: list[str] = []
    reasoning_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    observed_indices: list[int] = []
    finish_reasons: list[str] = []
    data_chunks = 0
    empty_choices = 0
    done_seen = False

    for line_number, line in _iter_payload_lines(lines):
        if not line:
            continue
        if line == "[DONE]":
            done_seen = True
            continue

        data_chunks += 1
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            report.add(
                "SSE_JSON_INVALID",
                "error",
                "stream data line is not valid JSON",
                path=f"line {line_number}",
            )
            continue
        if not isinstance(payload, Mapping):
            report.add(
                "SSE_PAYLOAD_INVALID",
                "error",
                "stream data payload must be an object",
                path=f"line {line_number}",
            )
            continue

        choices = payload.get("choices")
        if choices == []:
            empty_choices += 1
            continue
        if not isinstance(choices, list):
            report.add(
                "SSE_CHOICES_INVALID",
                "error",
                "stream payload choices must be an array",
                path=f"line {line_number}.choices",
            )
            continue

        for choice_index, choice in enumerate(choices):
            if not isinstance(choice, Mapping):
                report.add(
                    "SSE_CHOICE_INVALID",
                    "error",
                    "each stream choice must be an object",
                    path=f"line {line_number}.choices[{choice_index}]",
                )
                continue
            finish_reason = choice.get("finish_reason")
            if isinstance(finish_reason, str):
                finish_reasons.append(finish_reason)
            delta = choice.get("delta") or {}
            if not isinstance(delta, Mapping):
                report.add(
                    "SSE_DELTA_INVALID",
                    "error",
                    "stream choice delta must be an object",
                    path=f"line {line_number}.choices[{choice_index}].delta",
                )
                continue

            content = delta.get("content")
            if isinstance(content, str):
                content_parts.append(content)
            reasoning = delta.get("reasoning_content")
            if isinstance(reasoning, str):
                reasoning_parts.append(reasoning)

            deltas = delta.get("tool_calls") or []
            if not isinstance(deltas, list):
                report.add(
                    "SSE_TOOL_DELTAS_INVALID",
                    "error",
                    "delta.tool_calls must be an array",
                    path=f"line {line_number}.choices[{choice_index}].delta.tool_calls",
                )
                continue
            for delta_index, tool_delta in enumerate(deltas):
                if not isinstance(tool_delta, Mapping):
                    report.add(
                        "SSE_TOOL_DELTA_INVALID",
                        "error",
                        "each streamed tool-call delta must be an object",
                        path=f"line {line_number}.tool_calls[{delta_index}]",
                    )
                    continue
                index = tool_delta.get("index", 0)
                if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                    report.add(
                        "SSE_TOOL_INDEX_INVALID",
                        "error",
                        "streamed tool-call index must be a non-negative integer",
                        path=f"line {line_number}.tool_calls[{delta_index}].index",
                    )
                    continue
                observed_indices.append(index)
                aggregate = tool_calls.setdefault(
                    index,
                    {
                        "index": index,
                        "id": None,
                        "type": None,
                        "function": {"name": None, "arguments": ""},
                        "arguments_null_seen": False,
                    },
                )
                _merge_tool_delta(aggregate, tool_delta)

    if data_chunks == 0:
        report.add("SSE_EMPTY", "error", "stream contains no JSON data chunks")

    if empty_choices:
        report.add(
            "SSE_EMPTY_CHOICES",
            "info",
            f"observed {empty_choices} chunk(s) with choices=[]; these are tolerated",
            hint="Do not assume every SSE chunk contains a choice.",
        )

    interleaved = _is_interleaved(observed_indices)
    if interleaved:
        report.add(
            "SSE_TOOL_INDICES_INTERLEAVED",
            "info",
            "tool-call deltas interleave across indices; index-keyed aggregation succeeded",
            hint="Aggregate by tool-call index rather than appending by arrival order.",
        )

    normalized_calls: list[dict[str, Any]] = []
    for index in sorted(tool_calls):
        aggregate = tool_calls[index]
        arguments = aggregate["function"]["arguments"]
        normalized = {
            "index": index,
            "id": aggregate.get("id"),
            "type": aggregate.get("type"),
            "function": {
                "name": aggregate["function"].get("name"),
                "arguments": arguments,
            },
        }
        normalized_calls.append(normalized)
        if aggregate.get("arguments_null_seen"):
            report.add(
                "SSE_TOOL_ARGUMENTS_NULL",
                "info",
                f"streamed tool call {index} contains a null arguments fragment",
                path=f"tool_calls[{index}].function.arguments",
                hint="Preserve later string deltas and normalize null before client-side argument splitting.",
            )
        if arguments:
            try:
                decoded = json.loads(arguments)
            except json.JSONDecodeError:
                if "length" in finish_reasons:
                    severity = "warning"
                    hint = "The model stopped at the token limit; do not execute an incomplete tool call."
                else:
                    severity = "error"
                    hint = "Wait for all argument deltas before parsing the tool call."
                report.add(
                    "SSE_TOOL_ARGUMENTS_INVALID",
                    severity,
                    f"aggregated tool call {index} arguments are not valid JSON",
                    path=f"tool_calls[{index}].function.arguments",
                    hint=hint,
                )
            else:
                if not isinstance(decoded, dict):
                    report.add(
                        "SSE_TOOL_ARGUMENTS_NOT_OBJECT",
                        "error",
                        f"aggregated tool call {index} arguments are not a JSON object",
                        path=f"tool_calls[{index}].function.arguments",
                    )

    report.facts.update(
        {
            "data_chunks": data_chunks,
            "empty_choices": empty_choices,
            "done_seen": done_seen,
            "finish_reasons": finish_reasons,
            "content": "".join(content_parts),
            "reasoning_content": "".join(reasoning_parts),
            "tool_calls": normalized_calls,
            "observed_tool_indices": observed_indices,
            "interleaved_tool_indices": interleaved,
        }
    )
    return report


def _merge_tool_delta(aggregate: dict[str, Any], delta: Mapping[str, Any]) -> None:
    for key in ("id", "type"):
        value = delta.get(key)
        if isinstance(value, str) and value and not aggregate.get(key):
            aggregate[key] = value
    function = delta.get("function")
    if not isinstance(function, Mapping):
        return
    name = function.get("name")
    if isinstance(name, str) and name and not aggregate["function"].get("name"):
        aggregate["function"]["name"] = name
    arguments = function.get("arguments")
    if arguments is None and "arguments" in function:
        aggregate["arguments_null_seen"] = True
    elif isinstance(arguments, str):
        aggregate["function"]["arguments"] += arguments


def _is_interleaved(indices: list[int]) -> bool:
    if not indices:
        return False
    highest = indices[0]
    for index in indices[1:]:
        if index < highest:
            return True
        highest = max(highest, index)
    return False
