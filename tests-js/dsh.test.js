import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
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

test('stream wrapper preserves the null-arguments information finding', async () => {
  const stream = JSON.stringify({
    choices: [
      {
        delta: {
          tool_calls: [
            { index: 0, function: { name: 'search_web', arguments: null } },
          ],
        },
      },
    ],
  })
  const report = await inspectStream(stream)

  assert.equal(report.ok, true)
  assert.deepEqual(report.summary, { errors: 0, warnings: 0, infos: 1 })
  assert.equal(report.findings[0].code, 'SSE_TOOL_ARGUMENTS_NULL')
  assert.equal(report.findings[0].severity, 'info')
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

test('DSV4_DOCTOR_PYTHON selects the configured interpreter', async () => {
  const command = process.platform === 'win32' ? 'python' : 'python3'
  const configured = execFileSync(
    command,
    ['-c', 'import sys; print(sys.executable)'],
    { encoding: 'utf8' },
  ).trim()
  const previousPython = process.env.DSV4_DOCTOR_PYTHON
  process.env.DSV4_DOCTOR_PYTHON = configured

  try {
    const report = await inspectRequest({ messages: [] }, { thinking: 'disabled' })
    assert.equal(report.kind, 'request')
    assert.equal(report.ok, true)
  } finally {
    if (previousPython === undefined) delete process.env.DSV4_DOCTOR_PYTHON
    else process.env.DSV4_DOCTOR_PYTHON = previousPython
  }
})

test('pre-aborted execution does not start Python', async () => {
  const controller = new AbortController()
  controller.abort()
  await assert.rejects(
    inspectRequest({ messages: [] }, { signal: controller.signal }),
    error => error.name === 'AbortError',
  )
})

test('cancelling a running doctor terminates the child process', { skip: process.platform === 'win32' }, async () => {
  const directory = await mkdtemp(join(tmpdir(), 'dsv4-doctor-'))
  const executable = join(directory, 'sleeping-python.sh')
  const previousPython = process.env.DSV4_DOCTOR_PYTHON
  await writeFile(executable, '#!/bin/sh\nexec sleep 30\n', 'utf8')
  await chmod(executable, 0o755)
  process.env.DSV4_DOCTOR_PYTHON = executable
  const controller = new AbortController()
  const pending = inspectRequest(
    { messages: [] },
    { thinking: 'disabled', signal: controller.signal },
  )
  const abortTimer = setTimeout(() => controller.abort(), 25)

  try {
    await assert.rejects(pending, error => error.name === 'AbortError')
  } finally {
    clearTimeout(abortTimer)
    if (previousPython === undefined) delete process.env.DSV4_DOCTOR_PYTHON
    else process.env.DSV4_DOCTOR_PYTHON = previousPython
    await rm(directory, { recursive: true, force: true })
  }
})

test('input larger than 4 MiB is rejected before Python starts', async () => {
  await assert.rejects(
    inspectStream('x'.repeat(4 * 1024 * 1024 + 1)),
    error => error instanceof RangeError && /limit is 4194304$/.test(error.message),
  )
})

test('unsupported thinking mode is rejected before Python starts', () => {
  assert.throws(
    () => inspectRequest({ messages: [] }, { thinking: 'sometimes' }),
    error => error instanceof TypeError && /unsupported thinking mode/.test(error.message),
  )
})

test('output larger than 4 MiB is terminated and reported', { skip: process.platform === 'win32' }, async () => {
  const directory = await mkdtemp(join(tmpdir(), 'dsv4-doctor-'))
  const executable = join(directory, 'emit-output.sh')
  const previousPython = process.env.DSV4_DOCTOR_PYTHON
  await writeFile(executable, '#!/bin/sh\nprintf \'%4194305s\' x\n', 'utf8')
  await chmod(executable, 0o755)
  process.env.DSV4_DOCTOR_PYTHON = executable

  try {
    await assert.rejects(
      inspectRequest({ messages: [] }),
      error => /doctor output exceeded 4194304 bytes/.test(error.message),
    )
  } finally {
    if (previousPython === undefined) delete process.env.DSV4_DOCTOR_PYTHON
    else process.env.DSV4_DOCTOR_PYTHON = previousPython
    await rm(directory, { recursive: true, force: true })
  }
})

test('Unix Python lookup falls back from python3 to python', { skip: process.platform === 'win32' }, async () => {
  const realPython = execFileSync(
    'python3',
    ['-c', 'import sys; print(sys.executable)'],
    { encoding: 'utf8' },
  ).trim()
  const directory = await mkdtemp(join(tmpdir(), 'dsv4-doctor-'))
  const fallback = join(directory, 'python')
  const previousPath = process.env.PATH
  const previousPython = process.env.DSV4_DOCTOR_PYTHON
  await writeFile(fallback, `#!/bin/sh\nexec ${realPython} "$@"\n`, 'utf8')
  await chmod(fallback, 0o755)
  process.env.PATH = directory
  delete process.env.DSV4_DOCTOR_PYTHON

  try {
    const report = await inspectRequest({ messages: [] }, { thinking: 'disabled' })
    assert.equal(report.kind, 'request')
    assert.equal(report.ok, true)
  } finally {
    if (previousPath === undefined) delete process.env.PATH
    else process.env.PATH = previousPath
    if (previousPython === undefined) delete process.env.DSV4_DOCTOR_PYTHON
    else process.env.DSV4_DOCTOR_PYTHON = previousPython
    await rm(directory, { recursive: true, force: true })
  }
})
