# Compatibility Notes

This file records public integration reports that are useful for triage but do not yet contain a protocol capture.

Issue metadata and comments were checked on 2026-08-14 UTC.

## Cline with Ollama and local DeepSeek models

Public reports:

- [Cline #1653](https://github.com/cline/cline/issues/1653) was opened on 2025-02-05 and closed on 2025-06-21. It describes local DeepSeek models served by Ollama getting stuck in a tool-execution loop. The discussion focuses on the Ollama `num_ctx` setting and does not include a request, SSE/JSONL capture, HTTP status, or model response.
- [Cline #4362](https://github.com/cline/cline/issues/4362) was opened on 2025-06-21, closed on 2025-07-26, and last updated on 2025-08-04. It consolidates reports about Ollama compatibility and iterative tool use. The issue was closed as experimental support; its discussion does not provide a protocol capture that identifies a tool-call ID, message-history, `reasoning_content`, or stream-fragment failure.

Current assessment: these reports are behavior evidence, not fixtures. The doctor cannot determine from them whether the boundary is context exhaustion, model capability, client history reconstruction, endpoint behavior, or streamed tool-call handling. Do not add a finding code or fixture based on these reports alone.

A useful follow-up capture should include the client and backend versions, model and endpoint shape, thinking configuration, the smallest complete request or SSE/JSONL stream, and the observed HTTP error. Remove credentials, user content, private URLs, local paths, account IDs, and business data before sharing it.

## Open WebUI with DeepInfra

- [Open WebUI #27195](https://github.com/open-webui/open-webui/issues/27195) was opened on 2026-07-19 and updated on 2026-07-27. The report identifies Open WebUI v0.10.2, an OpenAI-compatible DeepInfra connection, and DeepSeek V4 models. It includes a representative stream fragment with `function.arguments: null`, the resulting `NoneType has no len()` stack trace, and the affected `_split_tool_calls` path. It does not include a complete ordered SSE/JSONL capture, tool-call ID sequence, or raw HTTP response.
- The linked [fix PR #27194](https://github.com/open-webui/open-webui/pull/27194) describes two client-side protections: normalize null arguments before splitting and normalize them during stream-delta merging. This is evidence of an integration boundary observed by that client, not proof that every DeepSeek-compatible endpoint emits null arguments.
- The fragment is not added to `fixtures/`: it is too small to establish stream ordering or a complete tool loop. A future fixture needs the full sanitized response sequence and enough request context to distinguish a provider payload from client-side reconstruction.

## Maintenance practice from vLLM

- vLLM [PR #50296](https://github.com/vllm-project/vllm/pull/50296) was opened on 2026-07-29 and updated on 2026-08-03. It adds per-parser tool-call format conformance tests using fixed raw bytes and mock tokenizers, so the tests run offline without a GPU, model download, or live server. The PR reports 34 passing tests and calibrates the suite by planting one defect at a time.
- This repository can use the same boundary when a real capture is available: pin the smallest observed wire fragment and keep provider execution outside the test. The PR does not provide a DeepSeek V4 capture for this repository, so it does not justify a new fixture or finding code here.
