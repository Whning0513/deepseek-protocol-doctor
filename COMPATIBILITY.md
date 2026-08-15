# Compatibility Notes

This file records public integration reports that are useful for triage but do not yet contain a protocol capture.

Issue and PR metadata were checked on 2026-08-15 UTC.

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

## Maintenance practice from vLLM

- vLLM [PR #50296](https://github.com/vllm-project/vllm/pull/50296) was opened on 2026-07-29 and updated on 2026-08-03. It adds per-parser tool-call format conformance tests using fixed raw bytes and mock tokenizers, so the tests run offline without a GPU, model download, or live server. The PR reports 34 passing tests and calibrates the suite by planting one defect at a time.
- This repository can use the same boundary when a real capture is available: pin the smallest observed wire fragment and keep provider execution outside the test. The PR does not provide a DeepSeek V4 capture for this repository, so it does not justify a new fixture or finding code here.

vLLM [PR #52255](https://github.com/vllm-project/vllm/pull/52255) was opened on 2026-08-14 and remained open on 2026-08-15. The patch attaches request-level tools to an existing system or developer message, restores the checkpoint's [reference golden](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash-0731/blob/main/encoding/test_output_1.txt), and adds four renderer tests. The PR body reports four restored goldens and the new tests passing; that result was not independently rerun here.

This is prompt-rendering parity evidence, not a provider response capture. It supports keeping backend golden tests tied to an upstream reference and recording the exact layer under test. It does not justify changing request-history validation or adding a stream fixture to this repository.

## DeepSeek V4 tokenizer and renderer reports

- vLLM [#51829](https://github.com/vllm-project/vllm/issues/51829) was opened on 2026-08-11 and reports that the Python DeepSeek V4 renderer places request-level tools in a synthetic system message even when an existing system message is present. The report compares Python, Rust, and the checkpoint reference encoder and includes a tokenizer-only reproduction without a GPU. This is a prompt-rendering parity issue, not a request-history or SSE finding in this project.
- vLLM [#52253](https://github.com/vllm-project/vllm/issues/52253) was opened on 2026-08-14 and [#52254](https://github.com/vllm-project/vllm/pull/52254) was opened the same day. They document a tools-present history where an assistant turn without `reasoning` was rendered as an empty `<think></think>` block, compare it with the checkpoint's expected encoding, and add encoder tests for missing and empty reasoning. The report provides an encoder-level reproduction, not a provider response capture; it does not justify changing `REASONING_CONTENT_MISSING` or adding a fixture here.
- SGLang [#33185](https://github.com/sgl-project/sglang/issues/33185) was opened on 2026-08-01 and updated on 2026-08-06. It compares the three `low`, `high`, and `max` reasoning-effort prompts in the DeepSeek-V4-Flash-0731 reference encoder with SGLang's mapping and includes a static source check plus a live reproduction script. The issue concerns backend template selection and does not establish a request or stream shape that this checker can validate.

These reports support a separate backend/template compatibility track. Until a complete sanitized request, rendered prompt or ordered response capture is available, keep them as evidence notes rather than protocol fixtures.
