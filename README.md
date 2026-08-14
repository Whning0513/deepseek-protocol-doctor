# DeepSeek Protocol Doctor

一个零依赖的离线诊断器，用来检查 DeepSeek V4-Pro / V4-Flash 在 OpenAI-compatible 客户端里的请求历史和流式响应。

它针对的是社区里最容易把“模型能力问题”误判成“模型不行”的一层：工具循环、`reasoning_content` 生命周期、流式增量聚合和请求边界。默认不联网、不读取 API key、不产生调用费用。

## 为什么做这个

DeepSeek 官方把 V4 API 暴露为 OpenAI Chat Completions / Anthropic-compatible 接口，并提供工具调用和 thinking mode。实际接入时，接口外形兼容不等于每个客户端的消息生命周期都兼容：

- thinking 工具循环需要保留 assistant 返回的原始 `reasoning_content`；
- 流式 `tool_calls` 的增量可能按 index 交错到达；
- 某些 chunk 的 `choices` 为空，不能直接假定每个 chunk 都有 choice；
- 工具参数必须等增量拼完后再按 JSON 解析；
- `max_tokens`、严格 schema 和 beta 路由会改变失败方式。

DSH 已经把其中很多行为做成了完整 harness。本项目选择一个更窄的、适合放进任意仓库 CI 的入口：输入一份真实请求或 SSE 录制，几秒内告诉你“下一次请求会在哪个边界出问题”。它是独立社区工具，不是 DeepSeek 官方组件，也不取代 DSH。

## 快速开始

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

dsv4-doctor check fixtures/valid_tool_loop.json
dsv4-doctor check fixtures/invalid_tool_loop.json
dsv4-doctor stream fixtures/stream_interleaved.jsonl
```

也可以不安装，直接运行：

```bash
PYTHONPATH=src python -m dsv4doctor check fixtures/valid_tool_loop.json
```

退出码为 1 表示存在 error；warning 默认不阻断，可用 `--fail-on-warning` 让 CI 更严格。

## CI / GitHub Actions

诊断结果可以输出成 SARIF，接到 GitHub Code Scanning 或其他 SARIF 消费器：

```bash
dsv4-doctor check artifacts/request.json --format sarif > dsv4-doctor.sarif
dsv4-doctor stream artifacts/response.sse --format sarif > dsv4-stream.sarif
```

输入既可以是完整请求 envelope，也可以只是 `messages` 数组。流式检查接受 `data: {...}` SSE 行和裸 JSONL 行。

## 当前检查项

| 代码 | 检查 |
| --- | --- |
| `REASONING_CONTENT_MISSING` | assistant 发起工具调用、下一条是 tool 结果，但没有保留原始 reasoning |
| `TOOL_RESULT_ORPHAN` | tool 结果的 `tool_call_id` 找不到对应调用 |
| `TOOL_ARGUMENTS_INVALID` | 非流式工具参数不是合法 JSON |
| `SSE_TOOL_INDICES_INTERLEAVED` | 流式工具增量交错，报告按 index 聚合的结果 |
| `SSE_EMPTY_CHOICES` | 发现可容忍的 `choices=[]` chunk |
| `STRICT_*` | 检查 strict function schema 的 required / additionalProperties 约束 |
| `MAX_TOKENS_*` | 检查是否显式设置了正的 max_tokens |
| `BETA_TOOL_ROUTE` | 工具调用请求疑似走了 `/beta` 路由 |

工具不会自动伪造缺失的 `reasoning_content`：那样虽然可能绕过一次 400，却会把不可验证的内容写回会话。报告会给出修复建议，由上层 harness 决定如何保留原始响应。

## 设计边界

这是一个“协议体检”而不是 benchmark：

1. `check` 只审计输入中实际存在的字段，不会向 DeepSeek 发请求。
2. `thinking=auto` 按 V4 社区 harness 的默认兼容策略检查工具循环；如果调用方明确关闭 thinking，可使用 `--thinking disabled`，或者在请求中设置 `extra_body.thinking.type`。
3. 上下文 token 数需要真实 tokenizer 才能精确计算；本版本只检查 `max_tokens` 的显式性和上限，不伪装成精确 token 计数器。
4. 对 OpenRouter、vLLM、SGLang 等中转/本地服务，协议行为可能不同；应分别保存 fixture 和运行 CI。

## 开发

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

下一步适合的贡献方向：把各客户端的真实失败录制转成匿名 fixture；增加 Open WebUI / Cline / OpenCode 的适配器；增加不同 provider 和本地推理后端的兼容性矩阵；最后再把稳定规则反馈给 DSH 或上游客户端。

## 参考资料

- [DeepSeek V4 Preview Release](https://api-docs.deepseek.com/news/news260424/)
- [DeepSeek Tool Calls 文档](https://api-docs.deepseek.com/guides/tool_calls/)
- [deepseek-harness / DSH](https://github.com/HenryZ838978/deepseek-harness)
- [Open WebUI 的 V4 工具调用讨论](https://github.com/open-webui/open-webui/discussions/24080)
- [DeepSeek V4 工具调用空响应 issue](https://github.com/deepseek-ai/DeepSeek-V3/issues/1453)
- [DeepSeek V4 模型社区讨论](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro/discussions)
