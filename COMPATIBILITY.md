# Compatibility Notes

This file records public integration reports that are useful for triage but do not yet contain a protocol capture.

Issue and PR metadata were checked on 2026-08-18 UTC.

## DeepSeek V4 agent-loop premature termination

- DeepSeek [DeepSeek-V3 #1554](https://github.com/deepseek-ai/DeepSeek-V3/issues/1554) was opened on 2026-08-09 and remained open when checked on 2026-08-16. The report describes `deepseek-v4-flash` returning a short natural-language status message with `finish_reason: stop` and no tool call inside an agent loop. It says the behavior was observed in streaming and non-streaming Chat Completions, with and without `reasoning_effort`, and at several `max_tokens` settings. The issue body does not include a complete request, response, HTTP metadata, or a reproducible raw capture.
- A 2026-08-09 follow-up by the reporter ([comment 5230508113](https://github.com/deepseek-ai/DeepSeek-V3/issues/1554#issuecomment-5230508113)) says the requests pass through CLIProxyAPI to `api.deepseek.com` and that the observation came from upstream request logs. It still does not publish the payload, response body, model response ID, or an ordered SSE stream. This is a client/agent report with stated upstream provenance, not a provider fixture.
- A 2026-08-13 comment ([5276120665](https://github.com/deepseek-ai/DeepSeek-V3/issues/1554#issuecomment-5276120665)) proposes a host-side completion gate: reject a short status utterance after `finish_reason: stop` when no tool call or concrete result is present, then apply a bounded retry budget. This is a third-party design proposal; this repository has not received code, a capture, or a measured false-positive rate for it. The checker therefore does not add a finding based on the proposal.
- A 2026-08-16 comment ([5306438650](https://github.com/deepseek-ai/DeepSeek-V3/issues/1554#issuecomment-5306438650)) describes a separate agent-layer observation involving structurally valid but semantically empty tool calls and post-execution read-back. That comment is also an implementation report without a request/response capture. It should not be used to infer a provider rule.
- The 24 fetched comments were authored by `HappinessEV`, `Lady-Lin`, `icophy`, `qingkong66`, and `yun520-1`; no comment identifies a DeepSeek organization account. The issue remained open at the checked time. No maintainer-confirmed behavior or official workaround was found.

Current assessment: #1554 supports documenting a possible host-level completion-gate compatibility track, not changing request validation or adding a stream fixture. A useful follow-up would include the smallest sanitized request, the complete raw Chat Completions response for both streaming and non-streaming modes, HTTP status/headers, model/API version information, and enough repeated cases to measure whether a gate wrongly retries valid final answers. Keep any retry policy in the host/orchestrator layer; the offline protocol checker cannot infer task completeness from a short assistant message alone.

## DeepSeek Chat Completions finish reasons

- The official [Chat Completions API reference](https://api-docs.deepseek.com/api/create-chat-completion/) checked on 2026-08-18 lists `max_tokens` as the request's generation limit. It does not list `max_completion_tokens` on that reference page. This supports keeping the current `MAX_TOKENS_MISSING` observation for a DeepSeek request that supplies only the latter; the FlowDown capture uses a Fireworks endpoint and is a separate provider contract.
- The same reference enumerates `stop`, `length`, `content_filter`, `tool_calls`, and `insufficient_system_resource` as response `finish_reason` values. It describes the last value as an interruption caused by insufficient inference-system resources. This is schema evidence, not a provider capture.
- The stream checker now preserves the documented `insufficient_system_resource` value without a finding and emits the warning `SSE_FINISH_REASON_UNKNOWN` for a string outside that set. Unknown values remain non-fatal because an OpenAI-compatible serving layer may extend the response contract; callers can use `--fail-on-warning` when undocumented values should block a check.

## Cline with Ollama and local DeepSeek models

Public reports:

- [Cline #1653](https://github.com/cline/cline/issues/1653) was opened on 2025-02-05 and closed on 2025-06-21. It describes local DeepSeek models served by Ollama getting stuck in a tool-execution loop. The discussion focuses on the Ollama `num_ctx` setting and does not include a request, SSE/JSONL capture, HTTP status, or model response.
- [Cline #4362](https://github.com/cline/cline/issues/4362) was opened on 2025-06-21, closed on 2025-07-26, and last updated on 2025-08-04. It consolidates reports about Ollama compatibility and iterative tool use. The issue was closed as experimental support; its discussion does not provide a protocol capture that identifies a tool-call ID, message-history, `reasoning_content`, or stream-fragment failure.

Current assessment: these reports are behavior evidence, not fixtures. The doctor cannot determine from them whether the boundary is context exhaustion, model capability, client history reconstruction, endpoint behavior, or streamed tool-call handling. Do not add a finding code or fixture based on these reports alone.

A useful follow-up capture should include the client and backend versions, model and endpoint shape, thinking configuration, the smallest complete request or SSE/JSONL stream, and the observed HTTP error. Remove credentials, user content, private URLs, local paths, account IDs, and business data before sharing it.

## DeepSeek V4 streaming parser work in SGLang

- SGLang [PR #34600](https://github.com/sgl-project/sglang/pull/34600) was opened on 2026-08-12 and was still open on 2026-08-15. Its body and patch describe four streaming parser boundaries in the DeepSeek V4 DSML detector: retaining a buffer after a parse exception, avoiding `rstrip` character-set truncation, flushing trapped text at stream end, and holding back split DSML tags across chunks.
- The PR body reports 11 new regression tests and 38 passing unit tests. Those results are author-reported here; this repository did not execute SGLang's suite. The PR body also shows failed latest base and extra CI markers at the time of inspection, so the implementation should be treated as review evidence rather than a merged behavior contract.
- The detector consumes DeepSeek DSML tags such as `<｜DSML｜tool_calls>`, while this project checks OpenAI-compatible SSE and JSONL payloads. The implementation supports testing practices for chunk boundaries and end-of-stream flushing, but it does not establish `function.arguments: null`, an OpenAI wire shape, or a provider response rule. No fixture or finding is added from this PR.

## Open WebUI with DeepInfra

- [Open WebUI #27195](https://github.com/open-webui/open-webui/issues/27195) was opened on 2026-07-19 and updated on 2026-07-27. The report identifies Open WebUI v0.10.2, an OpenAI-compatible DeepInfra connection, and DeepSeek V4 models. It includes a representative stream fragment with `function.arguments: null`, the resulting `NoneType has no len()` stack trace, and the affected `_split_tool_calls` path. It does not include a complete ordered SSE/JSONL capture, tool-call ID sequence, or raw HTTP response.
- The linked [fix PR #27194](https://github.com/open-webui/open-webui/pull/27194) describes two client-side protections: normalize null arguments before splitting and normalize them during stream-delta merging. This is evidence of an integration boundary observed by that client, not proof that every DeepSeek-compatible endpoint emits null arguments.
- The fragment is not added to `fixtures/`: it is too small to establish stream ordering or a complete tool loop. A future fixture needs the full sanitized response sequence and enough request context to distinguish a provider payload from client-side reconstruction.

## SGLang mixed content and tool-call response excerpt

- SGLang [#34214](https://github.com/sgl-project/sglang/issues/34214) was opened on 2026-08-10. The report supplies a request shape with `stream=true`, `stream_options.include_usage=true`, `reasoning_effort="max"`, and a weather tool, plus an eight-line response excerpt in which content deltas precede a tool-call delta and `finish_reason: "tool_calls"`.
- The report calls the response an excerpt and describes content that was missing after the displayed prefix. The public body does not establish the full ordered response, does not include `[DONE]`, and its request prompt is user content. A sanitized in-memory parse accepts the shown shape but cannot infer the missing content or assign the loss to a provider rather than the SGLang serving layer.
- The excerpt is not added to `fixtures/` and no new finding is inferred from it. A raw response export plus the request and server version would be needed to test this boundary without inventing expected content.

## vLLM-Ascend DeepSeek V4 stream candidate

- vLLM-Ascend [#12062](https://github.com/vllm-project/vllm-ascend/issues/12062) was opened on 2026-07-15 and updated on 2026-07-16. The report compares a DeepSeek SaaS stream with a local `vllm-ascend` stream and publishes the local engine command, model alias `dsv4`, `deepseek_v4` tokenizer/tool/reasoning parsers, eight local `data:` chunks, a `tool_calls` finish reason, and a final `choices=[]` usage chunk.
- In the local sequence, the first delta supplies the tool-call ID, type, name, and empty arguments. Later deltas set ID, type, and name to `null` while appending argument fragments. The source body displays Markdown `**` markers inside three JSON lines, has no `[DONE]` line or request body, and places SaaS and local outputs in one issue body.
- Removing those `**` markers in memory and checking the eight local lines produced one aggregated tool call, `finish_reason: "tool_calls"`, the argument object `{"query":"天花板开裂了","top_k":5}`, and only the tolerated `SSE_EMPTY_CHOICES` information. This confirms the parser can inspect the published shape, not that the normalized text is an exact wire capture.
- The normalized lines are not added to `fixtures/`. `tests/test_stream.py` contains a redacted guardrail using the same null-metadata and argument-delta shape. A fixture needs the unrendered response, the request/tool definitions, and a clear boundary between the SaaS and local streams.

## Maintenance practice from vLLM

- vLLM [PR #50296](https://github.com/vllm-project/vllm/pull/50296) was opened on 2026-07-29 and updated on 2026-08-03. It adds per-parser tool-call format conformance tests using fixed raw bytes and mock tokenizers, so the tests run offline without a GPU, model download, or live server. The PR reports 34 passing tests and calibrates the suite by planting one defect at a time.
- This repository can use the same boundary when a real capture is available: pin the smallest observed wire fragment and keep provider execution outside the test. The PR does not provide a DeepSeek V4 capture for this repository, so it does not justify a new fixture or finding code here.

vLLM [PR #52255](https://github.com/vllm-project/vllm/pull/52255) was opened on 2026-08-14 and remained open on 2026-08-15. The patch attaches request-level tools to an existing system or developer message, restores the checkpoint's [reference golden](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/main/encoding/test_output_1.txt), and adds four renderer tests. The PR body reports four restored goldens and the new tests passing; that result was not independently rerun here.

This is prompt-rendering parity evidence, not a provider response capture. It supports keeping backend golden tests tied to an upstream reference and recording the exact layer under test. It does not justify changing request-history validation or adding a stream fixture to this repository.

vLLM [PR #50861](https://github.com/vllm-project/vllm/pull/50861) was opened on 2026-08-03 and updated on 2026-08-14. The checked PR head is `61b0b93a9658d5dea4015fcf0b41c4da7286d322`. Its public body contains a complete minimal curl request for `deepseek-v4-flash` where `messages[1].tool_calls[0].function.arguments` is the JSON string `"[]"`. The PR reports that vLLM's frontend previously passed the decoded list downstream and returned HTTP 500; its patch coerces non-dict values and returns HTTP 400 for malformed JSON.

The request is a frontend input reproducer, not a provider response. After replacing only the two user-controlled content values with redaction markers, it is stored as [`fixtures/vllm_50861_non_object_arguments.json`](fixtures/vllm_50861_non_object_arguments.json) and covered by `TOOL_ARGUMENTS_NOT_OBJECT`. The fixture preserves the source's model, roles, call ID, function name, and argument shape.

## DeepSeek V4 tokenizer and renderer reports

- vLLM [#51829](https://github.com/vllm-project/vllm/issues/51829) was opened on 2026-08-11 and reports that the Python DeepSeek V4 renderer places request-level tools in a synthetic system message even when an existing system message is present. The report compares Python, Rust, and the checkpoint reference encoder and includes a tokenizer-only reproduction without a GPU. This is a prompt-rendering parity issue, not a request-history or SSE finding in this project.
- vLLM [#52253](https://github.com/vllm-project/vllm/issues/52253) was opened on 2026-08-14 and [#52254](https://github.com/vllm-project/vllm/pull/52254) was opened the same day. They document a tools-present history where an assistant turn without `reasoning` was rendered as an empty `<think></think>` block, compare it with the checkpoint's expected encoding, and add encoder tests for missing and empty reasoning. The report provides an encoder-level reproduction, not a provider response capture; it does not justify changing `REASONING_CONTENT_MISSING` or adding a fixture here.
- SGLang [#33185](https://github.com/sgl-project/sglang/issues/33185) was opened on 2026-08-01 and updated on 2026-08-06. It compares the three `low`, `high`, and `max` reasoning-effort prompts in the DeepSeek-V4-Flash-0731 reference encoder with SGLang's mapping and includes a static source check plus a live reproduction script. The issue concerns backend template selection and does not establish a request or stream shape that this checker can validate.

These reports support a separate backend/template compatibility track. Until a complete sanitized request, rendered prompt or ordered response capture is available, keep them as evidence notes rather than protocol fixtures.
