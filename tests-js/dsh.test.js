import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { inspectRequest, inspectStream } from '../dsh/runner.js'
import { createToolDefinitions } from '../dsh/tools.js'

const fixture = name => new URL(`../fixtures/${name}`, import.meta.url)

test('request wrapper returns a passing structured report', async () => {
  const payload = JSON.parse(await readFile(fixture('valid_tool_loop.json'), 'utf8'))
  const report = await inspectRequest(payload)

  assert.equal(report.kind, 'request')
  assert.equal(report.ok, true)
  assert.deepEqual(report.summary, { errors: 0, warnings: 0, infos: 0 })
})

test('request findings are results rather than process failures', async () => {
  const payload = JSON.parse(await readFile(fixture('invalid_tool_loop.json'), 'utf8'))
  const report = await inspectRequest(payload)

  assert.equal(report.ok, false)
  assert.ok(report.findings.some(finding => finding.code === 'REASONING_CONTENT_MISSING'))
})

test('stream wrapper reassembles interleaved tool calls', async () => {
  const stream = await readFile(fixture('stream_interleaved.jsonl'), 'utf8')
  const report = await inspectStream(stream)

  assert.equal(report.kind, 'stream')
  assert.equal(report.facts.interleaved_tool_indices, true)
  assert.equal(report.facts.tool_calls.length, 2)
})

test('DSH definitions expose two cancellable, read-only tools', async () => {
  const definitions = createToolDefinitions(value => value)
  assert.deepEqual(
    definitions.map(definition => definition.name),
    ['deepseek_protocol_check', 'deepseek_stream_check'],
  )
  assert.ok(definitions.every(definition => definition.timeoutMs === 30_000))
  assert.ok(definitions.every(definition => definition.output.schema.type === 'json'))

  const report = await definitions[0].execute(
    { payload: { messages: [] }, thinking: 'disabled' },
    { signal: new AbortController().signal },
  )
  assert.equal(report.ok, true)
})

test('pre-aborted execution does not start Python', async () => {
  const controller = new AbortController()
  controller.abort()
  await assert.rejects(
    inspectRequest({ messages: [] }, { signal: controller.signal }),
    error => error.name === 'AbortError',
  )
})
