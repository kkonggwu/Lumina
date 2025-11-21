import request from './request'
import { useAuthStore } from '@/stores/auth'

// 普通问答（同步）
export const chat = (data) => {
  return request({
    url: '/rag/chat/',
    method: 'post',
    data
  })
}

// RAG问答（SSE流式）
export const chatRagSSE = (data, onMessage, onError, onComplete) => {
  const authStore = useAuthStore()
  const token = authStore.accessToken
  
  console.log('开始SSE请求:', data) // 调试
  
  // EventSource不支持POST和自定义headers，使用fetch + ReadableStream实现SSE
  return fetch('/api/rag/chat_rag', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  }).then(response => {
    console.log('SSE响应状态:', response.status, response.statusText) // 调试
    
    if (!response.ok) {
      return response.json().then(err => {
        console.error('SSE响应错误:', err)
        throw new Error(err.message || 'SSE连接失败')
      }).catch(() => {
        throw new Error(`SSE连接失败: ${response.status} ${response.statusText}`)
      })
    }
    
    // 检查Content-Type是否为text/event-stream
    const contentType = response.headers.get('content-type') || ''
    console.log('SSE Content-Type:', contentType) // 调试
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    
    const readStream = () => {
      reader.read().then(({ done, value }) => {
        if (done) {
          console.log('SSE流读取完成') // 调试
          // 处理缓冲区中剩余的数据
          if (buffer.trim()) {
            processBuffer(buffer)
            buffer = ''
          }
          if (onComplete) onComplete()
          return
        }
        
        // 解码新数据并添加到缓冲区
        const chunk = decoder.decode(value, { stream: true })
        buffer += chunk
        
        // 处理完整的SSE消息（以\n\n分隔）
        const messages = buffer.split(/\n\n/)
        // 保留最后一个可能不完整的消息
        buffer = messages.pop() || ''
        
        // 处理每个完整的消息
        messages.forEach(msg => {
          processBuffer(msg)
        })
        
        // 继续读取
        readStream()
      }).catch(err => {
        console.error('读取SSE流失败:', err)
        if (onError) onError(err)
      })
    }
    
    // 处理SSE消息缓冲区
    const processBuffer = (msg) => {
      msg = msg.trim()
      if (!msg) return
      
      // SSE格式：data: {...} 或 data: 文本
      if (msg.startsWith('data: ')) {
        const dataStr = msg.slice(6).trim()
        if (dataStr) {
          try {
            const parsedData = JSON.parse(dataStr)
            console.log('解析SSE数据成功:', parsedData) // 调试
            if (onMessage) onMessage(parsedData)
          } catch (e) {
            console.warn('解析SSE JSON失败，尝试作为纯文本处理:', e, '数据:', dataStr.substring(0, 100))
            // 如果不是JSON，可能是纯文本chunk
            if (onMessage && dataStr) {
              onMessage({ chunk: dataStr })
            }
          }
        }
      } else if (msg && !msg.startsWith(':')) {
        // 处理没有data:前缀的数据
        try {
          const parsedData = JSON.parse(msg)
          console.log('解析SSE数据成功（无前缀）:', parsedData) // 调试
          if (onMessage) onMessage(parsedData)
        } catch (e) {
          // 纯文本数据
          if (onMessage && msg.trim()) {
            console.log('处理纯文本SSE数据:', msg.substring(0, 100)) // 调试
            onMessage({ chunk: msg })
          }
        }
      }
    }
    
    // 开始读取流
    readStream()
  }).catch(err => {
    console.error('SSE请求失败:', err)
    if (onError) onError(err)
  })
}

// 获取问答历史
export const getChatHistory = (params) => {
  return request({
    url: '/rag/history/',
    method: 'get',
    params
  })
}

