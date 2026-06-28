import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendChat, getChatHistory } from '../api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const sessionId = ref('default')
  const sending = ref(false)
  const error = ref(null)

  async function sendMessage(message) {
    if (!message.trim()) return

    sending.value = true
    error.value = null
    const trimmed = message.trim()

    try {
      const res = await sendChat(trimmed, sessionId.value)
      const data = res.data
      messages.value.push(
        { role: 'user', content: trimmed },
        {
          role: 'assistant',
          content: data.reply + (data.action_taken ? `\n[操作: ${data.action_taken}]` : '')
        }
      )
      return data
    } catch (err) {
      error.value = err.message
      messages.value.push({
        role: 'assistant',
        content: '抱歉，发送失败：' + err.message
      })
      throw err
    } finally {
      sending.value = false
    }
  }

  async function loadHistory() {
    try {
      const res = await getChatHistory(sessionId.value)
      messages.value = res.data.messages || []
    } catch (err) {
      console.error('加载历史失败', err)
    }
  }

  function setSessionId(id) {
    sessionId.value = id
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    messages,
    sessionId,
    sending,
    error,
    sendMessage,
    loadHistory,
    setSessionId,
    clearMessages
  }
})
