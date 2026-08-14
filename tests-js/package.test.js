import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const rootFile = name => new URL(`../${name}`, import.meta.url)

test('package advertises a source-installable DSH bundle', async () => {
  const manifest = JSON.parse(await readFile(rootFile('package.json'), 'utf8'))
  const patch = await readFile(rootFile('cordis.patch.yml'), 'utf8')
  const entrypoint = await readFile(rootFile('index.js'), 'utf8')
  const skill = await readFile(rootFile('skills/deepseek-protocol-doctor/SKILL.md'), 'utf8')

  assert.equal(manifest.dsh.bundle.patch, './cordis.patch.yml')
  assert.equal(manifest.main, './index.js')
  assert.ok(manifest.files.includes('COMPATIBILITY.md'))
  assert.equal(manifest.scripts.prepare, undefined)
  assert.match(patch, /name: dsh-deepseek-protocol-doctor/)
  assert.match(entrypoint, /ctx\.tools\.register/)
  assert.match(skill, new RegExp(`@v${manifest.version.replaceAll('.', '\\.')}`))
})
