import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getGraph, getMergedGraph } from '../api'

export const useGraphStore = defineStore('graph', () => {
  const nodes = ref([])
  const edges = ref([])
  const selectedNode = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const hasData = computed(() => nodes.value.length > 0)

  async function loadGraph(textbookId) {
    loading.value = true
    error.value = null
    try {
      const res = await getGraph(textbookId)
      nodes.value = res.data.nodes || []
      edges.value = res.data.edges || []
    } catch (err) {
      error.value = '加载图谱失败'
      console.error(error.value, err)
    } finally {
      loading.value = false
    }
  }

  async function loadMergedGraph() {
    loading.value = true
    error.value = null
    try {
      const res = await getMergedGraph()
      nodes.value = res.data.nodes || []
      edges.value = res.data.edges || []
    } catch (err) {
      error.value = '加载整合图谱失败'
      console.error(error.value, err)
    } finally {
      loading.value = false
    }
  }

  function selectNode(node) {
    selectedNode.value = node
  }

  function clearSelection() {
    selectedNode.value = null
  }

  return {
    nodes,
    edges,
    selectedNode,
    loading,
    error,
    hasData,
    loadGraph,
    loadMergedGraph,
    selectNode,
    clearSelection
  }
})
