<template>
    <div class="documents-container">
        <div class="page-header">
            <h1>📚 文档管理</h1>
            <div class="header-actions">
                <input v-model="filters.course_id" type="number" placeholder="课程ID筛选" class="filter-input"
                    @input="loadDocuments" />
                <button @click="showUploadModal = true" class="upload-btn" v-if="!isStudent">
                    + 上传文档
                </button>
            </div>
        </div>

        <div class="table-container">
            <table class="documents-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>文件名</th>
                        <th>课程名称</th>
                        <th>上传者</th>
                        <th>文件大小</th>
                        <th>文件类型</th>
                        <th>状态</th>
                        <th>上传时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="doc in documents" :key="doc.id">
                        <td>{{ doc.id }}</td>
                        <td>{{ doc.file_name }}</td>
                        <td>{{ doc.course_name || '-' }}</td>
                        <td>{{ doc.uploader_name || '-' }}</td>
                        <td>{{ formatFileSize(doc.file_size) }}</td>
                        <td>{{ doc.file_type || '-' }}</td>
                        <td>
                            <span :class="['status-badge', `status-${doc.document_status}`]">
                                {{ doc.document_status_display || getStatusName(doc.document_status) }}
                            </span>
                        </td>
                        <td>{{ formatDate(doc.uploaded_at) }}</td>
                        <td>
                            <button @click="viewDetail(doc)" class="action-btn view">详情</button>
                            <button @click="downloadDocument(doc.id, doc)" class="action-btn download">下载</button>
                            <button v-if="!isStudent" @click="confirmDelete(doc)" class="action-btn delete">
                                删除
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>

            <div v-if="loading" class="loading">加载中...</div>
            <div v-if="!loading && documents.length === 0" class="empty">暂无文档</div>

            <!-- 分页 -->
            <div v-if="total > 0" class="pagination">
                <button @click="changePage(page - 1)" :disabled="page <= 1" class="page-btn">
                    上一页
                </button>
                <span class="page-info">
                    第 {{ page }} 页，共 {{ Math.ceil(total / pageSize) }} 页，共 {{ total }} 条
                </span>
                <button @click="changePage(page + 1)" :disabled="page >= Math.ceil(total / pageSize)" class="page-btn">
                    下一页
                </button>
            </div>
        </div>

        <!-- 上传文档模态框 -->
        <div v-if="showUploadModal" class="modal-overlay" @click="showUploadModal = false">
            <div class="modal-content" @click.stop>
                <h2>上传文档</h2>
                <form @submit.prevent="handleUpload">
                    <div class="form-group">
                        <label>课程ID <span class="required">*</span></label>
                        <input v-model="uploadForm.course_id" type="number" required placeholder="请输入课程ID" />
                    </div>
                    <div class="form-group">
                        <label>选择文件 <span class="required">*</span></label>
                        <input type="file" ref="fileInput" @change="handleFileSelect"
                            accept=".md,.txt,.markdown,.pdf,.docx" required />
                        <div v-if="selectedFile" class="file-info">
                            已选择: {{ selectedFile.name }} ({{ formatFileSize(selectedFile.size) }})
                        </div>
                        <div class="file-hint">
                            支持格式: .md, .txt, .markdown, .pdf, .docx，最大50MB
                        </div>
                    </div>
                    <div class="modal-actions">
                        <button type="button" @click="closeUploadModal" class="btn-cancel">取消</button>
                        <button type="submit" :disabled="uploading" class="btn-submit">
                            {{ uploading ? '上传中...' : '上传' }}
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- 文档详情模态框 -->
        <div v-if="showDetailModal && currentDocument" class="modal-overlay" @click="showDetailModal = false">
            <div class="modal-content detail-modal" @click.stop>
                <h2>文档详情</h2>
                <div class="detail-content">
                    <div class="detail-item">
                        <label>文档ID:</label>
                        <span>{{ currentDocument.id }}</span>
                    </div>
                    <div class="detail-item">
                        <label>文件名:</label>
                        <span>{{ currentDocument.file_name }}</span>
                    </div>
                    <div class="detail-item">
                        <label>课程名称:</label>
                        <span>{{ currentDocument.course_name || '-' }}</span>
                    </div>
                    <div class="detail-item">
                        <label>上传者:</label>
                        <span>{{ currentDocument.uploader_name || '-' }}</span>
                    </div>
                    <div class="detail-item">
                        <label>文件大小:</label>
                        <span>{{ formatFileSize(currentDocument.file_size) }}</span>
                    </div>
                    <div class="detail-item">
                        <label>文件类型:</label>
                        <span>{{ currentDocument.file_type || '-' }}</span>
                    </div>
                    <div class="detail-item">
                        <label>MIME类型:</label>
                        <span>{{ currentDocument.mime_type || '-' }}</span>
                    </div>
                    <div class="detail-item">
                        <label>状态:</label>
                        <span :class="['status-badge', `status-${currentDocument.document_status}`]">
                            {{ currentDocument.document_status_display || getStatusName(currentDocument.document_status)
                            }}
                        </span>
                    </div>
                    <div class="detail-item" v-if="currentDocument.processing_log">
                        <label>处理日志:</label>
                        <div class="log-content">{{ currentDocument.processing_log }}</div>
                    </div>
                    <div class="detail-item">
                        <label>上传时间:</label>
                        <span>{{ formatDate(currentDocument.uploaded_at) }}</span>
                    </div>
                    <div class="detail-item">
                        <label>更新时间:</label>
                        <span>{{ formatDate(currentDocument.updated_at) }}</span>
                    </div>
                </div>
                <div class="modal-actions">
                    <button @click="downloadDocument(currentDocument.id)" class="btn-submit">下载文档</button>
                    <button @click="showDetailModal = false" class="btn-cancel">关闭</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import {
    getDocumentList,
    uploadDocument,
    getDocumentDetail,
    deleteDocument
} from '@/api/document'

