<template>
  <div class="merge-panel">
    <h4>跨教材整合</h4>

    <div class="selected-books">
      <div class="label">已选教材：</div>
      <div v-if="selectedBooks.length === 0" class="empty">请选择至少 2 本已解析教材</div>
      <div v-for="id in selectedBooks" :key="id" class="book-tag">
        {{ id }}
        <span @click="removeBook(id)">×</span>
      </div>
    </div>

    <div class="book-options">
      <div v-if="loadingBooks" class="empty">正在加载教材...</div>
      <div v-else-if="availableBooks.length === 0" class="empty">暂无已解析教材</div>
      <label v-for="book in availableBooks" :key="book.textbook_id" class="book-option">
        <input
          type="checkbox"
          :checked="selectedBooks.includes(book.textbook_id)"
          @change="toggleBook(book.textbook_id)"
        />
        <span>{{ book.filename }}</span>
      </label>
    </div>

    <div v-if="error" class="error-msg">{{ error }}</div>
    <div v-if="compressionRatio" class="ratio">
      内容保留率：{{ (compressionRatio * 100).toFixed(1) }}%
    </div>
    <div v-if="nodeRetentionRatio" class="ratio">
      节点保留率：{{ (nodeRetentionRatio * 100).toFixed(1) }}%
    </div>
    <div v-if="completenessWarning" class="warning-msg">
      {{ completenessWarning }}
    </div>

    <button class="btn-primary" @click="startMerge" :disabled="selectedBooks.length < 2 || merging">
      {{ merging ? '整合中...' : '开始整合' }}
    </button>

    <div v-if="decisions.length > 0" class="decisions">
      <h5>整合决策 ({{ decisions.length }})</h5>
      <div v-for="d in decisions" :key="d.decision_id" class="decision-item">
        <div class="action">
          <span :class="d.action">{{ d.action }}</span>
          {{ d.reason }}
        </div>
        <div class="nodes">涉及节点: {{ d.affected_nodes.length }}</div>
      </div>
      <button class="btn-primary" @click="confirmMerge">确认整合</button>
    </div>
  </div>
</template>

<script>
import { ref, onBeforeUnmount, onMounted } from 'vue'
import { getMergeDecisions, getMergeStats, getTextbookList, mergeTextbooks, confirmMerge as confirmMergeApi } from '../api'

export default {
  name: 'MergePanel',
  emits: ['merged'],
  setup(props, { emit }) {
    const availableBooks = ref([])
    const selectedBooks = ref([])
    const decisions = ref([])
    const compressionRatio = ref(0)
    const nodeRetentionRatio = ref(0)
    const completenessWarning = ref('')
    const loadingBooks = ref(false)
    const merging = ref(false)
    const error = ref('')
    let refreshTimer = null
    let booksLoading = false

    const loadBooks = async (silent = false) => {
      if (booksLoading) return
      booksLoading = true
      if (!silent) loadingBooks.value = true
      try {
        const res = await getTextbookList()
        availableBooks.value = (res.data.textbooks || []).filter(b => b.status === 'parsed')
        selectedBooks.value = selectedBooks.value.filter(id =>
          availableBooks.value.some(book => book.textbook_id === id)
        )
      } catch (err) {
        if (!silent) error.value = '教材列表加载失败'
        console.error('教材列表加载失败', err)
      } finally {
        if (!silent) loadingBooks.value = false
        booksLoading = false
      }
    }

    const loadDecisions = async () => {
      try {
        const res = await getMergeDecisions()
        decisions.value = res.data.decisions || []
      } catch (err) {
        console.error('获取决策失败', err)
      }
    }

    const loadStats = async () => {
      try {
        const res = await getMergeStats()
        const stats = res.data || {}
        compressionRatio.value = stats.compression_ratio || 0
        nodeRetentionRatio.value = stats.node_retention_ratio || 0
        completenessWarning.value = stats.completeness_warning || ''
      } catch (err) {
        console.error('获取整合统计失败', err)
      }
    }

    const refreshAll = async (silent = false) => {
      await Promise.all([loadBooks(silent), loadDecisions(), loadStats()])
    }

    const toggleBook = (id) => {
      if (selectedBooks.value.includes(id)) {
        removeBook(id)
      } else {
        selectedBooks.value.push(id)
      }
    }

    const removeBook = (id) => {
      selectedBooks.value = selectedBooks.value.filter(b => b !== id)
    }

    const startMerge = async () => {
      error.value = ''
      merging.value = true
      try {
        const res = await mergeTextbooks(selectedBooks.value)
        decisions.value = res.data.decisions || []
        compressionRatio.value = res.data.compression_ratio || 0
        nodeRetentionRatio.value = res.data.node_retention_ratio || 0
        completenessWarning.value = res.data.completeness_warning || ''
        emit('merged')
      } catch (err) {
        error.value = err.response?.data?.detail || err.message || '整合失败'
        console.error('整合失败', err)
      } finally {
        merging.value = false
      }
    }

    const confirmMerge = async () => {
      try {
        await confirmMergeApi()
        decisions.value = []
        await refreshAll(true)
        emit('merged')
        alert('整合已完成')
      } catch (err) {
        console.error('确认失败', err)
      }
    }

    onMounted(async () => {
      await refreshAll()
      refreshTimer = setInterval(() => refreshAll(true), 2000)
    })

    onBeforeUnmount(() => {
      if (refreshTimer) clearInterval(refreshTimer)
    })

    return {
      availableBooks,
      selectedBooks,
      decisions,
      compressionRatio,
      nodeRetentionRatio,
      completenessWarning,
      loadingBooks,
      merging,
      error,
      toggleBook,
      removeBook,
      startMerge,
      confirmMerge
    }
  }
}
</script>

<style scoped>
.merge-panel h4 { margin-bottom: 16px; }
.selected-books { margin-bottom: 16px; }
.label { font-size: 13px; color: #666; margin-bottom: 8px; }
.empty { color: #999; font-size: 13px; }
.book-options {
  margin-bottom: 16px;
  border: 1px solid #eee;
  border-radius: 6px;
  max-height: 180px;
  overflow-y: auto;
}
.book-option {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 8px 10px;
  font-size: 13px;
  border-bottom: 1px solid #f3f3f3;
  cursor: pointer;
}
.book-option:last-child { border-bottom: none; }
.book-option span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.book-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  background: #e6f7ff;
  border-radius: 4px;
  margin: 0 4px 4px 0;
  font-size: 12px;
}
.book-tag span { margin-left: 4px; cursor: pointer; color: #999; }
.book-tag span:hover { color: #f5222d; }
.error-msg {
  margin-bottom: 10px;
  color: #ff4d4f;
  font-size: 13px;
}
.ratio {
  margin-bottom: 10px;
  color: #666;
  font-size: 13px;
}
.warning-msg {
  margin-bottom: 10px;
  color: #fa8c16;
  font-size: 13px;
  line-height: 1.5;
}

.btn-primary {
  width: 100%;
  padding: 10px;
  background: #1890ff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.btn-primary:disabled { background: #d9d9d9; cursor: not-allowed; }

.decisions { margin-top: 20px; }
.decisions h5 { font-size: 14px; margin-bottom: 12px; }
.decision-item {
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-bottom: 8px;
}
.action { font-size: 13px; }
.nodes { font-size: 12px; color: #999; margin-top: 4px; }
span.merge { color: #52c41a; }
span.keep { color: #1890ff; }
span.remove { color: #ff4d4f; }
</style>
