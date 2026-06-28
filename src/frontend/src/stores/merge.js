import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getMergeDecisions,
  mergeTextbooks,
  confirmMerge,
  modifyDecision,
  getMergeStats,
  getMergedGraph
} from '../api'

export const useMergeStore = defineStore('merge', () => {
  const decisions = ref([])
  const stats = ref({
    original_count: 0,
    original_chars: 0,
    compression_ratio: 0,
    original_nodes: 0,
    merged_nodes: 0,
    edge_count: 0
  })
  const status = ref('idle') // idle | loading | done | error
  const error = ref(null)
  const selectedBooks = ref([])

  const decisionsSummary = computed(() => {
    const summary = { merge: 0, keep: 0, remove: 0 }
    decisions.value.forEach(d => {
      if (summary.hasOwnProperty(d.action)) {
        summary[d.action]++
      }
    })
    return summary
  })

  const hasData = computed(() => decisions.value.length > 0)

  function addBook(id) {
    if (!selectedBooks.value.includes(id)) {
      selectedBooks.value.push(id)
    }
  }

  function removeBook(id) {
    selectedBooks.value = selectedBooks.value.filter(b => b !== id)
  }

  async function loadDecisions() {
    status.value = 'loading'
    error.value = null
    try {
      const res = await getMergeDecisions()
      decisions.value = res.data.decisions || []
      status.value = 'done'
    } catch (err) {
      error.value = '加载决策失败'
      status.value = 'error'
      console.error(error.value, err)
    }
  }

  async function executeMerge(textbookIds) {
    status.value = 'loading'
    error.value = null
    try {
      const res = await mergeTextbooks(textbookIds)
      decisions.value = res.data.decisions || []
      status.value = 'done'
      return res.data
    } catch (err) {
      error.value = '整合失败'
      status.value = 'error'
      console.error(error.value, err)
      throw err
    }
  }

  async function executeConfirmMerge() {
    try {
      await confirmMerge()
      decisions.value = []
      selectedBooks.value = []
      status.value = 'idle'
    } catch (err) {
      console.error('确认失败', err)
      throw err
    }
  }

  async function updateDecision(decisionId, newAction) {
    try {
      await modifyDecision(decisionId, newAction)
      await loadDecisions()
    } catch (err) {
      console.error('修改决策失败', err)
      throw err
    }
  }

  async function loadStats() {
    try {
      const res = await getMergeStats()
      const data = res.data || {}
      stats.value = {
        original_count: data.original_count || 0,
        original_chars: data.original_chars || 0,
        compression_ratio: data.compression_ratio || 0,
        original_nodes: data.original_nodes || 0,
        merged_nodes: data.merged_nodes || 0,
        edge_count: data.edge_count || 0
      }
    } catch (err) {
      console.error('加载统计失败', err)
    }
  }

  async function loadReportData() {
    status.value = 'loading'
    error.value = null
    try {
      const [statsRes, decisionsRes, graphRes] = await Promise.all([
        getMergeStats(),
        getMergeDecisions(),
        getMergedGraph()
      ])

      const mergeStats = statsRes.data || {}
      const decisionList = decisionsRes.data?.decisions || []
      const mergedGraph = graphRes.data || { nodes: [], edges: [] }

      const summary = { merge: 0, keep: 0, remove: 0 }
      decisionList.forEach(d => {
        if (summary.hasOwnProperty(d.action)) {
          summary[d.action]++
        }
      })

      stats.value = {
        original_count: mergeStats.original_count || 0,
        original_chars: mergeStats.original_chars || 0,
        compression_ratio: mergeStats.compression_ratio || 0,
        original_nodes: mergeStats.original_nodes || 0,
        merged_nodes: mergeStats.merged_nodes || 0,
        edge_count: mergeStats.edge_count || mergedGraph.edges?.length || 0
      }

      decisions.value = decisionList
      status.value = 'done'
    } catch (err) {
      error.value = '加载报告数据失败'
      status.value = 'error'
      console.error(error.value, err)
    }
  }

  return {
    decisions,
    stats,
    status,
    error,
    selectedBooks,
    decisionsSummary,
    hasData,
    addBook,
    removeBook,
    loadDecisions,
    executeMerge,
    executeConfirmMerge,
    updateDecision,
    loadStats,
    loadReportData
  }
})
