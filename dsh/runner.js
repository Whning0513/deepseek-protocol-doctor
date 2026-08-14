import { spawn } from 'node:child_process'
import { delimiter, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const PLUGIN_ROOT = dirname(dirname(fileURLToPath(import.meta.url)))
const SOURCE_ROOT = join(PLUGIN_ROOT, 'src')
const MAX_INPUT_BYTES = 4 * 1024 * 1024
const MAX_OUTPUT_BYTES = 4 * 1024 * 1024

export function inspectRequest(payload, options = {}) {
  const thinking = options.thinking ?? 'auto'
  if (!['auto', 'enabled', 'disabled'].includes(thinking)) {
    throw new TypeError(`unsupported thinking mode: ${thinking}`)
  }
  return runDoctor('check', `${JSON.stringify(payload)}\n`, {
    ...options,
    extraArgs: ['--thinking', thinking],
  })
}

export function inspectStream(stream, options = {}) {
  if (typeof stream !== 'string') {
    throw new TypeError('stream must be a string containing SSE or JSONL')
  }
  return runDoctor('stream', stream, options)
}

async function runDoctor(command, input, options) {
  const inputBytes = Buffer.byteLength(input)
  if (inputBytes > MAX_INPUT_BYTES) {
    throw new RangeError(`input is ${inputBytes} bytes; limit is ${MAX_INPUT_BYTES}`)
  }

  const signal = options.signal
  if (signal?.aborted) throw abortError()

  const configuredPython = process.env.DSV4_DOCTOR_PYTHON
  const candidates = configuredPython
    ? [{ command: configuredPython, prefixArgs: [] }]
    : process.platform === 'win32'
      ? [
          { command: 'python', prefixArgs: [] },
          { command: 'py', prefixArgs: ['-3'] },
          { command: 'python3', prefixArgs: [] },
        ]
      : [
          { command: 'python3', prefixArgs: [] },
          { command: 'python', prefixArgs: [] },
        ]

  let lastMissingError
  for (const candidate of candidates) {
    try {
      return await spawnDoctor(candidate, command, input, options)
    } catch (error) {
      if (error?.code !== 'ENOENT') throw error
      lastMissingError = error
    }
  }
  const detail = lastMissingError?.message ?? 'no Python executable found'
  throw new Error(
    `DeepSeek Protocol Doctor requires Python 3.10+ (${detail}). `
      + 'Set DSV4_DOCTOR_PYTHON to an executable path.',
  )
}

function spawnDoctor(python, command, input, options) {
  return new Promise((resolve, reject) => {
    const pythonPath = process.env.PYTHONPATH
      ? `${SOURCE_ROOT}${delimiter}${process.env.PYTHONPATH}`
      : SOURCE_ROOT
    const child = spawn(
      python.command,
      [
        ...python.prefixArgs,
        '-m',
        'dsv4doctor',
        command,
        '-',
        '--format',
        'json',
        ...(options.extraArgs ?? []),
      ],
      {
        cwd: PLUGIN_ROOT,
        env: { ...process.env, PYTHONPATH: pythonPath },
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      },
    )

    const stdout = []
    const stderr = []
    let stdoutBytes = 0
    let stderrBytes = 0
    let outputOverflow = false
    let settled = false

    const finish = (callback) => {
      if (settled) return
      settled = true
      options.signal?.removeEventListener('abort', onAbort)
      callback()
    }
    const onAbort = () => child.kill('SIGTERM')
    options.signal?.addEventListener('abort', onAbort, { once: true })

    child.once('error', error => finish(() => reject(error)))
    child.stdout.on('data', chunk => {
      stdoutBytes += chunk.length
      if (stdoutBytes > MAX_OUTPUT_BYTES) {
        outputOverflow = true
        child.kill('SIGTERM')
        return
      }
      stdout.push(chunk)
    })
    child.stderr.on('data', chunk => {
      stderrBytes += chunk.length
      if (stderrBytes <= MAX_OUTPUT_BYTES) stderr.push(chunk)
    })
    child.once('close', (code, terminationSignal) => finish(() => {
      if (options.signal?.aborted) {
        reject(abortError())
        return
      }
      if (outputOverflow) {
        reject(new Error(`doctor output exceeded ${MAX_OUTPUT_BYTES} bytes`))
        return
      }

      const output = Buffer.concat(stdout).toString('utf8')
      const errorOutput = Buffer.concat(stderr).toString('utf8').trim()
      // Exit 1 is a successful diagnostic run with one or more findings.
      if (code !== 0 && code !== 1) {
        const status = terminationSignal ? `signal ${terminationSignal}` : `exit ${code}`
        reject(new Error(`doctor failed (${status}): ${errorOutput || 'no error output'}`))
        return
      }
      try {
        resolve(JSON.parse(output))
      } catch (error) {
        reject(new Error(`doctor returned invalid JSON: ${error.message}`))
      }
    }))

    child.stdin.on('error', error => {
      if (error.code !== 'EPIPE') finish(() => reject(error))
    })
    child.stdin.end(input)
  })
}

function abortError() {
  const error = new Error('DeepSeek Protocol Doctor execution was aborted')
  error.name = 'AbortError'
  return error
}
