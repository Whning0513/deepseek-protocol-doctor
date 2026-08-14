# Contributing

Thanks for helping turn real DeepSeek integration failures into reproducible protocol checks.

## Good first contributions

- Add an anonymized request or SSE/JSONL fixture that reproduces a client bug.
- Add a regression rule with one passing and one failing test.
- Document behavior differences in Open WebUI, Cline, OpenCode, OpenRouter, vLLM, SGLang, or another compatible client/backend.
- Improve the DSH tool descriptions, output shape, installation path, or cross-platform Python discovery.

## Fixture safety

Before committing a capture, remove API keys, cookies, authorization headers, user prompts, private URLs, file paths, account IDs, and business data. Replace identifiers consistently so tool-call relationships still reproduce. Keep only the smallest request or stream needed to expose the behavior.

Never submit secrets, even in a private issue. The doctor is offline, but fixtures committed to Git are public and durable.

## Protocol rules

A new rule should include:

1. A stable machine-readable finding code.
2. A short description of the observed failure boundary.
3. A practical repair hint that does not fabricate model output.
4. Tests for both the triggering input and a nearby valid input.
5. A link in the pull request to official documentation, an upstream issue, or a minimal reproduction when available.

Warnings should describe risky but potentially valid input. Errors should be reserved for malformed or internally inconsistent protocol state.

## Run the checks

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

The DSH wrapper must remain offline and read-only. Do not add provider calls, credential discovery, shell command interpolation, or telemetry to either tool.
