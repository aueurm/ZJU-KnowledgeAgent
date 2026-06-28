<template>
  <div class="app-container">
    <header class="app-header">
      <h1>学科知识整合智能体</h1>
    </header>

    <div class="app-main">
      <!-- 左侧：教材管理 -->
      <aside class="sidebar-left">
        <UploadZone @uploaded="onUploaded" @error="loadTextbooks" />
        <TextbookList
          :textbooks="textbooks"
          :selectedId="selectedTextbook"
          @select="selectTextbook"
        />
      </aside>

      <!-- 中间：知识图谱 -->
      <main class="graph-area">
        <GraphCanvas
          :graphData="currentGraph"
          :loading="graphLoading"
          :error="graphError"
          @nodeClick="onNodeClick"
        />
      </main>

      <!-- 右侧：功能面板 -->
      <aside class="sidebar-right">
        <div class="tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="panel-content">
          <MergePanel v-if="activeTab === 'merge'" @merged="showMergedGraph" />
          <RAGPanel v-if="activeTab === 'rag'" />
          <ChatPanel v-if="activeTab === 'chat'" />
          <ReportPanel v-if="activeTab === 'report'" />
        </div>
      </aside>
    </div>

    <!-- 节点详情弹窗 -->
    <NodeDetail
      v-if="selectedNode"
      :node="selectedNode"
      @close="selectedNode = null"
    />
  </div>
</template>

<script>
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { getTextbookList, getGraph, getMergedGraph } from './api'

// 导入组件
import UploadZone from './components/UploadZone.vue'
import TextbookList from './components/TextbookList.vue'
import GraphCanvas from './components/GraphCanvas.vue'
import NodeDetail from './components/NodeDetail.vue'
import MergePanel from './components/MergePanel.vue'
import RAGPanel from './components/RAGPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import ReportPanel from './components/ReportPanel.vue'

export default {
  name: 'App',
  components: {
    UploadZone,
    TextbookList,
    GraphCanvas,
    NodeDetail,
    MergePanel,
    RAGPanel,
    ChatPanel,
    ReportPanel
  },
  setup() {
    // 状态
    const textbooks = ref([])
    const selectedTextbook = ref(null)
    const currentGraph = ref({ nodes: [], edges: [] })
    const selectedNode = ref(null)
    const activeTab = ref('merge')
    const graphLoading = ref(false)
    const graphError = ref('')
    let listTimer = null
    let listLoading = false
    let graphRequestSeq = 0

    // Tab配置
    const tabs = [
      { key: 'merge', label: '整合操作' },
      { key: 'rag', label: 'RAG问答' },
      { key: 'chat', label: '对话交互' },
      { key: 'report', label: '整合报告' }
    ]

    // 加载教材列表
    const loadTextbooks = async () => {
      if (listLoading) return
      listLoading = true
      try {
        const res = await getTextbookList()
        textbooks.value = res.data.textbooks || []
      } catch (err) {
        console.error('加载教材失败', err)
      } finally {
        listLoading = false
      }
    }

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

    const fetchGraphWithRetry = async (textbookId, attempts = 4) => {
      for (let attempt = 0; attempt < attempts; attempt++) {
        const res = await getGraph(textbookId)
        const graph = res.data || { nodes: [], edges: [] }
        if (graph.nodes?.length || attempt === attempts - 1) {
          return graph
        }
        await sleep(350)
      }
      return { nodes: [], edges: [] }
    }

    // 选择教材
    const selectTextbook = async (textbookId) => {
      const requestId = ++graphRequestSeq
      selectedTextbook.value = textbookId
      graphLoading.value = true
      graphError.value = ''
      currentGraph.value = { nodes: [], edges: [] }
      try {
        const book = textbooks.value.find(item => item.textbook_id === textbookId)
        if (book?.status === 'parsing') {
          graphError.value = `教材仍在解析中：${book.current_step || `${book.progress || 0}%`}`
          return
        }
        if (book?.status === 'failed') {
          graphError.value = book.error || '教材解析失败，请重新上传或检查文件内容'
          return
        }

        const graph = await fetchGraphWithRetry(textbookId)
        if (requestId !== graphRequestSeq) return
        currentGraph.value = graph
        if (!graph.nodes?.length) {
          graphError.value = '该教材已完成解析，但暂未生成图谱数据。请查看左侧是否有解析警告。'
        }
      } catch (err) {
        if (requestId !== graphRequestSeq) return
        graphError.value = err.response?.data?.detail || err.message || '图谱加载失败'
        console.error('加载图谱失败', err)
      } finally {
        if (requestId === graphRequestSeq) {
          graphLoading.value = false
        }
      }
    }

    // 上传成功回调
    const onUploaded = () => {
      loadTextbooks()
    }

    // 节点点击回调
    const onNodeClick = (node) => {
      selectedNode.value = node
    }

    const showMergedGraph = async () => {
      const requestId = ++graphRequestSeq
      graphLoading.value = true
      graphError.value = ''
      try {
        const res = await getMergedGraph()
        const graph = res.data || { nodes: [], edges: [] }
        if (requestId !== graphRequestSeq) return
        currentGraph.value = graph
        selectedTextbook.value = 'merged'
        if (!graph.nodes?.length) {
          graphError.value = '暂无整合图谱，请先完成跨教材整合。'
        }
      } catch (err) {
        if (requestId !== graphRequestSeq) return
        graphError.value = err.response?.data?.detail || err.message || '整合图谱加载失败'
        console.error('加载整合图谱失败', err)
      } finally {
        if (requestId === graphRequestSeq) {
          graphLoading.value = false
        }
      }
    }

    // 初始化
    onMounted(() => {
      loadTextbooks()
      listTimer = setInterval(loadTextbooks, 1500)
    })

    onBeforeUnmount(() => {
      if (listTimer) clearInterval(listTimer)
    })

    return {
      textbooks,
      selectedTextbook,
      currentGraph,
      selectedNode,
      activeTab,
      graphLoading,
      graphError,
      tabs,
      loadTextbooks,
      selectTextbook,
      onUploaded,
      onNodeClick,
      showMergedGraph
    }
  }
}
</script>

<style>
/* 全局样式 */
* { margin: 0; padding: 0; box-sizing: border-box; }

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-header {
  padding: 16px 24px;
  background: #1890ff;
  color: white;
}

.app-header h1 { font-size: 20px; font-weight: 600; }

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar-left {
  width: 280px;
  border-right: 1px solid #eee;
  overflow-y: auto;
}

.graph-area {
  flex: 1;
  background: #fafafa;
}

.sidebar-right {
  width: 360px;
  border-left: 1px solid #eee;
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  border-bottom: 1px solid #eee;
}

.tabs button {
  flex: 1;
  padding: 12px 8px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 14px;
  color: #666;
}

.tabs button.active {
  color: #1890ff;
  border-bottom: 2px solid #1890ff;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
</style>
