from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .model import Report


DEFAULT_CONTEXT_LIMIT = 1_048_576


def validate_request(
    payload: Any,
    *,
    source: str = "<input>",
    thinking: str = "auto",
    context_limit: int = DEFAULT_CONTEXT_LIMIT,
) -> Report:
    """Validate a request envelope or a bare list of chat messages.

    This intentionally validates only information present in the input. It does
    not invent a missing ``reasoning_content`` value and it does not contact an
    API. ``thinking=auto`` follows the V4-compatible default used by the DSH
    community harness; callers can pass ``disabled`` for an explicitly
    non-thinking request.
    """

    report = Report(kind="request", source=source)
    request: Mapping[str, Any]
    if isinstance(payload, list):
        request = {}
        messages = payload
        has_envelope = False
    elif isinstance(payload, Mapping):
        request = payload
        messages = payload.get("messages")
        has_envelope = True
    else:
        report.add(
            "INPUT_NOT_OBJECT",
            "error",
            "input must be a JSON object with messages or a JSON array of messages",
            hint="Use an OpenAI-compatible request envelope or pass the messages array directly.",
        )
        return report

    if not isinstance(messages, list):
        report.add(
            "INPUT_MESSAGES_MISSING",
            "error",
            "messages must be a JSON array",
            path="messages",
        )
        return report

    model = request.get("model")
    tools = request.get("tools")
    tool_call_count = 0
    tool_result_count = 0
    effective_thinking = _thinking_mode(request, thinking)

    report.facts.update(
        {
            "message_count": len(messages),
            "model": model,
            "thinking_mode": effective_thinking,
        }
    )

    _validate_request_options(
        request,
        report,
        has_envelope=has_envelope,
        messages=messages,
        thinking=thinking,
        context_limit=context_limit,
    )
    _validate_tools(tools, report)

    pending: dict[str, str] = {}
    seen_call_ids: set[str] = set()

    for index, message in enumerate(messages):
        path = f"messages[{index}]"
        if not isinstance(message, Mapping):
            report.add(
                "MESSAGE_NOT_OBJECT",
                "error",
                "each message must be a JSON object",
                path=path,
            )
            continue

        role = message.get("role")
        if not isinstance(role, str) or not role:
            report.add(
                "MESSAGE_ROLE_MISSING",
                "error",
                "message role must be a non-empty string",
                path=f"{path}.role",
            )
            continue

        if pending and role not in {"tool", "assistant"}:
            report.add(
                "TOOL_RESULTS_INCOMPLETE",
                "error",
                "a new user/system message appears before all pending tool results were returned",
                path=path,
                hint="Return one tool message for every tool_call before starting another turn.",
            )

        if role == "assistant":
            tool_calls = message.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                report.add(
                    "TOOL_CALLS_NOT_ARRAY",
                    "error",
                    "assistant.tool_calls must be an array",
                    path=f"{path}.tool_calls",
                )
                continue

            if pending:
                report.add(
                    "TOOL_RESULTS_INCOMPLETE",
                    "error",
                    "assistant message begins while earlier tool calls are still pending",
                    path=path,
                )

            if tool_calls:
                tool_call_count += len(tool_calls)
                next_role = _next_role(messages, index)
                if next_role == "tool" and effective_thinking != "disabled":
                    reasoning = message.get("reasoning_content")
                    if not isinstance(reasoning, str) or not reasoning.strip():
                        report.add(
                            "REASONING_CONTENT_MISSING",
                            "error",
                            "assistant tool-call turn is missing the original reasoning_content",
                            path=f"{path}.reasoning_content",
                            hint=(
                                "Preserve the exact field returned by DeepSeek across the tool loop; "
                                "do not synthesize a replacement. If thinking is intentionally off, "
                                "declare thinking=disabled."
                            ),
                        )

                for call_index, tool_call in enumerate(tool_calls):
                    call_path = f"{path}.tool_calls[{call_index}]"
                    call_id = _validate_tool_call(tool_call, report, call_path)
                    if call_id is None:
                        continue
                    if call_id in seen_call_ids:
                        report.add(
                            "TOOL_CALL_ID_DUPLICATE",
                            "error",
                            f"tool call id {call_id!r} is reused",
                            path=f"{call_path}.id",
                        )
                    seen_call_ids.add(call_id)
                    pending[call_id] = call_path

        elif role == "tool":
            tool_result_count += 1
            result_id = message.get("tool_call_id")
            result_path = f"{path}.tool_call_id"
            if not isinstance(result_id, str) or not result_id.strip():
                report.add(
                    "TOOL_RESULT_ID_MISSING",
                    "error",
                    "tool message must contain a non-empty tool_call_id",
                    path=result_path,
                )
            elif result_id not in pending:
                report.add(
                    "TOOL_RESULT_ORPHAN",
                    "error",
                    f"tool_call_id {result_id!r} does not match a pending assistant tool call",
                    path=result_path,
                    hint="Keep the assistant tool_calls and tool results in the same history.",
                )
            else:
                del pending[result_id]

    if pending:
        report.add(
            "TOOL_RESULTS_PENDING",
            "warning",
            f"{len(pending)} assistant tool call(s) have no tool result yet",
            hint="This is valid for a captured mid-flight request, but not for a completed tool loop.",
        )

    report.facts.update(
        {
            "tool_call_count": tool_call_count,
            "tool_result_count": tool_result_count,
            "pending_tool_call_count": len(pending),
        }
    )
    return report


