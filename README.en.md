# DeepSeek Protocol Doctor

English | [中文](README.md)

[![test](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml/badge.svg)](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml)

While wiring up DeepSeek tool calling, I kept running into failures that looked like model problems at first: a tool result was present but the next request still returned 400; a stream looked fine until the assembled arguments failed JSON parsing; the same history worked with thinking disabled and failed when it was enabled.

Many of these turned out to be request/response assembly bugs. This tool takes a request JSON or a captured SSE stream and checks the common cases before you spend time debugging the model. It only reads the input you give it and does not call a provider.

## Install in DSH

Replace `demo` with the profile you use:

```bash
dsh plugin --profile demo add github:Whning0513/deepseek-protocol-doctor
```

Restart DSH. The plugin adds two tools:

- `deepseek_protocol_check` checks a request or message history.
- `deepseek_stream_check` checks a captured SSE or JSONL stream.

For example:

```text
Use deepseek_protocol_check to find the tool-calling problem in this request: { ... }
```

The plugin needs Python 3.10+. If `python3` is not on PATH, set `DSV4_DOCTOR_PYTHON` to the interpreter you want it to use.

## Use it as an Agent Skill

The repository also includes a standard `SKILL.md` at [`skills/deepseek-protocol-doctor`](skills/deepseek-protocol-doctor). DSH discovers skills from a project's `.agents/skills/` or `.dsh/skills/` directory and their user-level equivalents. Other Agent Skills-compatible clients can copy the same directory.

For example, install it for the current project:

```bash
mkdir -p .agents/skills
cp -R /path/to/deepseek-protocol-doctor/skills/deepseek-protocol-doctor .agents/skills/
```

The skill defines the debugging workflow and calls the existing `dsv4-doctor`; it does not duplicate the protocol checker.

## Command line

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

dsv4-doctor check fixtures/valid_tool_loop.json
dsv4-doctor check fixtures/invalid_tool_loop.json
dsv4-doctor stream fixtures/stream_interleaved.jsonl
```

It also runs without installation:

```bash
PYTHONPATH=src python -m dsv4doctor check fixtures/valid_tool_loop.json
```

`check` accepts a full OpenAI-compatible request or a bare `messages` array. `stream` accepts SSE and JSONL.

Exit code 1 means the report contains an error. Warnings do not fail CI unless `--fail-on-warning` is set.

## What it checks today

- tool messages that do not match a `tool_call_id`, and tool loops that move on before every result arrives;
- missing original `reasoning_content` in a thinking tool loop;
- `function.arguments` parsed before all stream deltas arrive;
- interleaved tool-call deltas appended in arrival order instead of grouped by index;
- missing `required` or `additionalProperties: false` in strict schemas;
- a few easy-to-miss settings around `max_tokens`, thinking mode, and `/beta` routes.

Every finding has a stable code for CI use. Output is available as text, JSON, or SARIF:

```bash
dsv4-doctor check request.json --format json
dsv4-doctor check request.json --format sarif > result.sarif
```

The doctor will not invent missing `reasoning_content`. That field should be the exact value returned by the model; making up a replacement may get past one check while writing bad state back into the conversation.

## Current limitations

- This checks requests; it is not a benchmark and says nothing about answer quality.
- There is no bundled tokenizer. `max_tokens` checks are static rather than a claim of exact token counting.
- OpenRouter, vLLM, SGLang, and other compatible endpoints have behavior that is not fully covered yet.
- DSH is still a developer preview. This wrapper may need updates as its plugin API changes.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

If you have a real failure capture, sanitize it and open an issue with a small fixture. Cases from Open WebUI, Cline, OpenCode, and local inference backends would be especially useful. See [CONTRIBUTING.md](CONTRIBUTING.md) for the fixture rules.

## Links

- [DeepSeek Harness / DSH](https://github.com/deepseek-ai/deepseek-harness)
- [DSH Discussions](https://github.com/deepseek-ai/deepseek-harness/discussions)
- [DeepSeek Tool Calls guide](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek V4 Preview Release](https://api-docs.deepseek.com/news/news260424/)

This is a third-party project, not an official DeepSeek component. MIT License.
