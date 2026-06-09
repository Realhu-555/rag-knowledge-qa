import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatInput from '../components/ChatInput.vue'

describe('ChatInput', () => {
  it('renders input field', () => {
    const wrapper = mount(ChatInput)
    expect(wrapper.find('input').exists()).toBe(true)
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('emits send event on button click', async () => {
    const wrapper = mount(ChatInput)
    const input = wrapper.find('input')

    await input.setValue('测试问题')
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('send')).toBeTruthy()
    expect(wrapper.emitted('send')![0]).toEqual(['测试问题'])
  })

  it('emits send event on enter key', async () => {
    const wrapper = mount(ChatInput)
    const input = wrapper.find('input')

    await input.setValue('测试问题')
    await input.trigger('keyup', { key: 'Enter' })

    expect(wrapper.emitted('send')).toBeTruthy()
  })

  it('clears input after sending', async () => {
    const wrapper = mount(ChatInput)
    const input = wrapper.find('input')

    await input.setValue('测试问题')
    await wrapper.find('button').trigger('click')

    expect((input.element as HTMLInputElement).value).toBe('')
  })

  it('does not send empty message', async () => {
    const wrapper = mount(ChatInput)
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('send')).toBeFalsy()
  })

  it('disables input when loading', () => {
    const wrapper = mount(ChatInput, { props: { loading: true } })
    const input = wrapper.find('input')
    const button = wrapper.find('button')

    expect((input.element as HTMLInputElement).disabled).toBe(true)
    expect((button.element as HTMLButtonElement).disabled).toBe(true)
  })
})
