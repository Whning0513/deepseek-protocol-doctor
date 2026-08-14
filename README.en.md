# DeepSeek Protocol Doctor

English | [中文](README.md)

[![test](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml/badge.svg)](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/Whning0513/deepseek-protocol-doctor)](https://github.com/Whning0513/deepseek-protocol-doctor/releases)
[![license](https://img.shields.io/github/license/Whning0513/deepseek-protocol-doctor)](LICENSE)

An offline-by-default DeepSeek request doctor with no Python runtime dependencies, also packaged as a source-installable [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/deepseek-harness) plugin.

It checks the protocol boundaries that are often mistaken for model-quality problems in OpenAI-compatible clients: tool loops, the `reasoning_content` lifecycle, strict schemas, thinking mode, `max_tokens`, and streamed tool-argument assembly. It makes no network requests, reads no API keys, and incurs no model usage costs.

> This is an independent community project, not an official DeepSeek component. DSH is currently a developer preview and its plugin interfaces may change.

## Install as a DSH plugin

You need a DSH-supported Node.js version and Python 3.10+ on PATH. Replace the example `demo` profile with your profile:

```bash
dsh plugin --profile demo add github:Whning0513/deepseek-protocol-doctor
```

Restart that DSH process. The bundle registers two read-only tools:

| Tool | Input | Purpose |
| --- | --- | --- |
| `deepseek_protocol_check` | Request object or bare `messages` array | Check reasoning preservation, tool-call/result pairing, schemas, and request options |
| `deepseek_stream_check` | SSE or JSONL text | Reassemble streamed tool arguments by index and validate the final JSON |

Example prompts:

```text
Use deepseek_protocol_check to audit this request before I send it: { ... }
Use deepseek_stream_check to inspect this captured SSE stream: "data: {...}\n..."
```

The plugin invokes the bundled Python core through a shell-free child process. Input and output are each capped at 4 MiB, and execution observes DSH cancellation. If Python is not on the default PATH, set `DSV4_DOCTOR_PYTHON` to the interpreter executable path.

## Use as a CLI

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

dsv4-doctor check fixtures/valid_tool_loop.json
dsv4-doctor check fixtures/invalid_tool_loop.json
dsv4-doctor stream fixtures/stream_interleaved.jsonl
```

Or run without installing:

```bash
PYTHONPATH=src python -m dsv4doctor check fixtures/valid_tool_loop.json
```

The request input may be a full envelope or a bare `messages` array. Stream inspection accepts `data: {...}` SSE lines and raw JSONL. Exit code 1 means the report contains an error; warnings are non-blocking unless `--fail-on-warning` is used.

## CI and SARIF

Reports are available as text, JSON, or SARIF:

```bash
dsv4-doctor check artifacts/request.json --format json
dsv4-doctor check artifacts/request.json --format sarif > dsv4-doctor.sarif
dsv4-doctor stream artifacts/response.sse --format sarif > dsv4-stream.sarif
```

Checks currently cover:

- missing `reasoning_content` across a thinking tool loop;
- orphaned, duplicated, missing, or incomplete tool calls and results;
- malformed non-streaming and aggregated streaming tool arguments;
- interleaved tool-call deltas and tolerated empty-choice chunks;
- DeepSeek strict-schema constraints;
- explicit thinking mode, `max_tokens`, and suspicious beta routes.

The doctor never invents missing `reasoning_content`. Synthesizing it may evade one validation error while corrupting the conversation; the report provides a fix hint and leaves preservation of the real response to the host harness.

## Scope

This is a protocol doctor, not a benchmark. It inspects only supplied fields and never calls a provider. It does not bundle a tokenizer, so token-related checks are static rather than a claim of exact context accounting. Proxies and local backends such as OpenRouter, vLLM, and SGLang can differ; keep separate anonymized fixtures for each behavior.

## Development and contributions

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

The most useful contributions are reproducible, sanitized failure captures and compatibility rules for clients such as Open WebUI, Cline, OpenCode, and local inference stacks. Read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting one.

## Community and references

- [DSH GitHub Discussions](https://github.com/deepseek-ai/deepseek-harness/discussions) (Show and tell is a good fit for plugins)
- [GitHub `dsh-plugin` topic](https://github.com/topics/dsh-plugin)
- [DSH Discord](https://discord.gg/Ycq5dCaS4)
- [DeepSeek Discord](https://discord.gg/Tc7c45Zzu5)
- [DeepSeek Tool Calls guide](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek V4 Preview Release](https://api-docs.deepseek.com/news/news260424/)

MIT License
