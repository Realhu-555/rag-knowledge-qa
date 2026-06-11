<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChat } from './composables/useChat'
import { useWebSocket } from './composables/useWebSocket'
import ChatMessage from './components/ChatMessage.vue'
import ChatInput from './components/ChatInput.vue'

const { messages, isLoading, error, sessionId, sendMessage, addAssistantMessage, handleToken, setMessageDone, setError } = useChat()

const WS_URL = ref('ws://localhost:8080/ws')
const ws = useWebSocket(WS_URL.value)

ws.connect(sessionId.value)

const pendingSources = ref<Record<string, any[]>>({})
const pendingTiming = ref<Record<string, any>>({})

ws.onToken = (messageId: string, token: string) => {
  handleToken(messageId, token)
}

ws.onSources = (messageId: string, sources: any[]) => {
  pendingSources.value[messageId] = sources
}

ws.onDone = (messageId: string, timing: any) => {
  const sources = pendingSources.value[messageId]
  setMessageDone(messageId, sources, timing)
  delete pendingSources.value[messageId]
}

ws.onError = (msg: string) => {
  setError(msg)
}

const chatContainer = ref<HTMLElement>()

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

watch(messages, scrollToBottom, { deep: true })

function handleSend(content: string) {
  sendMessage(content)
  const assistantMsg = addAssistantMessage()
  ws.sendQuery(content, assistantMsg.id)
}
</script>

<template>
  <div class="app">
    <header class="header">
      <h1>RAG 智能问答</h1>
      <div class="status" :class="{ connected: ws.isConnected.value }">
        {{ ws.isConnected.value ? '已连接' : '未连接' }}
      </div>
    </header>

    <main class="chat-container" ref="chatContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="icon">🤖</div>
        <p>有什么问题？问我吧！</p>
      </div>

      <ChatMessage
        v-for="msg in messages"
        :key="msg.id"
        :message="msg"
      />

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </main>

    <ChatInput :loading="isLoading" @send="handleSend" />
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--el-bg-color-page);
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
  background: var(--el-bg-color);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.header h1 {
  font-size: 20px;
  font-weight: 600;
}

.status {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 12px;
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
}

.status.connected {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}

.chat-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
}

.empty-state .icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.error-message {
  padding: 12px 16px;
  margin: 8px 0;
  background: var(--el-color-danger-light-9);
  color: var(--el-color-danger);
  border-radius: 8px;
}
</style>
