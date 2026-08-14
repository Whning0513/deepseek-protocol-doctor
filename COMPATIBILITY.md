# Compatibility Notes

This file records public integration reports that are useful for triage but do not yet contain a protocol capture.

Issue metadata and comments were checked on 2026-08-14 UTC.

## Cline with Ollama and local DeepSeek models

Public reports:

- [Cline #1653](https://github.com/cline/cline/issues/1653) was opened on 2025-02-05 and closed on 2025-06-21. It describes local DeepSeek models served by Ollama getting stuck in a tool-execution loop. The discussion focuses on the Ollama `num_ctx` setting and does not include a request, SSE/JSONL capture, HTTP status, or model response.
- [Cline #4362](https://github.com/cline/cline/issues/4362) was opened on 2025-06-21, closed on 2025-07-26, and last updated on 2025-08-04. It consolidates reports about Ollama compatibility and iterative tool use. The issue was closed as experimental support; its discussion does not provide a protocol capture that identifies a tool-call ID, message-history, `reasoning_content`, or stream-fragment failure.

Current assessment: these reports are behavior evidence, not fixtures. The doctor cannot determine from them whether the boundary is context exhaustion, model capability, client history reconstruction, endpoint behavior, or streamed tool-call handling. Do not add a finding code or fixture based on these reports alone.

A useful follow-up capture should include the client and backend versions, model and endpoint shape, thinking configuration, the smallest complete request or SSE/JSONL stream, and the observed HTTP error. Remove credentials, user content, private URLs, local paths, account IDs, and business data before sharing it.
