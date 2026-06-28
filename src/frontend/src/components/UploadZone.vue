<template>
  <div
    class="upload-zone"
    :class="{ dragover: isDragover }"
    @dragover.prevent="isDragover = true"
    @dragleave="isDragover = false"
    @drop.prevent="handleDrop"
    @click="triggerInput"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.md,.txt,.docx"
      multiple
      @change="handleFileSelect"
      hidden
    />
    <div class="upload-icon">+</div>
    <div class="upload-text">
      拖拽教材文件到此处<br>
      或点击选择文件
    </div>
    <div class="upload-hint">支持 PDF、Markdown、TXT、DOCX</div>

    <div v-if="uploads.length" class="upload-list" @click.stop>
      <div v-for="item in uploads" :key="item.id" class="upload-item">
        <div class="upload-row">
          <span class="upload-name">{{ item.name }}</span>
          <span :class="['upload-status', item.status]">{{ getStatusText(item.status) }}</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar" :style="{ width: item.progress + '%' }"></div>
        </div>
        <div class="upload-step">{{ item.step }}</div>
        <div v-if="item.warning" class="warning-msg">{{ item.warning }}</div>
        <div v-if="item.error" class="error-msg">{{ item.error }}</div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { getTextbookStatus, uploadTextbook } from '../api'

export default {
  name: 'UploadZone',
  emits: ['uploaded', 'error'],
  setup(props, { emit }) {
    const fileInput = ref(null)
    const isDragover = ref(false)
    const uploads = ref([])

    // 触发文件选择
    const triggerInput = () => fileInput.value?.click()

    // 处理文件选择
    const handleFileSelect = async (e) => {
      const files = e.target.files
      await uploadFiles(files)
      fileInput.value.value = ''  // 清空以便重复选择同一文件
    }

    // 处理拖拽
    const handleDrop = async (e) => {
      isDragover.value = false
      const files = e.dataTransfer.files
      await uploadFiles(files)
    }

    // 上传文件
    const uploadFiles = async (files) => {
      await Promise.all(Array.from(files).map(uploadOneFile))
    }

    const uploadOneFile = async (file) => {
        const item = {
          id: `${file.name}-${file.size}-${Date.now()}`,
          name: file.name,
          status: 'uploading',
          progress: 0,
          step: '正在上传',
          error: '',
          warning: ''
        }
        uploads.value.unshift(item)

        try {
          const res = await uploadTextbook(file, (percent) => {
            item.progress = Math.min(45, Math.round(percent * 0.45))
            item.step = `正在上传 ${percent}%`
          })
          const textbookId = res.data.textbook_id
          item.status = 'parsing'
          item.progress = Math.max(item.progress, 50)
          item.step = '上传完成，正在解析'
          emit('uploaded', file.name)
          await pollStatus(textbookId, item)
        } catch (err) {
          item.status = 'failed'
          item.progress = 100
          item.error = getErrorMessage(err)
          item.step = '处理失败'
          emit('error', { file: file.name, error: err })
        }
    }

    const pollStatus = async (textbookId, item) => {
      while (item.status === 'parsing') {
        await sleep(1500)
        const res = await getTextbookStatus(textbookId)
        const data = res.data
        item.progress = Math.max(item.progress, data.progress || 50)
        item.step = data.current_step || item.step
        item.warning = data.warning || ''
        emit('uploaded', item.name)

        if (data.status === 'parsed') {
          item.status = 'parsed'
          item.progress = 100
          item.step = data.warning ? '解析完成，RAG 索引有警告' : '解析完成'
          emit('uploaded', item.name)
          return
        }

        if (data.status === 'failed') {
          throw new Error(data.error || '后端解析失败')
        }
      }
    }

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))

    const getErrorMessage = (err) =>
      err.response?.data?.detail || err.message || '上传失败'

    const getStatusText = (status) => {
      const map = {
        uploading: '上传中',
        parsing: '解析中',
        parsed: '完成',
        failed: '失败'
      }
      return map[status] || status
    }

    return {
      fileInput,
      isDragover,
      uploads,
      triggerInput,
      handleFileSelect,
      handleDrop,
      getStatusText
    }
  }
}
</script>

<style scoped>
.upload-zone {
  margin: 16px;
  padding: 32px 16px;
  border: 2px dashed #ddd;
  border-radius: 8px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.upload-zone:hover,
.upload-zone.dragover {
  border-color: #1890ff;
  background: #f0f7ff;
}

.upload-icon {
  font-size: 48px;
  color: #ccc;
  margin-bottom: 8px;
}

.upload-text {
  color: #666;
  font-size: 14px;
  line-height: 1.6;
}

.upload-hint {
  margin-top: 8px;
  color: #999;
  font-size: 12px;
}

.upload-list {
  margin-top: 16px;
  text-align: left;
}

.upload-item {
  padding: 10px;
  border: 1px solid #eee;
  border-radius: 6px;
  background: white;
  margin-top: 8px;
}

.upload-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.upload-name {
  min-width: 0;
  flex: 1;
  color: #333;
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-status {
  flex-shrink: 0;
  font-size: 12px;
  color: #666;
}

.upload-status.parsed { color: #52c41a; }
.upload-status.failed { color: #ff4d4f; }

.progress-track {
  height: 6px;
  margin-top: 8px;
  background: #f0f0f0;
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: #1890ff;
  transition: width 0.2s ease;
}

.upload-step,
.warning-msg,
.error-msg {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.4;
}

.upload-step { color: #666; }
.warning-msg { color: #fa8c16; }
.error-msg { color: #ff4d4f; }
</style>
