import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getTextbookList, getGraph } from '../api'

export const useTextbookStore = defineStore('textbook', () => {
  const textbooks = ref([])
  const selectedId = ref(null)
  const currentGraph = ref({ nodes: [], edges: [] })
  const loading = ref(false)
  const error = ref(null)

  const processingStatus = computed(() => {
    const total = textbooks.value.length
    const parsing = textbooks.value.filter(b => b.status === 'parsing').length
    const parsed = textbooks.value.filter(b => b.status === 'parsed').length
    const failed = textbooks.value.filter(b => b.status === 'failed').length
    return { total, parsing, parsed, failed }
  })

  const selectedTextbook = computed(() =>
    textbooks.value.find(b => b.textbook_id === selectedId.value) || null
  )

  async function loadTextbooks() {
    loading.value = true
    error.value = null
    try {
      const res = await getTextbookList()
      textbooks.value = res.data.textbooks || []
    } catch (err) {
      error.value = '加载教材失败'
      console.error(error.value, err)
    } finally {
      loading.value = false
    }
  }

  async function selectTextbook(textbookId) {
    selectedId.value = textbookId
    loading.value = true
    error.value = null
    try {
      const res = await getGraph(textbookId)
      currentGraph.value = res.data
    } catch (err) {
      error.value = '加载图谱失败'
      console.error(error.value, err)
    } finally {
      loading.value = false
    }
  }

  return {
    textbooks,
    selectedId,
    currentGraph,
    loading,
    error,
    processingStatus,
    selectedTextbook,
    loadTextbooks,
    selectTextbook
  }
})