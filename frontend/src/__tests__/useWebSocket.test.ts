import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWebSocket } from '../composables/useWebSocket'

// Mock WebSocket
let mockWebSocket: any

const MockWebSocket = vi.fn(() => mockWebSocket)
MockWebSocket.OPEN = 1
MockWebSocket.CLOSED = 3
vi.stubGlobal('WebSocket', MockWebSocket)

describe('useWebSocket', () => {
  let ws: ReturnType<typeof useWebSocket>

  beforeEach(() => {
    vi.clearAllMocks()
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: 1,
      onmessage: null,
      onclose: null,
      onerror: null,
      onopen: null
    }
  })

  it('initializes with disconnected state', () => {
    ws = useWebSocket('ws://localhost:8080')
    expect(ws.isConnected.value).toBe(false)
  })

  it('connects to websocket server', () => {
    ws = useWebSocket('ws://localhost:8080')
    ws.connect('session123')

    expect(WebSocket).toHaveBeenCalledWith('ws://localhost:8080?session_id=session123')
  })

  it('sends query message', () => {
    ws = useWebSocket('ws://localhost:8080')
    ws.connect('session123')

    ws.sendQuery('测试问题', 'msg1')

    expect(mockWebSocket.send).toHaveBeenCalledWith(JSON.stringify({
      type: 'query',
      query: '测试问题',
      message_id: 'msg1'
    }))
  })

  it('handles incoming token messages', () => {
    const onToken = vi.fn()
    ws = useWebSocket('ws://localhost:8080')
    ws.onToken = onToken
    ws.connect('session123')

    const event = {
      data: JSON.stringify({
        type: 'token',
        message_id: 'msg1',
        token: '你好'
      })
    }
    mockWebSocket.onmessage(event)

    expect(onToken).toHaveBeenCalledWith('msg1', '你好')
  })

  it('handles incoming sources messages', () => {
    const onSources = vi.fn()
    ws = useWebSocket('ws://localhost:8080')
    ws.onSources = onSources
    ws.connect('session123')

    const sources = [{ file: 'test.md', section: 'test', content_type: 'text', chunk: 'test', score: 0.9 }]
    const event = {
      data: JSON.stringify({
        type: 'sources',
        message_id: 'msg1',
        sources
      })
    }
    mockWebSocket.onmessage(event)

    expect(onSources).toHaveBeenCalledWith('msg1', sources)
  })

  it('handles done messages', () => {
    const onDone = vi.fn()
    ws = useWebSocket('ws://localhost:8080')
    ws.onDone = onDone
    ws.connect('session123')

    const event = {
      data: JSON.stringify({
        type: 'done',
        message_id: 'msg1',
        timing: { retrieval_ms: 100, generation_ms: 200, total_ms: 300 }
      })
    }
    mockWebSocket.onmessage(event)

    expect(onDone).toHaveBeenCalledWith('msg1', { retrieval_ms: 100, generation_ms: 200, total_ms: 300 })
  })

  it('handles error messages', () => {
    const onError = vi.fn()
    ws = useWebSocket('ws://localhost:8080')
    ws.onError = onError
    ws.connect('session123')

    const event = {
      data: JSON.stringify({
        type: 'error',
        message: '发生错误'
      })
    }
    mockWebSocket.onmessage(event)

    expect(onError).toHaveBeenCalledWith('发生错误')
  })

  it('disconnects from server', () => {
    ws = useWebSocket('ws://localhost:8080')
    ws.connect('session123')
    ws.disconnect()

    expect(mockWebSocket.close).toHaveBeenCalled()
  })
})