def _validate_request_options(
    request: Mapping[str, Any],
    report: Report,
    *,
    has_envelope: bool,
    messages: list[Any],
    thinking: str,
    context_limit: int,
) -> None:
    if not has_envelope:
        report.add(
            "MAX_TOKENS_UNKNOWN",
            "info",
            "bare messages input has no max_tokens field to check",
            hint="Pass the full request envelope when auditing request limits.",
        )
    elif "max_tokens" not in request:
        report.add(
            "MAX_TOKENS_MISSING",
            "warning",
            "request does not set max_tokens explicitly",
            path="max_tokens",
            hint="Set a finite max_tokens value so the context budget is predictable.",
        )
    else:
        max_tokens = request.get("max_tokens")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
            report.add(
                "MAX_TOKENS_INVALID",
                "error",
                "max_tokens must be a positive integer",
                path="max_tokens",
            )
        elif max_tokens > context_limit:
            report.add(
                "MAX_TOKENS_OVER_CONTEXT",
                "error",
                f"max_tokens ({max_tokens}) exceeds the configured context limit ({context_limit})",
                path="max_tokens",
                hint="Reduce max_tokens; the message history also consumes context.",
            )

    model = request.get("model")
    if isinstance(model, str) and model.startswith("deepseek-v4"):
        explicit_thinking = _explicit_thinking(request)
        if explicit_thinking is None:
            report.add(
                "THINKING_NOT_EXPLICIT",
                "warning",
                "DeepSeek V4 request does not explicitly declare thinking mode",
                hint="Declare thinking disabled or enabled so client behavior is reproducible.",
            )
        elif explicit_thinking not in {"enabled", "disabled"}:
            report.add(
                "THINKING_VALUE_INVALID",
                "error",
                "thinking.type must be 'enabled' or 'disabled'",
                path="extra_body.thinking.type",
            )

    base_url = request.get("base_url") or request.get("endpoint")
    has_tools = bool(request.get("tools")) or any(
        isinstance(message, Mapping) and message.get("tool_calls") for message in messages
    )
    if isinstance(base_url, str) and "/beta" in base_url and has_tools:
        report.add(
            "BETA_TOOL_ROUTE",
            "warning",
            "tool calls are being sent through a /beta route",
            path="base_url",
            hint="Use the normal DeepSeek endpoint for tool loops unless a beta feature is required.",
        )


def _validate_tools(tools: Any, report: Report) -> None:
    if tools is None:
        return
    if not isinstance(tools, list):
        report.add("TOOLS_NOT_ARRAY", "error", "tools must be an array", path="tools")
        return

    for index, tool in enumerate(tools):
        path = f"tools[{index}]"
        if not isinstance(tool, Mapping):
            report.add("TOOL_NOT_OBJECT", "error", "each tool must be an object", path=path)
            continue
        function = tool.get("function")
        if tool.get("type") != "function" or not isinstance(function, Mapping):
            report.add(
                "TOOL_FUNCTION_SHAPE",
                "error",
                "tool must use the OpenAI function tool shape",
                path=path,
            )
            continue
        if not isinstance(function.get("name"), str) or not function["name"].strip():
            report.add(
                "TOOL_NAME_MISSING",
                "error",
                "function tool needs a non-empty name",
                path=f"{path}.function.name",
            )
        parameters = function.get("parameters")
        if not isinstance(parameters, Mapping):
            report.add(
                "TOOL_PARAMETERS_MISSING",
                "error",
                "function tool needs a parameters JSON schema",
                path=f"{path}.function.parameters",
            )
        if function.get("strict") is True and isinstance(parameters, Mapping):
            _validate_strict_schema(parameters, report, f"{path}.function.parameters")


