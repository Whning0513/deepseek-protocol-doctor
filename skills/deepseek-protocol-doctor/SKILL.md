---
name: deepseek-protocol-doctor
description: Diagnose DeepSeek request histories, tool-call loops, reasoning_content handling, and OpenAI-compatible SSE captures. Use when a DeepSeek or DSH integration returns a 400 error, loses tool results, produces invalid streamed arguments, behaves differently with thinking enabled, or needs an offline protocol check before blaming the model.
---

# DeepSeek Protocol Doctor

Check the captured request or stream offline. Separate protocol evidence from guesses about model quality.

## Choose the checker

- Use `deepseek_protocol_check` when the DSH plugin tool is available and the input is a request envelope or `messages` array.
- Use `deepseek_stream_check` when the DSH plugin tool is available and the input is an SSE or JSONL capture.
- Otherwise use the `dsv4-doctor` CLI. Prefer an installed command, then the repository source, then the pinned `uvx` command below.

```bash
dsv4-doctor check request.json --format json
dsv4-doctor stream response.jsonl --format json
```

Inside a checkout of the project:

```bash
PYTHONPATH=src python -m dsv4doctor check request.json --format json
```

Without an installation:

```bash
uvx --from git+https://github.com/Whning0513/deepseek-protocol-doctor.git@v0.1.2 \
  dsv4-doctor check request.json --format json
```

Replace `check` with `stream` for SSE or JSONL. Installation may use the network; the actual inspection does not call a model or upload the capture.

## Inspect safely

1. Identify whether the input is a request JSON, bare message array, SSE, or JSONL capture. Do not feed logs or prose to the parser unchanged.
2. Preserve roles, tool-call IDs, ordering, `reasoning_content`, streamed indices, and argument fragments. Redact API keys and private values without changing protocol structure.
3. Run the matching checker with JSON output. Do not modify the capture merely to make validation pass.
4. Group findings into errors, warnings, and facts. Quote the stable finding code and JSON path when present.
5. Explain the smallest client-side fix that follows from the evidence. State when the capture is incomplete or the checker cannot prove the cause.
6. Re-run the same capture after the client change when possible. Use `--fail-on-warning` only when warnings are intended to fail CI.

## Keep the diagnosis honest

- Never invent, summarize, or replace missing `reasoning_content`; preserve the exact field returned by DeepSeek across a tool loop.
- Do not recommend disabling thinking as the default fix. It can hide a broken history reconstruction path.
- Do not make a live API call unless the user explicitly asks for one and supplies the required access.
- Do not call a protocol-valid capture proof that the model chose the correct tool or arguments. That requires a task-level evaluation.
- Treat a pending tool result as valid for a mid-flight capture and suspicious for a completed loop.

Report what was checked, the relevant finding codes, the likely boundary at fault, and one concrete next step.
