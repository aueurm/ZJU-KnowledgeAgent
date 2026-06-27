<template>
  <div class="merge-panel">
    <h4>跨教材整合</h4>

    <div class="selected-books">
      <div class="label">已选教材：</div>
      <div v-if="selectedBooks.length === 0" class="empty">请在左侧选择教材</div>
      <div v-for="id in selectedBooks" :key="id" class="book-tag">
        {{ id }}
        <span @click="removeBook(id)">×</span>
      </div>
    </div>

    <button class="btn-primary" @click="startMerge" :disabled="selectedBooks.length < 2">
      开始整合
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
import { ref, onMounted } from 'vue'
import { getMergeDecisions, mergeTextbooks, confirmMerge as confirmMergeApi } from '../api'

export default {
  name: 'MergePanel',
  setup() {
    const selectedBooks = ref([])
    const decisions = ref([])
    const compressionRatio = ref(0)

    const removeBook = (id) => {
      selectedBooks.value = selectedBooks.value.filter(b => b !== id)
    }

    const startMerge = async () => {
      try {
        const res = await mergeTextbooks(selectedBooks.value)
        decisions.value = res.data.decisions || []
        compressionRatio.value = res.data.compression_ratio || 0
      } catch (err) {
        console.error('整合失败', err)
      }
    }

    const confirmMerge = async () => {
      try {
        await confirmMergeApi()
        decisions.value = []
        alert('整合已完成')
      } catch (err) {
        console.error('确认失败', err)
      }
    }

    onMounted(async () => {
      try {
        const res = await getMergeDecisions()
        decisions.value = res.data.decisions || []
      } catch (err) {
        console.error('获取决策失败', err)
      }
    })

    return { selectedBooks, decisions, compressionRatio, removeBook, startMerge, confirmMerge }
  }
}
</script>

<style scoped>
.merge-panel h4 { margin-bottom: 16px; }
.selected-books { margin-bottom: 16px; }
.label { font-size: 13px; color: #666; margin-bottom: 8px; }
.empty { color: #999; font-size: 13px; }
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