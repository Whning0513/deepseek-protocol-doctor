import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const rootFile = name => new URL(`../${name}`, import.meta.url)

test('package advertises a source-installable DSH bundle', async () => {
  const manifest = JSON.parse(await readFile(rootFile('package.json'), 'utf8'))
  const patch = await readFile(rootFile('cordis.patch.yml'), 'utf8')
  const entrypoint = await readFile(rootFile('index.js'), 'utf8')

  assert.equal(manifest.dsh.bundle.patch, './cordis.patch.yml')
  assert.equal(manifest.main, './index.js')
  assert.equal(manifest.scripts.prepare, undefined)
  assert.match(patch, /name: dsh-deepseek-protocol-doctor/)
  assert.match(entrypoint, /ctx\.tools\.register/)
})
