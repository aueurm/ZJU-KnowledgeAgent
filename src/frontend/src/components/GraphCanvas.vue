<template>
  <div class="graph-canvas" ref="container">
    <div v-if="hasData" class="graph-toolbar">
      <button v-if="activeModule" @click.stop="backToModules">返回模块</button>
      <span>{{ activeModule || '模块概览' }}</span>
    </div>
    <div v-if="loading" class="graph-overlay">
      正在加载图谱...
    </div>
    <div v-else-if="error" class="graph-overlay error">
      {{ error }}
    </div>
    <div v-else-if="!hasData" class="graph-overlay">
      请选择教材查看知识图谱
    </div>
    <div v-if="notice" class="graph-notice">
      {{ notice }}
    </div>
  </div>
</template>

<script>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import G6 from '@antv/g6'

const MAX_RENDER_NODES = 300
const LABEL_MAX_LENGTH = 10

export default {
  name: 'GraphCanvas',
  props: {
    graphData: { type: Object, default: () => ({ nodes: [], edges: [] }) },
    loading: { type: Boolean, default: false },
    error: { type: String, default: '' }
  },
  emits: ['nodeClick'],
  setup(props, { emit }) {
    const container = ref(null)
    let graph = null
    let frame = null
    let rendered = false

    const hasData = ref(false)
    const notice = ref('')
    const activeModule = ref('')

    const shortLabel = (value) => {
      const label = String(value || '')
      return label.length > LABEL_MAX_LENGTH
        ? `${label.slice(0, LABEL_MAX_LENGTH - 2)}...`
        : label
    }

    // 初始化图谱
    const initGraph = () => {
      if (!container.value) return

      graph = new G6.Graph({
        container: container.value,
        width: container.value.clientWidth,
        height: container.value.clientHeight,
        // 配置布局
        layout: { type: 'preset' },
        // 节点配置
        defaultNode: {
          size: 32,
          style: {
            fill: '#1890ff',
            stroke: '#ffffff',
            lineWidth: 2,
            cursor: 'pointer'
          },
          labelCfg: {
            position: 'bottom',
            offset: 6,
            style: {
              fill: '#333',
              fontSize: 11,
              textAlign: 'center',
              textBaseline: 'top'
            }
          }
        },
        // 边配置
        defaultEdge: {
          style: {
            stroke: '#e0e0e0',
            lineWidth: 1
          }
        },
        // 交互行为
        modes: {
          default: ['drag-canvas', 'zoom-canvas', 'drag-node']
        }
      })

      // 节点点击事件
      graph.on('node:click', (e) => {
        const node = e.item.getModel()
        if (node.isModule) {
          activeModule.value = node.moduleName
          scheduleUpdate()
          return
        }
        if (node.isHub) return
        emit('nodeClick', node)
      })
    }

    // 更新图谱数据
    const updateGraph = () => {
      if (!graph) return

      const nodes = props.graphData?.nodes || []
      const edges = props.graphData?.edges || []
      hasData.value = nodes.length > 0
      notice.value = nodes.length > MAX_RENDER_NODES
        ? `图谱较大，已优先显示前 ${MAX_RENDER_NODES} 个节点`
        : ''

      if (!nodes.length) {
        renderData({ nodes: [], edges: [] })
        return
      }

      const modules = buildModules(nodes)
      const renderGraph = activeModule.value
        ? buildModuleGraph(activeModule.value, modules, edges)
        : buildOverviewGraph(modules, edges)

      const visibleNodes = renderGraph.nodes.slice(0, MAX_RENDER_NODES)
      const visibleIds = new Set(visibleNodes.map(n => n.id))
      const colors = ['#1890ff', '#52c41a', '#fa8c16', '#f5222d', '#722ed1', '#13c2c2']
      const sourceColors = {}
      let nextColor = 0
      const nodeData = positionNodes(visibleNodes.map(n => {
        const source = n.moduleName || n.source || 'default'
        if (!sourceColors[source]) {
          sourceColors[source] = colors[nextColor % colors.length]
          nextColor++
        }
        return {
          ...n,
          label: shortLabel(n.name),
          size: n.isModule
            ? Math.min(72, 38 + Math.sqrt(n.count || 1) * 7)
            : Math.min(48, 30 + (n.freq || 1) * 4),
          style: {
            fill: n.isHub ? '#13c2c2' : sourceColors[source]
          }
        }
      }))

      const edgeData = renderGraph.edges
        .filter(e => visibleIds.has(e.source) && visibleIds.has(e.target))
        .map((e, index) => ({
          id: e.id || `edge_${index}`,
          source: e.source,
          target: e.target,
          relationType: e.relation_type
        }))

      renderData({ nodes: nodeData, edges: edgeData })
      graph.fitView(32)
    }

    const buildModules = (nodes) => {
      const fields = ['module', 'chapter', 'category']
      let field = fields.find(name => new Set(nodes.map(n => cleanModule(n[name]))).size > 1) || 'chapter'
      const modules = {}
      nodes.forEach(node => {
        const name = cleanModule(node[field])
        if (!modules[name]) modules[name] = []
        modules[name].push(node)
      })
      return modules
    }

    const cleanModule = (value) => String(value || '未分组').replace(/\s+/g, ' ').trim() || '未分组'

    const buildOverviewGraph = (modules, edges) => {
      const moduleByNode = {}
      Object.entries(modules).forEach(([name, list]) => {
        list.forEach(node => { moduleByNode[node.id] = name })
      })
      const moduleNodes = Object.entries(modules).map(([name, list]) => ({
        id: `module_${name}`,
        name,
        moduleName: name,
        isModule: true,
        count: list.length,
        category: '模块',
        definition: `包含 ${list.length} 个知识点`,
        page: Math.min(...list.map(n => Number(n.page) || 1))
      }))
      const seen = new Set()
      const moduleEdges = []
      edges.forEach(edge => {
        const source = moduleByNode[edge.source]
        const target = moduleByNode[edge.target]
        if (!source || !target || source === target) return
        const key = [source, target].sort().join('->')
        if (seen.has(key)) return
        seen.add(key)
        moduleEdges.push({
          source: `module_${source}`,
          target: `module_${target}`,
          relation_type: 'related'
        })
      })
      notice.value = `${moduleNodes.length} 个模块，点击模块查看内部图谱`
      return { nodes: moduleNodes, edges: moduleEdges }
    }

    const buildModuleGraph = (moduleName, modules, edges) => {
      const nodes = modules[moduleName] || []
      const nodeIds = new Set(nodes.map(n => n.id))
      const hubId = `hub_${moduleName}`
      const hub = {
        id: hubId,
        name: moduleName,
        moduleName,
        isHub: true,
        category: '模块',
        definition: `包含 ${nodes.length} 个知识点`,
        page: Math.min(...nodes.map(n => Number(n.page) || 1))
      }
      const hubEdges = nodes.map(node => ({
        source: hubId,
        target: node.id,
        relation_type: 'contains'
      }))
      const innerEdges = edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
      notice.value = `${moduleName}：${nodes.length} 个知识点`
      return { nodes: [hub, ...nodes], edges: [...hubEdges, ...innerEdges] }
    }

    const renderData = (data) => {
      if (rendered) {
        graph.changeData(data)
      } else {
        graph.data(data)
        graph.render()
        rendered = true
      }
    }

    const scheduleUpdate = () => {
      if (frame) cancelAnimationFrame(frame)
      frame = requestAnimationFrame(updateGraph)
    }

    const backToModules = () => {
      activeModule.value = ''
      scheduleUpdate()
    }

    const positionNodes = (nodes) => {
      const count = nodes.length
      if (!count) return nodes

      const width = Math.max(container.value?.clientWidth || 900, 600)
      const height = Math.max(container.value?.clientHeight || 600, 420)
      const cols = Math.max(1, Math.ceil(Math.sqrt(count * width / height)))
      const cellW = count > 120 ? 96 : 116
      const cellH = count > 120 ? 76 : 88
      const rows = Math.ceil(count / cols)
      const totalW = (Math.min(cols, count) - 1) * cellW
      const totalH = (rows - 1) * cellH

      return nodes.map((node, index) => ({
        ...node,
        x: (index % cols) * cellW - totalW / 2,
        y: Math.floor(index / cols) * cellH - totalH / 2
      }))
    }

    // 窗口大小变化
    const handleResize = () => {
      if (graph && container.value) {
        graph.changeSize(container.value.clientWidth, container.value.clientHeight)
        scheduleUpdate()
      }
    }

    // 监听数据变化
    watch(() => props.graphData, () => {
      activeModule.value = ''
      scheduleUpdate()
    })

    onMounted(() => {
      initGraph()
      updateGraph()
      window.addEventListener('resize', handleResize)
    })

    onUnmounted(() => {
      if (frame) cancelAnimationFrame(frame)
      if (graph) graph.destroy()
      window.removeEventListener('resize', handleResize)
    })

    return { container, hasData, notice, activeModule, backToModules }
  }
}
</script>

<style scoped>
.graph-canvas {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.graph-overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.86);
  color: #999;
  font-size: 16px;
}

.graph-overlay.error {
  color: #ff4d4f;
  padding: 24px;
  text-align: center;
}

.graph-toolbar {
  position: absolute;
  left: 16px;
  top: 16px;
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.94);
  color: #333;
  font-size: 13px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

.graph-toolbar button {
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  background: white;
  color: #1890ff;
  cursor: pointer;
  font-size: 12px;
  padding: 3px 8px;
}

.graph-notice {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 3;
  padding: 6px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.92);
  color: #666;
  font-size: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}
</style>
