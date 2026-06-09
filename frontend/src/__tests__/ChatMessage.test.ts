import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '../components/ChatMessage.vue'
import type { Message } from '../types'

describe('ChatMessage', () => {
  const userMessage: Message = {
    id: '1',
    role: 'user',
    content: '什么是RAG？'
  }

  const assistantMessage: Message = {
    id: '2',
    role: 'assistant',
    content: 'RAG是检索增强生成技术[1]',
    sources: [
      { file: 'rag.md', section: '简介', content_type: 'text', chunk: 'RAG是一种...', score: 0.95 }
    ],
    timing: { retrieval_ms: 100, generation_ms: 200, total_ms: 300 }
  }

  it('renders user message', () => {
    const wrapper = mount(ChatMessage, { props: { message: userMessage } })
    expect(wrapper.text()).toContain('什么是RAG？')
    expect(wrapper.classes()).toContain('message-user')
  })

  it('renders assistant message', () => {
    const wrapper = mount(ChatMessage, { props: { message: assistantMessage } })
    expect(wrapper.text()).toContain('RAG是检索增强生成技术')
    expect(wrapper.classes()).toContain('message-assistant')
  })

  it('renders citation references', () => {
    const wrapper = mount(ChatMessage, { props: { message: assistantMessage } })
    expect(wrapper.find('.citation').exists()).toBe(true)
    expect(wrapper.text()).toContain('[1]')
  })

  it('expands sources on message content click', async () => {
    const wrapper = mount(ChatMessage, { props: { message: assistantMessage } })
    const content = wrapper.find('.message-content')
    await content.trigger('click')

    expect(wrapper.find('.sources-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('rag.md')
    expect(wrapper.text()).toContain('RAG是一种...')
  })

  it('shows timing info', async () => {
    const wrapper = mount(ChatMessage, { props: { message: assistantMessage } })
    const content = wrapper.find('.message-content')
    await content.trigger('click')

    expect(wrapper.text()).toContain('300ms')
  })

  it('shows loading indicator for empty assistant', () => {
    const loadingMessage: Message = { id: '3', role: 'assistant', content: '' }
    const wrapper = mount(ChatMessage, { props: { message: loadingMessage } })
    expect(wrapper.find('.loading').exists()).toBe(true)
  })
})
