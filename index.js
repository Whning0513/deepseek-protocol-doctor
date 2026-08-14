import { defineTool } from '@deepseek-ai/dsh-tools'

import { createToolDefinitions } from './dsh/tools.js'

export const name = 'dsh-deepseek-protocol-doctor'
export const inject = ['tools']

export function apply(ctx) {
  for (const definition of createToolDefinitions(defineTool)) {
    ctx.tools.register(definition)
  }
}
