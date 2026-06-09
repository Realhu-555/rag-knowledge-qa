import { ref } from 'vue'
import type { Source, Timing } from '../types'

/**
 * WebSocket消息处理器
 */
export function useWebSocket(baseUrl: string) {
  const isConnected = ref(false)
  let ws: WebSocket | null = null

  // 回调函数
  let onToken: ((messageId: string, token: string) => void) | null = null
  let onSources: ((messageId: string, sources: Source[]) => void) | null = null
  let onDone: ((messageId: string, timing: Timing) => void) | null = null
  let onError: ((message: string) => void) | null = null

  /**
   * 连接到WebSocket服务器
   */
  function connect(sessionId: string): void {
    ws = new WebSocket(`${baseUrl}?session_id=${sessionId}`)

    ws.onopen = () => {
      isConnected.value = true
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleMessage(data)
    }

    ws.onclose = () => {
      isConnected.value = false
    }

    ws.onerror = () => {
      isConnected.value = false
      onError?.call(null, 'WebSocket连接错误')
    }
  }

  /**
   * 处理收到的消息
   */
  function handleMessage(data: any): void {
    switch (data.type) {
      case 'token':
        onToken?.call(null, data.message_id, data.token)
        break
      case 'sources':
        onSources?.call(null, data.message_id, data.sources)
        break
      case 'done':
        onDone?.call(null, data.message_id, data.timing)
        break
      case 'error':
        onError?.call(null, data.message)
        break
    }
  }

  /**
   * 发送查询消息
   */
  function sendQuery(query: string, messageId: string): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'query',
        query,
        message_id: messageId
      }))
    }
  }

  /**
   * 断开连接
   */
  function disconnect(): void {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return {
    isConnected,
    connect,
    disconnect,
    sendQuery,
    get onToken() { return onToken },
    set onToken(fn) { onToken = fn },
    get onSources() { return onSources },
    set onSources(fn) { onSources = fn },
    get onDone() { return onDone },
    set onDone(fn) { onDone = fn },
    get onError() { return onError },
    set onError(fn) { onError = fn }
  }
}
