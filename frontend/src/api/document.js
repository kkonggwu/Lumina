import request from './request'

// 上传文档
export const uploadDocument = (formData) => {
  return request({
    url: '/course/documents/upload/',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取文档列表
export const getDocumentList = (params) => {
  return request({
    url: '/course/documents/',
    method: 'get',
    params
  })
}

// 获取文档详情
export const getDocumentDetail = (documentId) => {
  return request({
    url: `/course/documents/${documentId}/`,
    method: 'get'
  })
}

// 下载文档
export const downloadDocument = (documentId) => {
  return request({
    url: `/course/documents/${documentId}/download/`,
    method: 'get',
    responseType: 'blob'
  })
}

// 删除文档
export const deleteDocument = (documentId) => {
  return request({
    url: `/course/documents/${documentId}/delete/`,
    method: 'delete'
  })
}


