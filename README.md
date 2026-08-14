# DeepSeek Protocol Doctor

[English](README.en.md) | 中文

[![test](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml/badge.svg)](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml)
[![GitHub release](https://img.shields.io/github/v/release/Whning0513/deepseek-protocol-doctor)](https://github.com/Whning0513/deepseek-protocol-doctor/releases)
[![license](https://img.shields.io/github/license/Whning0513/deepseek-protocol-doctor)](LICENSE)

一个零依赖、默认离线的 DeepSeek 请求体检器，也是可从 GitHub 直接安装的 [DeepSeek Harness（DSH）](https://github.com/deepseek-ai/deepseek-harness) 插件。

它检查 OpenAI-compatible 客户端里最容易被误判成“模型能力问题”的协议边界：工具调用循环、`reasoning_content` 生命周期、strict schema、thinking mode、`max_tokens`，以及 SSE 工具参数增量聚合。它不联网、不读取 API key，也不会产生模型调用费用。

> 本项目是独立社区工具，不是 DeepSeek 官方组件。目前 DSH 仍处于 developer preview，插件接口可能变化。

## 作为 DSH 插件安装

要求：DSH 支持的 Node.js 版本，以及 PATH 中可用的 Python 3.10+。`demo` 是 profile 示例，请替换成你实际使用的 profile：

```bash
dsh plugin --profile demo add github:Whning0513/deepseek-protocol-doctor
```

重启对应 DSH 进程后，会注册两个只读工具：

| 工具 | 输入 | 用途 |
| --- | --- | --- |
| `deepseek_protocol_check` | 请求对象或 `messages` 数组 | 检查 reasoning、工具调用/结果配对、schema 与请求选项 |
| `deepseek_stream_check` | SSE 或 JSONL 文本 | 按 index 重组流式工具参数并检查最终 JSON |

可以直接让 Agent 调用，例如：

```text
Use deepseek_protocol_check to audit this request before I send it: { ... }
Use deepseek_stream_check to inspect this captured SSE stream: "data: {...}\n..."
```

插件通过无 shell 的子进程调用仓库内自带的 Python 核心；输入和输出各限制为 4 MiB，并会响应 DSH 的取消信号。若 Python 不在默认 PATH，可把 `DSV4_DOCTOR_PYTHON` 设置为解释器的可执行文件路径。

## 作为 CLI 使用

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

dsv4-doctor check fixtures/valid_tool_loop.json
dsv4-doctor check fixtures/invalid_tool_loop.json
dsv4-doctor stream fixtures/stream_interleaved.jsonl
```

也可以不安装：

```bash
PYTHONPATH=src python -m dsv4doctor check fixtures/valid_tool_loop.json
```

输入可以是完整请求 envelope，也可以只是 `messages` 数组。流式检查接受 `data: {...}` SSE 行和裸 JSONL 行。退出码 1 表示存在 error；warning 默认不阻断，可用 `--fail-on-warning` 让 CI 更严格。

## CI / GitHub Code Scanning

报告支持纯文本、JSON 和 SARIF：

```bash
dsv4-doctor check artifacts/request.json --format json
dsv4-doctor check artifacts/request.json --format sarif > dsv4-doctor.sarif
dsv4-doctor stream artifacts/response.sse --format sarif > dsv4-stream.sarif
```

## 当前检查项

| 代码 | 检查 |
| --- | --- |
| `REASONING_CONTENT_MISSING` | assistant 发起工具调用后，没有在历史中保留原始 reasoning |
| `TOOL_RESULT_ORPHAN` / `TOOL_RESULTS_*` | tool 结果无法对应调用，或结果不完整 |
| `TOOL_ARGUMENTS_INVALID` | 非流式工具参数不是合法 JSON |
| `SSE_TOOL_INDICES_INTERLEAVED` | 流式工具增量交错，并报告按 index 聚合的结果 |
| `SSE_EMPTY_CHOICES` | 发现可容忍的 `choices=[]` chunk |
| `STRICT_*` | strict function schema 的 required / additionalProperties 约束 |
| `MAX_TOKENS_*` | `max_tokens` 缺失、无效或超出上下文上限 |
| `THINKING_*` | thinking mode 未显式声明或值无效 |
| `BETA_TOOL_ROUTE` | 工具调用请求疑似走了 `/beta` 路由 |

工具不会伪造缺失的 `reasoning_content`。伪造内容即使绕过一次请求校验，也会污染会话；报告只给出修复建议，由上层 harness 保留真实原始响应。

## 设计边界

这是协议体检，不是 benchmark：

1. 只审计输入里实际存在的字段，不会向 DeepSeek 或其他 provider 发请求。
2. `thinking=auto` 按请求字段和兼容默认值检查；显式关闭时可使用 `--thinking disabled`。
3. 本版本不内置 tokenizer，只检查 `max_tokens` 的显式性和静态上限，不声称提供精确 token 计数。
4. OpenRouter、vLLM、SGLang 等中转或本地后端可能有不同协议行为，建议分别保存匿名 fixture。

## 开发与贡献

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

最有价值的贡献是可复现、已脱敏的真实失败录制，以及 Open WebUI、Cline、OpenCode、本地推理后端等客户端的兼容规则。提交前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 社区与资料

- [DSH GitHub Discussions](https://github.com/deepseek-ai/deepseek-harness/discussions)（插件展示建议发到 Show and tell）
- [GitHub `dsh-plugin` topic](https://github.com/topics/dsh-plugin)
- [DSH Discord](https://discord.gg/Ycq5dCaS4)
- [DeepSeek Discord](https://discord.gg/Tc7c45Zzu5)
- [DeepSeek Tool Calls 文档](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek V4 Preview Release](https://api-docs.deepseek.com/news/news260424/)

MIT License