const authStore = useAuthStore()
const isStudent = computed(() => authStore.isStudent)

const documents = ref([])
const loading = ref(false)
const uploading = ref(false)
const showUploadModal = ref(false)
const showDetailModal = ref(false)
const currentDocument = ref(null)
const selectedFile = ref(null)
const fileInput = ref(null)

const filters = ref({
    course_id: ''
})

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const uploadForm = ref({
    course_id: '',
    file: null
})

const loadDocuments = async () => {
    loading.value = true
    try {
        const params = {
            page: page.value,
            page_size: pageSize.value
        }
        if (filters.value.course_id) {
            params.course_id = parseInt(filters.value.course_id)
        }

        const response = await getDocumentList(params)
        if (response.success) {
            documents.value = response.data || []
            total.value = response.total || 0
        } else {
            alert(response.message || '加载文档列表失败')
        }
    } catch (error) {
        console.error('加载文档列表失败:', error)
        alert(error.message || '加载文档列表失败')
    } finally {
        loading.value = false
    }
}

const formatFileSize = (bytes) => {
    if (!bytes) return '-'
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

const formatDate = (dateString) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('zh-CN')
}

const getStatusName = (status) => {
    const statusMap = {
        0: '上传中',
        1: '处理成功',
        2: '处理失败'
    }
    return statusMap[status] || '未知'
}

const handleFileSelect = (event) => {
    const file = event.target.files[0]
    if (file) {
        // 检查文件大小（50MB）
        const maxSize = 50 * 1024 * 1024
        if (file.size > maxSize) {
            alert('文件大小不能超过50MB')
            event.target.value = ''
            selectedFile.value = null
            return
        }
        selectedFile.value = file
        uploadForm.value.file = file
    }
}

const handleUpload = async () => {
    if (!uploadForm.value.course_id || !uploadForm.value.file) {
        alert('请填写课程ID并选择文件')
        return
    }

    uploading.value = true
    try {
        const formData = new FormData()
        formData.append('course_id', uploadForm.value.course_id)
        formData.append('file', uploadForm.value.file)

        const response = await uploadDocument(formData)
        if (response.success) {
            alert('上传成功')
            closeUploadModal()
            loadDocuments()
        } else {
            alert(response.message || '上传失败')
        }
    } catch (error) {
        console.error('上传失败:', error)
        alert(error.message || '上传失败')
    } finally {
        uploading.value = false
    }
}

