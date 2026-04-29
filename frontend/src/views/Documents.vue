<template>
    <div class="documents-container">
        <div class="page-header">
            <h1>文档管理</h1>
            <div class="header-actions">
                <template v-if="!selectedCourse">
                    <input
                        v-model="courseNameKeyword"
                        type="text"
                        placeholder="按课程名称筛选"
                        class="filter-input course-name-filter"
                    />
                </template>
                <template v-else>
                    <button @click="backToCourses" class="back-btn">返回课程列表</button>
                </template>
                <button @click="openUploadModal" class="upload-btn" v-if="!isStudent && selectedCourse">
                    + 上传文档
                </button>
            </div>
        </div>

        <!-- 课程卡片列表：先选择课程，再查看该课程文档 -->
        <div v-if="!selectedCourse" class="course-grid-container">
            <div v-if="coursesLoading" class="loading">课程加载中...</div>
            <div v-if="!coursesLoading && filteredCourses.length === 0" class="empty">暂无课程</div>

            <div v-if="!coursesLoading && filteredCourses.length > 0" class="course-grid">
                <div
                    v-for="course in filteredCourses"
                    :key="course.id"
                    class="course-card"
                    @click="selectCourse(course)"
                >
                    <div class="course-card-header">
                        <h3>{{ course.course_name }}</h3>
                        <span :class="['course-status', `course-status-${course.status}`]">
                            {{ course.status_display || (course.status === 1 ? '已发布' : '草稿') }}
                        </span>
                    </div>

                    <div class="course-card-body">
                        <div class="course-meta-line">
                            <span class="course-meta-label">课程老师：</span>
                            <span>{{ course.teacher_name || '-' }}</span>
                        </div>
                        <div class="course-meta-line" v-if="course.academic_year">
                            <span class="course-meta-label">学年：</span>
                            <span>{{ course.academic_year }}</span>
                        </div>
                        <div class="course-meta-line" v-if="course.semester_display">
                            <span class="course-meta-label">学期：</span>
                            <span>{{ course.semester_display }}</span>
                        </div>
                        <div class="course-meta-line" v-if="!isStudent">
                            <span class="course-meta-label">学生数：</span>
                            <span>{{ course.student_count || 0 }} / {{ course.max_students || '-' }}</span>
                        </div>
                        <div class="course-meta-line" v-if="!isStudent && course.invite_code">
                            <span class="course-meta-label">邀请码：</span>
                            <span class="invite-code">{{ course.invite_code }}</span>
                        </div>
                    </div>

                    <div v-if="course.course_description" class="course-card-desc">
                        {{ formatCourseDescription(course.course_description) }}
                    </div>

                    <div class="course-card-footer">
                        点击查看该课程文档
                    </div>
                </div>
            </div>
        </div>

        <div v-else class="table-container">
            <div class="selected-course-bar">
                <div>
                    <div class="selected-course-title">{{ selectedCourse.course_name }}</div>
                    <div class="selected-course-subtitle">
                        课程老师：{{ selectedCourse.teacher_name || '-' }}
                        <span v-if="selectedCourse.academic_year"> · {{ selectedCourse.academic_year }}</span>
                        <span v-if="selectedCourse.semester_display"> · {{ selectedCourse.semester_display }}</span>
                    </div>
                </div>
            </div>

            <table class="documents-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>文件名</th>
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
                        <label>所属课程</label>
                        <div class="readonly-course">
                            {{ selectedCourse?.course_name || '-' }}
                            <span>（课程老师：{{ selectedCourse?.teacher_name || '-' }}）</span>
                        </div>
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
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { getCourseList } from '@/api/course'
import {
    getDocumentList,
    uploadDocument,
    getDocumentDetail,
    deleteDocument
} from '@/api/document'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const isStudent = computed(() => authStore.isStudent)

const courses = ref([])
const coursesLoading = ref(false)
const selectedCourse = ref(null)
const courseNameKeyword = ref('')

const documents = ref([])
const loading = ref(false)
const uploading = ref(false)
const showUploadModal = ref(false)
const showDetailModal = ref(false)
const currentDocument = ref(null)
const selectedFile = ref(null)
const fileInput = ref(null)

const selectedCourseId = computed(() => selectedCourse.value?.id || null)

const filteredCourses = computed(() => {
    const keyword = courseNameKeyword.value.trim().toLowerCase()
    if (!keyword) return courses.value
    return courses.value.filter((course) =>
        (course.course_name || '').toLowerCase().includes(keyword)
    )
})

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const uploadForm = ref({
    course_id: '',
    file: null
})

