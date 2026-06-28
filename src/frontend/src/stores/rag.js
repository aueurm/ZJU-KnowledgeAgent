import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { ragQuery, buildRagIndex, getRagStatus } from '../api'

export const useRagStore = defineStore('rag', () => {
  const status = reactive({ indexed_textbooks: 0, total_chunks: 0, status: 'ready' })
  const queryHistory = ref([])
  const messages = ref([])
  const currentResult = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function sendQuery(question) {
    if (!question.trim()) return

    loading.value = true
    error.value = null
    messages.value.push({ role: 'user', content: question })

    try {
      const res = await ragQuery(question)
      const data = res.data
      currentResult.value = data
      messages.value.push({
        role: 'assistant',
        content: data.answer,
        citations: data.citations
      })
      queryHistory.value.push({
        question,
        answer: data.answer,
        timestamp: Date.now()
      })
      return data
    } catch (err) {
      error.value = err.message
      messages.value.push({
        role: 'assistant',
        content: '抱歉，查询失败：' + err.message
      })
      throw err
    } finally {
      loading.value = false
    }
  }

  async function buildIndex(textbookId) {
    status.status = 'indexing'
    try {
      await buildRagIndex(textbookId)
      await loadStatus()
    } catch (err) {
      console.error('索引构建失败', err)
    } finally {
      status.status = 'ready'
    }
  }

  async function loadStatus() {
    try {
      const res = await getRagStatus()
      Object.assign(status, res.data)
    } catch (err) {
      console.error('获取状态失败', err)
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return {
    status,
    queryHistory,
    messages,
    currentResult,
    loading,
    error,
    sendQuery,
    buildIndex,
    loadStatus,
    clearMessages
  }
})
