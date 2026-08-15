# DeepSeek Protocol Doctor

[English](README.en.md) | 中文

[![test](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml/badge.svg)](https://github.com/Whning0513/deepseek-protocol-doctor/actions/workflows/test.yml)

我在接 DeepSeek tool calling 时碰到过几类很像“模型抽风”的问题：工具结果明明传回去了，请求还是 400；流式输出看着正常，最后拼出来的参数却不是 JSON；同一段 history 在关掉 thinking 后能跑，打开就报错。

最后发现不少问题都出在请求和响应的拼接上。于是写了这个小工具，把 request JSON 或 SSE 录制丢进去，先排查这些常见坑。它只看你给它的内容，不会调用模型。

## 装到 DSH 里

`demo` 换成你正在用的 profile：

```bash
dsh plugin --profile demo add github:Whning0513/deepseek-protocol-doctor
```

重启 DSH 后会多出两个工具：

- `deepseek_protocol_check`：检查请求和消息历史。
- `deepseek_stream_check`：检查保存下来的 SSE / JSONL 流。

比如可以直接对 DSH 说：

```text
用 deepseek_protocol_check 看看这个请求里的工具调用哪里不对：{ ... }
```

插件需要 Python 3.10+。一般能在终端里运行 `python3` 就行；如果 Python 装在别处，可以设置 `DSV4_DOCTOR_PYTHON`。

## 当作 Agent Skill 用

仓库里也带了一个标准 `SKILL.md`：[`skills/deepseek-protocol-doctor`](skills/deepseek-protocol-doctor)。DSH 会从项目的 `.agents/skills/`、`.dsh/skills/`，以及用户目录下的对应位置自动发现它。其他兼容 Agent Skills 的客户端也可以直接复制这个目录。

例如装到当前项目的共享目录：

```bash
mkdir -p .agents/skills
cp -R /path/to/deepseek-protocol-doctor/skills/deepseek-protocol-doctor .agents/skills/
```

Skill 只负责把排查步骤组织好，实际协议检查仍调用同一套 `dsv4-doctor`，没有第二份实现。

## 命令行用法

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .

dsv4-doctor check fixtures/valid_tool_loop.json
dsv4-doctor check fixtures/invalid_tool_loop.json
dsv4-doctor stream fixtures/stream_interleaved.jsonl
```

不想安装也可以直接跑：

```bash
PYTHONPATH=src python -m dsv4doctor check fixtures/valid_tool_loop.json
```

`check` 接受完整的 OpenAI-compatible 请求，也接受单独的 `messages` 数组。`stream` 接受 SSE 和 JSONL。

退出码 1 表示查到了 error。warning 默认不拦 CI；需要严格一点时加 `--fail-on-warning`。

## 现在能查什么

- tool message 找不到对应的 `tool_call_id`，或者一轮调用还没收齐结果就开始了下一轮；
- thinking 工具循环里，assistant 原样返回的 `reasoning_content` 被客户端丢掉；
- `function.arguments` 还没拼完就被当成 JSON 解析；
- 流片段显式给出 `function.arguments: null` 时，记录 `SSE_TOOL_ARGUMENTS_NULL` 信息，不把这个片段单独判为错误；
- 多个流式 tool call 的 delta 交错到达，客户端却按到达顺序直接追加；
- strict schema 漏了 `required` 或 `additionalProperties: false`；
- `max_tokens`、thinking mode 和 `/beta` 路由里几个容易忽略的配置。

报告里每条问题都有固定 code，方便在 CI 里处理。输出支持 text、JSON 和 SARIF：

```bash
dsv4-doctor check request.json --format json
dsv4-doctor check request.json --format sarif > result.sarif
```

工具不会替你补一段假的 `reasoning_content`。这个字段应该保存模型原始返回值；伪造一个字符串虽然可能绕过一次检查，但会把错误内容写回会话。

## 目前的限制

- 这是请求检查器，不是 benchmark，也不会判断回答质量。
- 没有内置 tokenizer，所以只做静态的 `max_tokens` 检查，不给出假装精确的 token 数。
- OpenRouter、vLLM、SGLang 和其他兼容接口可能有自己的行为，目前还没有完整覆盖。
- DSH 还在 developer preview；如果上游插件接口变化，这里的包装也需要跟着改。

## 开发

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
npm test
npm pack --dry-run
```

如果你手上有真实失败记录，欢迎先脱敏，再放进 `fixtures/` 提 issue。最想补的是 Open WebUI、Cline、OpenCode 和本地推理后端的案例。具体要求写在 [CONTRIBUTING.md](CONTRIBUTING.md)。

公开但缺少协议 capture 的兼容性报告记录在 [COMPATIBILITY.md](COMPATIBILITY.md)。这些报告不能直接转成 finding 或 fixture。

## 相关链接

- [DeepSeek Harness / DSH](https://github.com/deepseek-ai/deepseek-harness)
- [DSH Discussions](https://github.com/deepseek-ai/deepseek-harness/discussions)
- [DeepSeek Tool Calls 文档](https://api-docs.deepseek.com/guides/tool_calls/)
- [DeepSeek V4 Preview Release](https://api-docs.deepseek.com/news/news260424/)

这是第三方项目，不是 DeepSeek 官方组件。MIT License。
