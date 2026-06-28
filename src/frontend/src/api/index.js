/**
 * API 封装层
 * 职责：统一管理所有后端API调用
 */
import axios from 'axios'

// 创建axios实例，配置默认参数
const api = axios.create({
  baseURL: '/api',  // 开发环境走代理，生产环境填实际地址
  timeout: 60000
})

// ==================== 教材相关API ====================

/**
 * 上传教材文件
 * @param {File} file - 文件对象
 * @returns {Promise} 教材信息
 */
export const uploadTextbook = (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 0,
    onUploadProgress: (event) => {
      if (event.total && onProgress) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    }
  })
}

/**
 * 获取教材列表
 * @returns {Promise} 教材列表
 */
export const getTextbookList = () => api.get('/upload/list')

/**
 * 获取教材详情
 * @param {string} textbookId - 教材ID
 * @returns {Promise} 教材详情
 */
export const getTextbookDetail = (textbookId) => api.get(`/upload/${textbookId}`)

export const getTextbookStatus = (textbookId) => api.get(`/upload/status/${textbookId}`)

// ==================== 知识图谱相关API ====================

/**
 * 获取教材知识图谱
 * @param {string} textbookId - 教材ID
 * @returns {Promise} 图谱数据
 */
export const getGraph = (textbookId) => api.get(`/graph/${textbookId}`)

/**
 * 获取整合后图谱
 * @returns {Promise} 整合图谱
 */
export const getMergedGraph = () => api.get('/graph/merged')

/**
 * 获取知识点详情
 * @param {string} nodeId - 节点ID
 * @returns {Promise} 节点详情
 */
export const getNodeDetail = (nodeId) => api.get(`/graph/node/${nodeId}`)

// ==================== 整合相关API ====================

/**
 * 执行跨教材整合
 * @param {string[]} textbookIds - 教材ID列表
 * @returns {Promise} 整合结果
 */
export const mergeTextbooks = (textbookIds) => api.post('/merge', { textbook_ids: textbookIds })

/**
 * 获取整合决策列表
 * @returns {Promise} 决策列表
 */
export const getMergeDecisions = () => api.get('/merge/decisions')

/**
 * 获取整合统计信息
 * @returns {Promise} 统计信息
 */
export const getMergeStats = () => api.get('/merge/stats')

/**
 * 确认整合
 * @returns {Promise} 确认结果
 */
export const confirmMerge = () => api.post('/merge/confirm')

/**
 * 修改整合决策
 * @param {string} decisionId - 决策ID
 * @param {string} newAction - 新操作类型
 * @returns {Promise} 修改结果
 */
export const modifyDecision = (decisionId, newAction) =>
  api.post('/merge/modify', { decision_id: decisionId, new_action: newAction })

// ==================== RAG问答相关API ====================

/**
 * 建立RAG索引
 * @returns {Promise} 索引状态
 */
export const buildRagIndex = () => api.post('/rag/index')

/**
 * RAG问答
 * @param {string} question - 问题
 * @returns {Promise} 回答结果
 */
export const ragQuery = (question) => api.post('/rag/query', { question })

/**
 * 获取RAG状态
 * @returns {Promise} 状态信息
 */
export const getRagStatus = () => api.get('/rag/status')

// ==================== 对话相关API ====================

/**
 * 发送对话消息
 * @param {string} message - 消息内容
 * @param {string} sessionId - 会话ID
 * @returns {Promise} 回复
 */
export const sendChat = (message, sessionId = 'default') =>
  api.post('/chat', { message, session_id: sessionId })

/**
 * 获取对话历史
 * @param {string} sessionId - 会话ID
 * @returns {Promise} 历史消息
 */
export const getChatHistory = (sessionId = 'default') =>
  api.get('/chat/history', { params: { session_id: sessionId } })

export default api
