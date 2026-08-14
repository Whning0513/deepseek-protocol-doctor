import { inspectRequest, inspectStream } from './runner.js'

const reportOutput = {
  schema: { type: 'json' },
  render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
}

export function createToolDefinitions(defineTool) {
  return [
    defineTool({
      name: 'deepseek_protocol_check',
      description:
        'Offline, read-only validation of a DeepSeek/OpenAI-compatible request or message history. '
        + 'Checks tool-call/result pairing, reasoning_content preservation, strict schemas, thinking mode, '
        + 'max_tokens, and endpoint pitfalls. It never sends an API request or reads API keys.',
      parameters: {
        payload: {
          type: 'json',
          required: true,
          description: 'OpenAI-compatible request object or a bare messages array.',
        },
        thinking: {
          type: 'string',
          enum: ['auto', 'enabled', 'disabled'],
          description: 'Override thinking-mode detection; defaults to auto.',
        },
      },
      output: reportOutput,
      timeoutMs: 30_000,
      isConcurrencySafe: () => true,
      execute(args, exec) {
        return inspectRequest(args.payload, {
          thinking: args.thinking ?? 'auto',
          signal: exec.signal,
        })
      },
    }),
    defineTool({
      name: 'deepseek_stream_check',
      description:
        'Offline, read-only inspection of a captured OpenAI-compatible SSE or JSONL stream. '
        + 'Reassembles interleaved tool-call deltas by index, validates final arguments, and tolerates '
        + 'empty choices chunks. It never connects to a provider.',
      parameters: {
        stream: {
          type: 'string',
          required: true,
          description: 'Captured SSE text (data: lines) or one JSON object per line.',
        },
      },
      output: reportOutput,
      timeoutMs: 30_000,
      isConcurrencySafe: () => true,
      execute(args, exec) {
        return inspectStream(args.stream, { signal: exec.signal })
      },
    }),
  ]
}