def _validate_strict_schema(schema: Mapping[str, Any], report: Report, path: str) -> None:
    schema_type = schema.get("type")
    if schema_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, Mapping):
            report.add(
                "STRICT_PROPERTIES_INVALID",
                "error",
                "strict object schema properties must be an object",
                path=f"{path}.properties",
            )
            properties = {}
        required = schema.get("required", [])
        if not isinstance(required, list):
            required = []
            report.add(
                "STRICT_REQUIRED_INVALID",
                "error",
                "strict object schema required must be an array",
                path=f"{path}.required",
            )
        missing = sorted(set(properties) - set(required))
        if missing:
            report.add(
                "STRICT_REQUIRED_MISSING",
                "error",
                f"strict object schema does not require all properties: {', '.join(missing)}",
                path=f"{path}.required",
                hint="DeepSeek strict mode requires every object property to be listed in required.",
            )
        if schema.get("additionalProperties") is not False:
            report.add(
                "STRICT_ADDITIONAL_PROPERTIES",
                "error",
                "strict object schema must set additionalProperties to false",
                path=f"{path}.additionalProperties",
            )
        for name, child in properties.items():
            if isinstance(child, Mapping):
                _validate_strict_schema(child, report, f"{path}.properties.{name}")

    for key in ("items",):
        child = schema.get(key)
        if isinstance(child, Mapping):
            _validate_strict_schema(child, report, f"{path}.{key}")
    for key in ("anyOf", "oneOf", "allOf"):
        children = schema.get(key)
        if isinstance(children, list):
            for index, child in enumerate(children):
                if isinstance(child, Mapping):
                    _validate_strict_schema(child, report, f"{path}.{key}[{index}]")


def _validate_tool_call(tool_call: Any, report: Report, path: str) -> str | None:
    if not isinstance(tool_call, Mapping):
        report.add("TOOL_CALL_NOT_OBJECT", "error", "tool call must be an object", path=path)
        return None

    call_id = tool_call.get("id")
    if not isinstance(call_id, str) or not call_id.strip():
        report.add("TOOL_CALL_ID_MISSING", "error", "tool call needs a non-empty id", path=f"{path}.id")
        call_id = None

    function = tool_call.get("function")
    if not isinstance(function, Mapping):
        report.add(
            "TOOL_CALL_FUNCTION_MISSING",
            "error",
            "tool call needs a function object",
            path=f"{path}.function",
        )
        return call_id

    name = function.get("name")
    if not isinstance(name, str) or not name.strip():
        report.add(
            "TOOL_CALL_NAME_MISSING",
            "error",
            "tool call function.name must be non-empty",
            path=f"{path}.function.name",
        )

    arguments = function.get("arguments")
    if isinstance(arguments, str):
        try:
            decoded = json.loads(arguments)
        except json.JSONDecodeError:
            report.add(
                "TOOL_ARGUMENTS_INVALID",
                "error",
                "tool call function.arguments is not valid JSON",
                path=f"{path}.function.arguments",
                hint="Wait for all streaming argument deltas before parsing the tool call.",
            )
        else:
            if not isinstance(decoded, dict):
                report.add(
                    "TOOL_ARGUMENTS_NOT_OBJECT",
                    "error",
                    "tool call arguments should decode to a JSON object",
                    path=f"{path}.function.arguments",
                )
    elif isinstance(arguments, Mapping):
        report.add(
            "TOOL_ARGUMENTS_OBJECT_SHAPE",
            "warning",
            "tool call arguments are an object instead of the OpenAI-compatible JSON string shape",
            path=f"{path}.function.arguments",
            hint="Serialize arguments with json.dumps before sending or replaying the message.",
        )
    else:
        report.add(
            "TOOL_ARGUMENTS_MISSING",
            "error",
            "tool call function.arguments must be a JSON string",
            path=f"{path}.function.arguments",
        )
    return call_id


def _next_role(messages: Sequence[Any], index: int) -> str | None:
    if index + 1 >= len(messages):
        return None
    next_message = messages[index + 1]
    return next_message.get("role") if isinstance(next_message, Mapping) else None


def _explicit_thinking(request: Mapping[str, Any]) -> str | None:
    thinking = request.get("thinking")
    if isinstance(thinking, Mapping):
        value = thinking.get("type")
        return value if isinstance(value, str) else None
    extra_body = request.get("extra_body")
    if isinstance(extra_body, Mapping):
        thinking = extra_body.get("thinking")
        if isinstance(thinking, Mapping):
            value = thinking.get("type")
            return value if isinstance(value, str) else None
    return None


def _thinking_mode(request: Mapping[str, Any], requested: str) -> str:
    explicit = _explicit_thinking(request)
    if explicit:
        return explicit
    return requested
