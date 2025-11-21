<template>
  <div class="chat-container">
    <div class="chat-header">
      <h1>💬 智能问答</h1>
      <div class="chat-controls">
        <div class="mode-selector">
          <button 
            :class="['mode-btn', { active: chatMode === 'rag' }]"
            @click="chatMode = 'rag'"
          >
            RAG问答 (SSE)
          </button>
          <button 
            :class="['mode-btn', { active: chatMode === 'normal' }]"
            @click="chatMode = 'normal'"
          >
            普通问答
          </button>
        </div>
        <button @click="clearChat" class="clear-btn">清空对话</button>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="(message, index) in messages" 
        :key="index"
        :class="['message', message.role]"
      >
        <div class="message-avatar">
          <span v-if="message.role === 'user'">👤</span>
          <span v-else>🤖</span>
        </div>
        <div class="message-content">
          <div class="message-text" v-html="formatMessage(message.content)"></div>
          <div class="message-time">{{ formatTime(message.timestamp) }}</div>
        </div>
      </div>
      <div v-if="isLoading" class="message assistant">
        <div class="message-avatar">🤖</div>
        <div class="message-content">
          <div class="message-text typing">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-input-container">
      <div class="input-options">
        <input 
          v-model="courseId" 
          type="number" 
          placeholder="课程ID（RAG模式必填）"
          class="course-input"
        />
        <input 
          v-model="sessionId" 
          type="text" 
          placeholder="会话ID（可选，留空自动生成）"
          class="session-input"
        />
      </div>
      <div class="input-wrapper">
        <textarea
          v-model="inputMessage"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.shift.enter.exact="inputMessage += '\n'"
          placeholder="输入您的问题..."
          class="chat-input"
          rows="3"
        ></textarea>
        <button 
          @click="sendMessage" 
          :disabled="!inputMessage.trim() || isLoading"
          class="send-btn"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { chat, chatRagSSE, getChatHistory } from '@/api/rag'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// 简单的UUID生成函数
const generateUUID = () => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

// 配置marked选项
marked.setOptions({
  breaks: true, // 支持换行
  gfm: true, // 支持GitHub风格的Markdown
  headerIds: false, // 不生成header ID
  mangle: false // 不混淆邮箱地址
})

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const chatMode = ref('rag') // 'rag' 或 'normal'
const courseId = ref('')
const sessionId = ref('')
const messagesContainer = ref(null)

// 生成会话ID
const generateSessionId = () => {
  if (!sessionId.value) {
    sessionId.value = generateUUID()
  }
}

