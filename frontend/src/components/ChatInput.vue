<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'send', message: string): void
}>()

const inputText = ref('')

function handleSend(): void {
  if (inputText.value.trim() && !props.loading) {
    emit('send', inputText.value.trim())
    inputText.value = ''
  }
}

function handleKeyup(e: KeyboardEvent): void {
  if (e.key === 'Enter' && !e.shiftKey) {
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input">
    <input
      v-model="inputText"
      type="text"
      placeholder="输入问题..."
      :disabled="loading"
      @keyup="handleKeyup"
    />
    <button :disabled="loading || !inputText.trim()" @click="handleSend">
      {{ loading ? '发送中...' : '发送' }}
    </button>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
}

input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

input:focus {
  border-color: var(--el-color-primary);
}

button {
  padding: 12px 24px;
  background: var(--el-color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: opacity 0.2s;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
