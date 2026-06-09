import { describe, it, expect } from 'vitest'
import type { Message, Source, Timing, Usage, QueryResponse, WSMessage } from '../types'

describe('TypeScript Types', () => {
  it('Message interface has correct structure', () => {
    const message: Message = {
      id: '1',
      role: 'user',
      content: '测试消息'
    }
    expect(message.id).toBe('1')
    expect(message.role).toBe('user')
    expect(message.content).toBe('测试消息')
  })

  it('Source interface has correct structure', () => {
    const source: Source = {
      file: 'test.md',
      section: '测试章节',
      content_type: 'text',
      chunk: '测试内容',
      score: 0.95
    }
    expect(source.file).toBe('test.md')
    expect(source.score).toBe(0.95)
  })

  it('Timing interface has correct structure', () => {
    const timing: Timing = {
      retrieval_ms: 100,
      generation_ms: 500,
      total_ms: 600
    }
    expect(timing.total_ms).toBe(600)
  })

  it('Usage interface has correct structure', () => {
    const usage: Usage = {
      prompt_tokens: 100,
      completion_tokens: 50,
      total_tokens: 150
    }
    expect(usage.total_tokens).toBe(150)
  })

  it('QueryResponse interface has correct structure', () => {
    const response: QueryResponse = {
      request_id: 'req_123',
      answer: '测试回答',
      sources: [],
      usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      timing: { retrieval_ms: 0, generation_ms: 0, total_ms: 0 }
    }
    expect(response.request_id).toBe('req_123')
  })

  it('WSMessage union type works correctly', () => {
    const tokenMsg: WSMessage = { type: 'token', content: '你好' }
    const sourcesMsg: WSMessage = { type: 'sources', sources: [] }
    const doneMsg: WSMessage = { type: 'done', usage: {} as Usage, timing: {} as Timing }
    const errorMsg: WSMessage = { type: 'error', message: '错误' }

    expect(tokenMsg.type).toBe('token')
    expect(sourcesMsg.type).toBe('sources')
    expect(doneMsg.type).toBe('done')
    expect(errorMsg.type).toBe('error')
  })
})