// 格式化消息内容（支持Markdown）
const formatMessage = (content) => {
  if (!content) return ''
  
  try {
    // 使用marked将Markdown转换为HTML
    const html = marked.parse(content)
    // 使用DOMPurify清理HTML，防止XSS攻击
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'hr', 'div', 'span'
      ],
      ALLOWED_ATTR: ['href', 'title', 'alt', 'src', 'class']
    })
  } catch (error) {
    console.error('Markdown渲染失败:', error)
    // 如果渲染失败，返回转义的HTML
    return content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const addMessage = (role, content) => {
  messages.value.push({
    role,
    content,
    timestamp: new Date().toISOString()
  })
  scrollToBottom()
}

const clearChat = () => {
  if (confirm('确定要清空所有对话吗？')) {
    messages.value = []
    sessionId.value = ''
  }
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const question = inputMessage.value.trim()
  inputMessage.value = ''

  // 添加用户消息
  addMessage('user', question)

  // 生成会话ID
  generateSessionId()

  isLoading.value = true

  try {
    if (chatMode.value === 'rag') {
      // RAG模式 - SSE流式响应
      let assistantMessageIndex = -1
      
      await chatRagSSE(
        {
          question,
          session_id: sessionId.value,
          course_id: courseId.value ? parseInt(courseId.value) : null
        },
        (data) => {
          // SSE数据流处理
          // 后端返回的数据结构：
          // - 流式状态：{ chunk: "文本片段", status: "streaming", ... }
          // - 完成状态：{ response: "完整回答", status: "completed", ... }
          console.log('收到SSE数据:', data) // 调试用
          
          let content = ''
          if (data.status === 'streaming' && data.chunk) {
            // 流式状态，使用chunk字段
            content = data.chunk
          } else if (data.status === 'completed' && data.response) {
            // 完成状态，使用response字段
            content = data.response
          } else if (data.chunk) {
            // 兼容处理：直接有chunk字段
            content = data.chunk
          } else if (data.response) {
            // 兼容处理：直接有response字段
            content = data.response
          } else if (data.content || data.answer || data.text) {
            // 兼容其他可能的字段名
            content = data.content || data.answer || data.text
          }
          
          if (content) {
            // 如果最后一条消息是AI的，更新它；否则添加新消息
            if (assistantMessageIndex === -1 || 
                !messages.value[assistantMessageIndex] || 
                messages.value[assistantMessageIndex].role !== 'assistant') {
              // 添加新的AI消息
              addMessage('assistant', content)
              assistantMessageIndex = messages.value.length - 1
            } else {
              // 更新现有AI消息（流式追加）
              messages.value[assistantMessageIndex].content += content
            }
            scrollToBottom()
          }
          
          // 如果是完成状态，标记加载完成
          if (data.status === 'completed') {
            isLoading.value = false
          }
        },
        (error) => {
          console.error('SSE错误:', error)
          addMessage('assistant', '抱歉，发生了错误：' + (error.message || '未知错误'))
          isLoading.value = false
        },
        () => {
          isLoading.value = false
        }
      )
    } else {
      // 普通模式 - 同步请求
      const response = await chat({
        question,
        session_id: sessionId.value,
        course_id: courseId.value ? parseInt(courseId.value) : null
      })

      if (response.success && response.data) {
        addMessage('assistant', response.data.answer || '')
      } else {
        addMessage('assistant', response.message || '获取回答失败')
      }
      isLoading.value = false
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    addMessage('assistant', '抱歉，发生了错误：' + (error.message || '未知错误'))
    isLoading.value = false
  }
}

// 加载历史记录
const loadHistory = async () => {
  if (!sessionId.value) return
  
  try {
    const response = await getChatHistory({
      session_id: sessionId.value,
      limit: 50
    })
    
    if (response.success && response.data) {
      messages.value = response.data.map(item => ({
        role: item.role || 'assistant',
        content: item.answer || item.question || '',
        timestamp: item.created_at
      }))
      scrollToBottom()
    }
  } catch (error) {
    console.error('加载历史记录失败:', error)
  }
}

watch(sessionId, () => {
  if (sessionId.value) {
    loadHistory()
  }
})

onMounted(() => {
  generateSessionId()
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.chat-header {
  padding: 20px 30px;
  border-bottom: 2px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.chat-header h1 {
  font-size: 24px;
  margin: 0;
}

.chat-controls {
  display: flex;
  gap: 15px;
  align-items: center;
}

.mode-selector {
  display: flex;
  gap: 5px;
  background: rgba(255, 255, 255, 0.2);
  padding: 5px;
  border-radius: 8px;
}

.mode-btn {
  padding: 8px 16px;
  background: transparent;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.mode-btn.active {
  background: white;
  color: #667eea;
  font-weight: bold;
}

.clear-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.clear-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f8f9fa;
}

.message {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message.assistant .message-avatar {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.message-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.message.user .message-content {
  align-items: flex-end;
}

.message-text {
  padding: 20px 24px;
  border-radius: 12px;
  line-height: 1.8;
  word-wrap: break-word;
  font-size: 15px;
  letter-spacing: 0.3px;
}

.message.user .message-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message.assistant .message-text {
  background: white;
  color: #333;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: 1px solid #f0f0f0;
}

.message-text code {
  background: #f5f5f5;
  padding: 3px 8px;
  border-radius: 4px;
  font-family: 'Courier New', 'Consolas', monospace;
  font-size: 0.9em;
  border: 1px solid #e0e0e0;
}

.message-text pre {
  background: #f8f9fa;
  padding: 18px 20px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  border-left: 4px solid #667eea;
  border: 1px solid #e8e8e8;
}

.message-text pre code {
  background: transparent;
  padding: 0;
  font-size: 0.9em;
}

.message-text h1,
.message-text h2,
.message-text h3,
.message-text h4,
.message-text h5,
.message-text h6 {
  margin: 24px 0 16px 0;
  font-weight: 600;
  line-height: 1.5;
  letter-spacing: 0.2px;
}

.message-text h1:first-child,
.message-text h2:first-child,
.message-text h3:first-child,
.message-text h4:first-child,
.message-text h5:first-child,
.message-text h6:first-child {
  margin-top: 0;
}

.message-text h1 {
  font-size: 1.9em;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 12px;
  margin-top: 0;
}

.message-text h2 {
  font-size: 1.6em;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 10px;
}

.message-text h3 {
  font-size: 1.4em;
  color: #444;
}

.message-text h4 {
  font-size: 1.2em;
  color: #555;
}

.message-text ul,
.message-text ol {
  margin: 16px 0;
  padding-left: 32px;
}

.message-text li {
  margin: 8px 0;
  line-height: 1.8;
  padding-left: 4px;
}

.message-text ul li {
  list-style-type: disc;
}

.message-text ol li {
  list-style-type: decimal;
}

.message-text blockquote {
  border-left: 4px solid #667eea;
  padding: 12px 20px;
  margin: 16px 0;
  color: #666;
  font-style: italic;
  background: #f8f9fa;
  border-radius: 0 6px 6px 0;
}

.message-text hr {
  border: none;
  border-top: 2px solid #e0e0e0;
  margin: 28px 0;
  height: 0;
}

.message-text table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.message-text table th,
.message-text table td {
  border: 1px solid #e0e0e0;
  padding: 12px 16px;
  text-align: left;
}

.message-text table th {
  background: #f8f9fa;
  font-weight: 600;
  color: #333;
}

.message-text a {
  color: #667eea;
  text-decoration: none;
}

.message-text a:hover {
  text-decoration: underline;
}

.message-text p {
  margin: 14px 0;
  line-height: 1.8;
  color: #333;
}

.message-text p:first-child {
  margin-top: 0;
}

.message-text p:last-child {
  margin-bottom: 0;
}

.message-text img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.message-time {
  font-size: 12px;
  color: #999;
  padding: 0 4px;
}

.message.typing {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
}

.message.typing span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #999;
  animation: typing 1.4s infinite;
}

.message.typing span:nth-child(2) {
  animation-delay: 0.2s;
}

.message.typing span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

.chat-input-container {
  padding: 20px;
  border-top: 2px solid #f0f0f0;
  background: white;
}

.input-options {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.course-input,
.session-input {
  flex: 1;
  padding: 8px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  resize: none;
  font-family: inherit;
}

.chat-input:focus {
  outline: none;
  border-color: #667eea;
}

.send-btn {
  padding: 12px 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>

