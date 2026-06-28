<template>
  <div class="textbook-list">
    <h3>已上传教材</h3>
    <div v-if="textbooks.length === 0" class="empty">
      暂无教材，请上传
    </div>
    <div
      v-for="book in textbooks"
      :key="book.textbook_id"
      class="textbook-item"
      :class="{ selected: book.textbook_id === selectedId }"
      @click="$emit('select', book.textbook_id)"
    >
      <div class="book-icon">📚</div>
      <div class="book-info">
        <div class="book-name">{{ book.filename }}</div>
        <div class="book-status">
          <span :class="['status', book.status]">{{ getStatusText(book.status) }}</span>
          <span v-if="book.status === 'parsing'" class="progress-text">{{ book.progress || 0 }}%</span>
        </div>
        <div v-if="book.status === 'parsing'" class="progress-track">
          <div class="progress-bar" :style="{ width: (book.progress || 0) + '%' }"></div>
        </div>
        <div v-if="book.current_step" class="book-step">{{ book.current_step }}</div>
        <div v-if="book.warning" class="book-warning">{{ book.warning }}</div>
        <div v-if="book.error" class="book-error">{{ book.error }}</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TextbookList',
  props: {
    textbooks: { type: Array, default: () => [] },
    selectedId: { type: String, default: null }
  },
  emits: ['select'],
  setup() {
    const getStatusText = (status) => {
      const map = { parsing: '解析中', parsed: '已完成', failed: '失败' }
      return map[status] || status
    }
    return { getStatusText }
  }
}
</script>

<style scoped>
.textbook-list { padding: 16px; }
.textbook-list h3 { font-size: 14px; color: #666; margin-bottom: 12px; }
.empty { color: #999; font-size: 13px; text-align: center; padding: 20px 0; }

.textbook-item {
  display: flex;
  align-items: center;
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.textbook-item:hover { background: #f5f5f5; }
.textbook-item.selected {
  border-color: #1890ff;
  background: #f0f7ff;
}

.book-icon { font-size: 24px; margin-right: 12px; }
.book-name { font-size: 14px; color: #333; }
.book-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}
.progress-text {
  color: #999;
  font-size: 12px;
}
.progress-track {
  height: 5px;
  margin-top: 6px;
  background: #f0f0f0;
  border-radius: 999px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  background: #1890ff;
  transition: width 0.2s ease;
}
.book-step,
.book-warning,
.book-error {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-word;
}
.book-step { color: #888; }
.book-warning { color: #fa8c16; }
.book-error { color: #ff4d4f; }
.status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
}
.status.parsing { background: #fff7e6; color: #fa8c16; }
.status.parsed { background: #f6ffed; color: #52c41a; }
.status.failed { background: #fff2f0; color: #ff4d4f; }
</style>