const loadCourses = async () => {
    coursesLoading.value = true
    try {
        const response = await getCourseList({ mine: true, page_size: 100 })
        if (response.success) {
            courses.value = response.data || []
            const queryCourseId = route.query.course_id ? Number(route.query.course_id) : null
            if (queryCourseId) {
                const found = courses.value.find((course) => course.id === queryCourseId)
                if (found) {
                    await selectCourse(found, false)
                }
            }
        } else {
            alert(response.message || '加载课程列表失败')
        }
    } catch (error) {
        console.error('加载课程列表失败:', error)
        alert(error.message || '加载课程列表失败')
    } finally {
        coursesLoading.value = false
    }
}

const selectCourse = async (course, syncRoute = true) => {
    selectedCourse.value = course
    page.value = 1
    documents.value = []
    total.value = 0
    if (syncRoute) {
        router.replace({ name: route.name, query: { course_id: course.id } })
    }
    await loadDocuments()
}

const backToCourses = () => {
    selectedCourse.value = null
    documents.value = []
    total.value = 0
    page.value = 1
    router.replace({ name: route.name, query: {} })
}

const loadDocuments = async () => {
    if (!selectedCourseId.value) {
        documents.value = []
        total.value = 0
        return
    }

    loading.value = true
    try {
        const params = {
            page: page.value,
            page_size: pageSize.value,
            course_id: selectedCourseId.value
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

const formatCourseDescription = (text) => {
    if (!text) return ''
    return text.length > 90 ? `${text.slice(0, 90)}...` : text
}

const openUploadModal = () => {
    if (!selectedCourse.value) {
        alert('请先选择课程')
        return
    }
    uploadForm.value.course_id = selectedCourse.value.id
    showUploadModal.value = true
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
    if (!selectedCourseId.value || !uploadForm.value.file) {
        alert('请先选择课程并选择文件')
        return
    }

    uploading.value = true
    try {
        const formData = new FormData()
        formData.append('course_id', selectedCourseId.value)
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
        course_id: selectedCourseId.value || '',
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
    loadCourses()
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

.course-name-filter {
    width: 240px;
}

.filter-input:focus {
    outline: none;
    border-color: #2563eb;
}

.upload-btn {
    padding: 10px 20px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 0.2s, box-shadow 0.2s;
}

.upload-btn:hover {
    background: #1d4ed8;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
}

.back-btn {
    padding: 10px 18px;
    background: #f0f2f5;
    color: #333;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.3s;
}

.back-btn:hover {
    background: #e6e8eb;
    transform: translateY(-2px);
}

.course-grid-container {
    min-height: 240px;
}

.course-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 18px;
}

.course-card {
    border: 1px solid #f0f0f0;
    border-radius: 12px;
    padding: 18px;
    cursor: pointer;
    background: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    transition: all 0.25s;
}

.course-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 20px rgba(102, 126, 234, 0.16);
    border-color: #b7c3ff;
}

.course-card-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 14px;
}

.course-card-header h3 {
    margin: 0;
    font-size: 18px;
    color: #222;
    line-height: 1.4;
}

.course-status {
    flex-shrink: 0;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}

.course-status-1 {
    background: #e8f7ee;
    color: #2ed573;
}

.course-status-0 {
    background: #fff4e5;
    color: #ffa502;
}

.course-card-body {
    min-height: 118px;
}

.course-meta-line {
    margin-bottom: 8px;
    color: #444;
    font-size: 14px;
}

.course-meta-label {
    color: #888;
}

.invite-code {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 10px;
    background: #e5f3ff;
    color: #3742fa;
    font-size: 12px;
    font-weight: 600;
}

.course-card-desc {
    margin-top: 10px;
    padding: 10px 12px;
    background: #fafafa;
    border-radius: 8px;
    color: #666;
    line-height: 1.6;
    min-height: 50px;
}

.course-card-footer {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
    color: #2563eb;
    font-weight: 600;
    font-size: 13px;
}

.selected-course-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding: 14px 16px;
    background: #f6f8ff;
    border-left: 4px solid #2563eb;
    border-radius: 8px;
}

.selected-course-title {
    font-size: 18px;
    font-weight: 700;
    color: #222;
}

.selected-course-subtitle {
    margin-top: 4px;
    color: #666;
    font-size: 13px;
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

.readonly-course {
    padding: 10px 12px;
    background: #f6f8ff;
    border: 1px solid #dfe6ff;
    border-radius: 8px;
    color: #333;
    line-height: 1.6;
}

.readonly-course span {
    color: #666;
    font-size: 13px;
}

.form-group input:focus {
    outline: none;
    border-color: #2563eb;
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
    background: #2563eb;
    color: white;
}
</style>
