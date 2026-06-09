import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useChat } from '../composables/useChat'

// Mock WebSocket
const mockWebSocket = {
  send: vi.fn(),
  close: vi.fn(),
  readyState: 1,
  onmessage: null,
  onclose: null,
  onerror: null,
  onopen: null
}

vi.stubGlobal('WebSocket', vi.fn(() => mockWebSocket))

describe('useChat', () => {
  let chat: ReturnType<typeof useChat>

  beforeEach(() => {
    vi.clearAllMocks()
    chat = useChat()
  })

  it('initializes with empty messages', () => {
    expect(chat.messages.value).toEqual([])
    expect(chat.isLoading.value).toBe(false)
    expect(chat.error.value).toBeNull()
  })

  it('adds user message when sending', () => {
    chat.sendMessage('测试问题')
    expect(chat.messages.value.length).toBe(1)
    expect(chat.messages.value[0].role).toBe('user')
    expect(chat.messages.value[0].content).toBe('测试问题')
  })

  it('sets loading state when sending', () => {
    chat.sendMessage('测试问题')
    expect(chat.isLoading.value).toBe(true)
  })

  it('generates unique message ids', () => {
    chat.sendMessage('消息1')
    chat.sendMessage('消息2')
    expect(chat.messages.value[0].id).not.toBe(chat.messages.value[1].id)
  })

  it('clears messages', () => {
    chat.sendMessage('测试问题')
    chat.clearMessages()
    expect(chat.messages.value).toEqual([])
  })

  it('handles token message', () => {
    chat.sendMessage('测试问题')
    const assistantMessage = chat.addAssistantMessage()

    // Simulate token message via handleToken
    chat.handleToken(assistantMessage.id, '测试回答')

    expect(assistantMessage.content).toBe('测试回答')
  })
})
