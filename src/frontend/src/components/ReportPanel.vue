<template>
  <div class="report-panel">
    <h4>整合报告</h4>

    <div v-if="loading" class="loading">加载中...</div>
    <template v-else>

    <div class="stats">
      <div class="stat-item">
        <div class="label">原始教材</div>
        <div class="value">{{ stats.original_count }} 本</div>
      </div>
      <div class="stat-item">
        <div class="label">原始字数</div>
        <div class="value">{{ stats.original_chars.toLocaleString() }} 字</div>
      </div>
      <div class="stat-item">
        <div class="label">内容保留率</div>
        <div class="value" :class="{ warning: stats.completeness_warning }">
          {{ (stats.compression_ratio * 100).toFixed(1) }}%
        </div>
      </div>
    </div>

    <div class="decisions-summary">
      <h5>决策摘要</h5>
      <div v-if="hasData" class="summary-grid">
        <div class="summary-item merge">合并: {{ decisionsSummary.merge }}</div>
        <div class="summary-item keep">保留: {{ decisionsSummary.keep }}</div>
        <div class="summary-item remove">删除: {{ decisionsSummary.remove }}</div>
      </div>
      <div v-else class="no-data">暂无整合决策</div>
    </div>

    <div class="graph-stats">
      <h5>图谱统计</h5>
      <div>整合前节点: {{ stats.original_nodes }}</div>
      <div>整合后节点: {{ stats.merged_nodes }}</div>
      <div>节点保留率: {{ (stats.node_retention_ratio * 100).toFixed(1) }}%</div>
      <div>关系边数: {{ stats.edge_count }}</div>
      <div>关系边保留率: {{ (stats.edge_retention_ratio * 100).toFixed(1) }}%</div>
    </div>

    <div v-if="stats.completeness_warning" class="warning-box">
      {{ stats.completeness_warning }}
    </div>

    <div v-if="hasData" class="compression-info">
      内容保留率 = 整合后定义字数 / 原始定义字数
    </div>

    <button class="btn-export" @click="exportReport" :disabled="!hasData">导出报告</button>
    </template>
  </div>
</template>

<script>
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { getMergeStats, getMergeDecisions, getMergedGraph } from '../api'

export default {
  name: 'ReportPanel',
  setup() {
    const loading = ref(true)
    const stats = ref({
      original_count: 0,
      original_chars: 0,
      compression_ratio: 0,
      original_nodes: 0,
      merged_nodes: 0,
      edge_count: 0,
      node_retention_ratio: 0,
      edge_retention_ratio: 0,
      completeness_warning: ''
    })

    const decisionsSummary = ref({ merge: 0, keep: 0, remove: 0 })
    const hasData = ref(false)
    let refreshTimer = null

    const exportReport = () => {
      const warning = stats.value.completeness_warning
        ? `\n## 完整性提示\n\n${stats.value.completeness_warning}\n`
        : ''
      const content = `# 整合报告\n\n## 整合概览\n\n| 指标 | 数值 |\n|------|------|\n| 原始教材 | ${stats.value.original_count}本 |\n| 原始字数 | ${stats.value.original_chars.toLocaleString()} |\n| 内容保留率 | ${(stats.value.compression_ratio * 100).toFixed(1)}% |\n| 节点保留率 | ${(stats.value.node_retention_ratio * 100).toFixed(1)}% |\n\n## 图谱统计\n\n| 指标 | 数值 |\n|------|------|\n| 整合前节点 | ${stats.value.original_nodes} |\n| 整合后节点 | ${stats.value.merged_nodes} |\n| 关系边数 | ${stats.value.edge_count} |\n| 关系边保留率 | ${(stats.value.edge_retention_ratio * 100).toFixed(1)}% |\n${warning}\n## 决策摘要\n\n| 操作 | 数量 |\n|------|------|\n| 合并 | ${decisionsSummary.value.merge} |\n| 保留 | ${decisionsSummary.value.keep} |\n| 删除 | ${decisionsSummary.value.remove} |\n`
      const blob = new Blob([content], { type: 'text/markdown' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = '整合报告.md'
      a.click()
    }

    const loadReport = async () => {
      try {
        const [statsRes, decisionsRes, graphRes] = await Promise.all([
          getMergeStats(),
          getMergeDecisions(),
          getMergedGraph()
        ])

        const mergeStats = statsRes.data || {}
        const decisions = decisionsRes.data?.decisions || []
        const mergedGraph = graphRes.data || { nodes: [], edges: [] }

        const summary = { merge: 0, keep: 0, remove: 0 }
        decisions.forEach(d => {
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
          edge_count: mergeStats.edge_count || mergedGraph.edges?.length || 0,
          node_retention_ratio: mergeStats.node_retention_ratio || 0,
          edge_retention_ratio: mergeStats.edge_retention_ratio || 0,
          completeness_warning: mergeStats.completeness_warning || ''
        }

        decisionsSummary.value = summary
        hasData.value = decisions.length > 0 || mergedGraph.nodes?.length > 0
      } catch (err) {
        console.error('加载报告数据失败', err)
      } finally {
        loading.value = false
      }
    }

    onMounted(async () => {
      await loadReport()
      refreshTimer = setInterval(loadReport, 2000)
    })

    onBeforeUnmount(() => {
      if (refreshTimer) clearInterval(refreshTimer)
    })

    return { stats, decisionsSummary, exportReport, hasData, loading }
  }
}
</script>

<style scoped>
.report-panel h4 { margin-bottom: 16px; }
.report-panel .loading,
.report-panel .no-data {
  text-align: center;
  padding: 40px 0;
  color: #999;
  font-size: 14px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.stat-item {
  text-align: center;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 6px;
}
.stat-item .label { font-size: 12px; color: #666; }
.stat-item .value { font-size: 18px; font-weight: 600; margin-top: 4px; }
.stat-item .value.warning { color: #ff4d4f; }

.decisions-summary { margin-bottom: 20px; }
.decisions-summary h5 { font-size: 14px; margin-bottom: 8px; }
.summary-grid { display: flex; gap: 8px; }
.summary-item {
  flex: 1;
  text-align: center;
  padding: 8px;
  border-radius: 4px;
  font-size: 13px;
}
.summary-item.merge { background: #f6ffed; color: #52c41a; }
.summary-item.keep { background: #e6f7ff; color: #1890ff; }
.summary-item.remove { background: #fff2f0; color: #ff4d4f; }

.graph-stats { margin-bottom: 20px; }
.graph-stats h5 { font-size: 14px; margin-bottom: 8px; }
.graph-stats div { font-size: 13px; color: #666; margin-bottom: 4px; }

.warning-box {
  margin-bottom: 16px;
  padding: 10px;
  border: 1px solid #ffe58f;
  border-radius: 4px;
  background: #fffbe6;
  color: #ad6800;
  font-size: 13px;
  line-height: 1.5;
}

.compression-info {
  font-size: 12px;
  color: #999;
  margin-bottom: 16px;
  text-align: center;
}

.btn-export {
  width: 100%;
  padding: 10px;
  background: #52c41a;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-export:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
