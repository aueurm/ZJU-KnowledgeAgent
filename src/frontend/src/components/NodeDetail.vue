<template>
  <div class="node-detail-overlay" @click.self="$emit('close')">
    <div class="node-detail">
      <div class="header">
        <h4>{{ node.name }}</h4>
        <button class="close-btn" @click="$emit('close')">×</button>
      </div>

      <div class="content">
        <div class="info-row">
          <span class="label">类型：</span>
          <span class="value">{{ node.category }}</span>
        </div>
        <div class="info-row">
          <span class="label">来源：</span>
          <span class="value">{{ node.source }}</span>
        </div>
        <div class="info-row">
          <span class="label">章节：</span>
          <span class="value">{{ node.chapter }}</span>
        </div>
        <div v-if="node.module" class="info-row">
          <span class="label">模块：</span>
          <span class="value">{{ node.module }}</span>
        </div>
        <div class="info-row">
          <span class="label">页码：</span>
          <span class="value">{{ node.page }}</span>
        </div>
        <div class="info-row">
          <span class="label">频次：</span>
          <span class="value">{{ node.freq || 1 }} 本教材提及</span>
        </div>

        <div class="definition">
          <div class="label">定义：</div>
          <div class="value">{{ node.definition }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'NodeDetail',
  props: {
    node: { type: Object, required: true }
  },
  emits: ['close']
}
</script>

<style scoped>
.node-detail-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.node-detail {
  width: 400px;
  max-height: 80vh;
  background: white;
  border-radius: 8px;
  overflow: hidden;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #eee;
}

.header h4 { margin: 0; font-size: 16px; }

.close-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  font-size: 20px;
  cursor: pointer;
  color: #999;
}
.close-btn:hover { color: #333; }

.content { padding: 16px; }

.info-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;
}

.label { color: #666; width: 60px; }

.definition {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.definition .label { display: block; margin-bottom: 8px; }

.definition .value {
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}
</style>