const closeUploadModal = () => {
    showUploadModal.value = false
    uploadForm.value = {
        course_id: '',
        file: null
    }
    selectedFile.value = null
    if (fileInput.value) {
        fileInput.value.value = ''
    }
}

const viewDetail = async (doc) => {
    try {
        const response = await getDocumentDetail(doc.id)
        if (response.success) {
            currentDocument.value = response.data
            showDetailModal.value = true
        } else {
            alert(response.message || '获取文档详情失败')
        }
    } catch (error) {
        console.error('获取文档详情失败:', error)
        alert(error.message || '获取文档详情失败')
    }
}

const downloadDocument = async (documentId, docInfo = null) => {
    try {
        // 获取文档信息（优先使用传入的参数，否则从列表中查找）
        const doc = docInfo || documents.value.find(d => d.id === documentId)
        let defaultFilename = doc ? doc.file_name : 'document'

        // 使用axios直接请求，因为需要获取完整的response对象
        const token = authStore.accessToken

        const response = await axios({
            url: `/api/course/documents/${documentId}/download/`,
            method: 'get',
            responseType: 'blob',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        })

        // 处理blob响应
        const blob = response.data
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url

        // 从响应头获取文件名（尝试多种可能的键名）
        let filename = defaultFilename

        // axios 响应头键名可能是小写，尝试多种可能的键名
        let contentDisposition = response.headers['content-disposition'] ||
            response.headers['Content-Disposition'] ||
            response.headers['Content-Disposition']

        // 如果是字符串，直接使用；如果是数组，取第一个元素
        if (Array.isArray(contentDisposition)) {
            contentDisposition = contentDisposition[0]
        }

        if (contentDisposition && typeof contentDisposition === 'string') {
            // 尝试匹配 filename="..." 或 filename=... 或 filename*=UTF-8''...
            const patterns = [
                /filename\*=UTF-8''([^;]+)/i,  // RFC 5987 格式
                /filename\*=['"]?([^'";]+)['"]?/i,  // 带星号的格式
                /filename=['"]?([^'";]+)['"]?/i  // 标准格式
            ]

            for (const pattern of patterns) {
                const match = contentDisposition.match(pattern)
                if (match && match[1]) {
                    // 处理URL编码的文件名
                    let extractedFilename = match[1].trim()
                    // 移除可能的引号
                    extractedFilename = extractedFilename.replace(/^["']|["']$/g, '')
                    // 尝试解码（可能是URL编码）
                    try {
                        filename = decodeURIComponent(extractedFilename)
                    } catch {
                        filename = extractedFilename
                    }
                    break
                }
            }
        }

        // 确保文件名有正确的扩展名
        if (!filename.includes('.')) {
            // 如果文件名没有扩展名，尝试从文档信息中获取
            if (doc) {
                // 优先使用 file_type（不带点号的扩展名）
                if (doc.file_type) {
                    filename = `${filename}.${doc.file_type}`
                }
                // 如果 file_type 也没有，尝试从原始文件名中提取
                else if (doc.file_name && doc.file_name.includes('.')) {
                    const ext = doc.file_name.split('.').pop()
                    filename = `${filename}.${ext}`
                }
            }
        }

        link.download = filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
    } catch (error) {
        console.error('下载失败:', error)
        // 如果是blob错误响应，尝试解析JSON
        if (error.response && error.response.data instanceof Blob) {
            const text = await error.response.data.text()
            try {
                const errorData = JSON.parse(text)
                alert(errorData.message || '下载失败')
            } catch {
                alert('下载失败')
            }
        } else {
            alert(error.message || '下载失败')
        }
    }
}

const confirmDelete = (doc) => {
    if (confirm(`确定要删除文档 "${doc.file_name}" 吗？`)) {
        handleDelete(doc.id)
    }
}

const handleDelete = async (documentId) => {
    try {
        const response = await deleteDocument(documentId)
        if (response.success) {
            alert('删除成功')
            loadDocuments()
        } else {
            alert(response.message || '删除失败')
        }
    } catch (error) {
        console.error('删除失败:', error)
        alert(error.message || '删除失败')
    }
}

const changePage = (newPage) => {
    if (newPage >= 1 && newPage <= Math.ceil(total.value / pageSize.value)) {
        page.value = newPage
        loadDocuments()
    }
}

onMounted(() => {
    loadDocuments()
})
</script>

<style scoped>
.documents-container {
    background: white;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    padding-bottom: 20px;
    border-bottom: 2px solid #f0f0f0;
}

.page-header h1 {
    font-size: 28px;
    color: #333;
}

.header-actions {
    display: flex;
    gap: 15px;
    align-items: center;
}

.filter-input {
    padding: 10px 15px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 14px;
    width: 150px;
}

.filter-input:focus {
    outline: none;
    border-color: #667eea;
}

.upload-btn {
    padding: 10px 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: bold;
    cursor: pointer;
    transition: all 0.3s;
}

.upload-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.table-container {
    overflow-x: auto;
}

.documents-table {
    width: 100%;
    border-collapse: collapse;
}

.documents-table th,
.documents-table td {
    padding: 15px;
    text-align: left;
    border-bottom: 1px solid #f0f0f0;
}

.documents-table th {
    background: #f8f9fa;
    font-weight: bold;
    color: #333;
}

.documents-table tr:hover {
    background: #f8f9fa;
}

.status-badge {
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}

.status-badge.status-0 {
    background: #fff4e5;
    color: #ffa502;
}

.status-badge.status-1 {
    background: #e5ffe5;
    color: #2ed573;
}

.status-badge.status-2 {
    background: #ffe5e5;
    color: #ff4757;
}

.action-btn {
    padding: 6px 12px;
    margin-right: 8px;
    border: none;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.3s;
}

.action-btn.view {
    background: #e5f3ff;
    color: #3742fa;
}

.action-btn.download {
    background: #e5ffe5;
    color: #2ed573;
}

.action-btn.delete {
    background: #ffe5e5;
    color: #ff4757;
}

.action-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading,
.empty {
    text-align: center;
    padding: 40px;
    color: #999;
}

.pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
    margin-top: 20px;
    padding: 20px;
}

.page-btn {
    padding: 8px 16px;
    background: #f0f0f0;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.3s;
}

.page-btn:hover:not(:disabled) {
    background: #e0e0e0;
}

.page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.page-info {
    color: #666;
    font-size: 14px;
}

.modal-overlay {
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

.modal-content {
    background: white;
    border-radius: 12px;
    padding: 30px;
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
}

.detail-modal {
    max-width: 700px;
}

.modal-content h2 {
    margin-bottom: 20px;
    color: #333;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    color: #333;
    font-weight: 500;
}

.required {
    color: #ff4757;
}

.form-group input[type="file"] {
    width: 100%;
    padding: 10px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 14px;
}

.form-group input[type="number"],
.form-group input[type="text"] {
    width: 100%;
    padding: 10px;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    font-size: 14px;
}

.form-group input:focus {
    outline: none;
    border-color: #667eea;
}

.file-info {
    margin-top: 8px;
    padding: 8px;
    background: #f0f0f0;
    border-radius: 6px;
    font-size: 12px;
    color: #666;
}

.file-hint {
    margin-top: 8px;
    font-size: 12px;
    color: #999;
}

.detail-content {
    display: flex;
    flex-direction: column;
    gap: 15px;
}

.detail-item {
    display: flex;
    gap: 10px;
    padding: 10px;
    border-bottom: 1px solid #f0f0f0;
}

.detail-item label {
    font-weight: 500;
    color: #666;
    min-width: 100px;
}

.detail-item span {
    color: #333;
}

.log-content {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 6px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 200px;
    overflow-y: auto;
}

.modal-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 20px;
}

.btn-cancel,
.btn-submit {
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-cancel {
    background: #f0f0f0;
    color: #333;
}

.btn-submit {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}
</style>
