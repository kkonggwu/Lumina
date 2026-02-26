<template>
  <div class="courses-container">
    <div class="page-header">
      <h1>📖 课程管理</h1>
      <div class="header-actions">
        <!-- 筛选条件 -->
        <div class="filters">
          <!-- 教师和管理员的筛选条件 -->
          <template v-if="!isStudent">
            <input 
              v-model="filters.teacher_id" 
              type="number" 
              placeholder="教师ID" 
              class="filter-input"
              @input="loadCourses"
            />
            <select v-model="filters.status" class="filter-select" @change="loadCourses">
              <option value="">全部状态</option>
              <option value="0">草稿</option>
              <option value="1">已发布</option>
            </select>
            <select v-model="filters.is_public" class="filter-select" @change="loadCourses">
              <option value="">全部类型</option>
              <option value="true">公开</option>
              <option value="false">私有</option>
            </select>
          </template>
          <!-- 学生的筛选条件 -->
          <template v-else>
            <select v-model="filters.enrollment_status" class="filter-select" @change="loadCourses">
              <option value="1">已加入</option>
              <option value="0">待审核</option>
              <option value="2">已退出</option>
              <option value="">全部状态</option>
            </select>
          </template>
        </div>
        <!-- 创建课程按钮（仅教师和管理员） -->
        <button 
          v-if="!isStudent" 
          @click="showCreateModal = true" 
          class="create-btn"
        >
          + 创建课程
        </button>
        <!-- 加入课程按钮（仅学生） -->
        <button 
          v-if="isStudent" 
          @click="showJoinModal = true" 
          class="join-btn"
        >
          + 加入课程
        </button>
      </div>
    </div>

    <!-- 课程列表 -->
    <div class="courses-grid" v-if="!loading && courses.length > 0">
      <div 
        v-for="course in courses" 
        :key="course.id" 
        class="course-card"
        @click="viewCourseDetail(course.id)"
      >
        <div class="course-header">
          <h3 class="course-title">{{ course.course_name }}</h3>
          <div class="course-badges">
            <span :class="['status-badge', `status-${course.status}`]">
              {{ course.status_display }}
            </span>
            <span v-if="course.is_public" class="public-badge">公开</span>
            <span v-else class="private-badge">私有</span>
          </div>
        </div>
        
        <div class="course-info">
          <div class="info-item">
            <span class="label">教师:</span>
            <span class="value">{{ course.teacher_name }}</span>
          </div>
          <div class="info-item" v-if="course.academic_year">
            <span class="label">学年:</span>
            <span class="value">{{ course.academic_year }}</span>
          </div>
          <div class="info-item" v-if="course.semester_display">
            <span class="label">学期:</span>
            <span class="value">{{ course.semester_display }}</span>
          </div>
          <div class="info-item" v-if="!isStudent">
            <span class="label">学生数:</span>
            <span class="value">{{ course.student_count || 0 }} / {{ course.max_students }}</span>
          </div>
          <div class="info-item" v-if="isStudent && course.enrollment_status_display">
            <span class="label">选课状态:</span>
            <span :class="['status-badge', `enrollment-${course.enrollment_status}`]">
              {{ course.enrollment_status_display }}
            </span>
          </div>
          <div class="info-item" v-if="isStudent && course.joined_at">
            <span class="label">加入时间:</span>
            <span class="value">{{ formatDate(course.joined_at) }}</span>
          </div>
          <div class="info-item" v-if="!isStudent && course.invite_code">
            <span class="label">邀请码:</span>
            <span class="value invite-code">{{ course.invite_code }}</span>
          </div>
        </div>

        <div class="course-description" v-if="course.course_description">
          {{ course.course_description.length > 100 
            ? course.course_description.substring(0, 100) + '...' 
            : course.course_description }}
        </div>

        <div class="course-actions">
          <button 
            @click.stop="viewCourseDetail(course.id)" 
            class="action-btn view"
          >
            查看详情
          </button>
          <button 
            v-if="!isStudent && course.teacher_id && (isAdmin || course.teacher_id === userInfo.id)" 
            @click.stop="editCourse(course)" 
            class="action-btn edit"
          >
            编辑
          </button>
          <button 
            v-if="!isStudent && course.teacher_id && (isAdmin || course.teacher_id === userInfo.id)" 
            @click.stop="confirmDelete(course)" 
            class="action-btn delete"
          >
            删除
          </button>
          <button 
            v-if="isStudent && course.enrollment_status === 1" 
            @click.stop="confirmLeave(course)" 
            class="action-btn leave"
          >
            退出课程
          </button>
          <button 
            v-if="isStudent && course.enrollment_status === 2" 
            @click.stop="viewCourseDetail(course.id)" 
            class="action-btn view"
          >
            重新加入
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="!loading && courses.length === 0" class="empty">暂无课程</div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination">
      <button 
        @click="changePage(page - 1)" 
        :disabled="page <= 1" 
        class="page-btn"
      >
        上一页
      </button>
      <span class="page-info">
        第 {{ page }} 页，共 {{ Math.ceil(total / pageSize) }} 页，共 {{ total }} 条
      </span>
      <button 
        @click="changePage(page + 1)" 
        :disabled="page >= Math.ceil(total / pageSize)" 
        class="page-btn"
      >
        下一页
      </button>
    </div>

    <!-- 创建课程模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-content" @click.stop>
        <h2>{{ editingCourse ? '编辑课程' : '创建课程' }}</h2>
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label>课程名称 <span class="required">*</span></label>
            <input 
              v-model="courseForm.course_name" 
              type="text" 
              required 
              maxlength="100"
              placeholder="请输入课程名称"
            />
          </div>
          <div class="form-group">
            <label>课程描述</label>
            <textarea 
              v-model="courseForm.course_description" 
              rows="4"
              placeholder="请输入课程描述"
            ></textarea>
          </div>
          <div class="form-group">
            <label>封面图片URL</label>
            <input 
              v-model="courseForm.cover_image" 
              type="text"
              placeholder="请输入封面图片URL"
            />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>学年</label>
              <input 
                v-model="courseForm.academic_year" 
                type="text"
                placeholder="如：2024-2025"
              />
            </div>
            <div class="form-group">
              <label>学期</label>
              <select v-model="courseForm.semester">
                <option :value="null">请选择</option>
                <option :value="1">春季</option>
                <option :value="2">秋季</option>
              </select>
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>最大学生数</label>
              <input 
                v-model.number="courseForm.max_students" 
                type="number" 
                min="1"
                placeholder="默认100"
              />
            </div>
            <div class="form-group">
              <label>状态</label>
              <select v-model.number="courseForm.status">
                <option :value="0">草稿</option>
                <option :value="1">已发布</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label>
              <input 
                type="checkbox" 
                v-model="courseForm.is_public"
              />
              是否公开
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeCreateModal" class="btn-cancel">取消</button>
            <button type="submit" :disabled="submitting" class="btn-submit">
              {{ submitting ? '提交中...' : (editingCourse ? '更新' : '创建') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 加入课程模态框 -->
    <div v-if="showJoinModal" class="modal-overlay" @click="showJoinModal = false">
      <div class="modal-content" @click.stop>
        <h2>加入课程</h2>
        <form @submit.prevent="handleJoin">
          <div class="form-group">
            <label>课程邀请码 <span class="required">*</span></label>
            <input 
              v-model="joinForm.invite_code" 
              type="text" 
              required 
              placeholder="请输入课程邀请码"
              style="text-transform: uppercase;"
            />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showJoinModal = false" class="btn-cancel">取消</button>
            <button type="submit" :disabled="joining" class="btn-submit">
              {{ joining ? '加入中...' : '加入课程' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  getCourseList,
  createCourse,
  updateCourse,
  deleteCourse,
  joinCourse,
  getStudentCourses,
  leaveCourse
} from '@/api/course'

const router = useRouter()
const authStore = useAuthStore()

const isStudent = computed(() => authStore.isStudent)
const isAdmin = computed(() => authStore.isAdmin)
const userInfo = computed(() => authStore.userInfo)

const courses = ref([])
const loading = ref(false)
const submitting = ref(false)
const joining = ref(false)
const showCreateModal = ref(false)
const showJoinModal = ref(false)
const editingCourse = ref(null)

const filters = ref({
  teacher_id: '',
  status: '',
  is_public: '',
  enrollment_status: '' // 学生选课状态筛选
})

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const courseForm = ref({
  course_name: '',
  course_description: '',
  cover_image: '',
  academic_year: '',
  semester: null,
  max_students: 100,
  is_public: false,
  status: 1
})

const joinForm = ref({
  invite_code: ''
})

const loadCourses = async () => {
  loading.value = true
  try {
    // 如果是学生，调用学生选课列表接口
    if (isStudent.value) {
      const params = {
        page: page.value,
        page_size: pageSize.value
      }
      
      // 默认只显示已加入的课程（enrollment_status = 1）
      if (filters.value.enrollment_status !== '') {
        params.enrollment_status = parseInt(filters.value.enrollment_status)
      } else {
        params.enrollment_status = 1 // 默认只显示已加入的课程
      }

      const response = await getStudentCourses(params)
      if (response.success) {
        // 将选课记录转换为课程信息格式
        const enrollments = response.data || []
        courses.value = enrollments.map(enrollment => ({
          id: enrollment.course_id,
          course_name: enrollment.course_name,
          teacher_name: enrollment.teacher_name,
          teacher_id: null, // 选课记录中没有teacher_id
          course_description: null,
          cover_image: null,
          invite_code: null,
          academic_year: null,
          semester: null,
          semester_display: null,
          max_students: null,
          is_public: null,
          status: null,
          status_display: null,
          student_count: null,
          created_at: null,
          updated_at: null,
          // 选课相关信息
          enrollment_id: enrollment.id,
          enrollment_status: enrollment.enrollment_status,
          enrollment_status_display: enrollment.enrollment_status_display,
          joined_at: enrollment.joined_at
        }))
        total.value = response.total || 0
      } else {
        alert(response.message || '加载选课列表失败')
      }
    } else {
      // 教师和管理员，调用课程列表接口
      const params = {
        page: page.value,
        page_size: pageSize.value
      }
      
      if (filters.value.teacher_id) {
        params.teacher_id = parseInt(filters.value.teacher_id)
      }
      if (filters.value.status !== '') {
        params.status = parseInt(filters.value.status)
      }
      if (filters.value.is_public !== '') {
        params.is_public = filters.value.is_public === 'true'
      }

      const response = await getCourseList(params)
      if (response.success) {
        courses.value = response.data || []
        total.value = response.total || 0
      } else {
        alert(response.message || '加载课程列表失败')
      }
    }
  } catch (error) {
    console.error('加载课程列表失败:', error)
    alert(error.message || '加载课程列表失败')
  } finally {
    loading.value = false
  }
}

const viewCourseDetail = (courseId) => {
  router.push(`/courses/${courseId}`)
}

const editCourse = (course) => {
  editingCourse.value = course
  courseForm.value = {
    course_name: course.course_name || '',
    course_description: course.course_description || '',
    cover_image: course.cover_image || '',
    academic_year: course.academic_year || '',
    semester: course.semester || null,
    max_students: course.max_students || 100,
    is_public: course.is_public || false,
    status: course.status !== undefined ? course.status : 1
  }
  showCreateModal.value = true
}

const confirmDelete = (course) => {
  if (confirm(`确定要删除课程 "${course.course_name}" 吗？此操作不可恢复。`)) {
    handleDelete(course.id)
  }
}

const handleDelete = async (courseId) => {
  try {
    const response = await deleteCourse(courseId)
    if (response.success) {
      alert('删除成功')
      loadCourses()
    } else {
      alert(response.message || '删除失败')
    }
  } catch (error) {
    console.error('删除失败:', error)
    alert(error.message || '删除失败')
  }
}

const handleSubmit = async () => {
  if (!courseForm.value.course_name.trim()) {
    alert('请输入课程名称')
    return
  }

  submitting.value = true
  try {
    const data = { ...courseForm.value }
    // 清理空值
    if (!data.academic_year) delete data.academic_year
    if (data.semester === null) delete data.semester
    if (!data.cover_image) delete data.cover_image
    if (!data.course_description) delete data.course_description

    let response
    if (editingCourse.value) {
      response = await updateCourse(editingCourse.value.id, data)
    } else {
      response = await createCourse(data)
    }

    if (response.success) {
      alert(editingCourse.value ? '更新成功' : '创建成功')
      closeCreateModal()
      loadCourses()
    } else {
      alert(response.message || '操作失败')
    }
  } catch (error) {
    console.error('操作失败:', error)
    alert(error.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleJoin = async () => {
  if (!joinForm.value.invite_code.trim()) {
    alert('请输入课程邀请码')
    return
  }

  joining.value = true
  try {
    const response = await joinCourse({
      invite_code: joinForm.value.invite_code.toUpperCase()
    })
    if (response.success) {
      alert('成功加入课程')
      showJoinModal.value = false
      joinForm.value.invite_code = ''
      // 如果是学生，可以刷新选课列表
      loadCourses()
    } else {
      alert(response.message || '加入失败')
    }
  } catch (error) {
    console.error('加入失败:', error)
    alert(error.message || '加入失败')
  } finally {
    joining.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const closeCreateModal = () => {
  showCreateModal.value = false
  editingCourse.value = null
  courseForm.value = {
    course_name: '',
    course_description: '',
    cover_image: '',
    academic_year: '',
    semester: null,
    max_students: 100,
    is_public: false,
    status: 1
  }
}

const confirmLeave = (course) => {
  if (confirm(`确定要退出课程 "${course.course_name}" 吗？`)) {
    handleLeave(course.id)
  }
}

const handleLeave = async (courseId) => {
  try {
    const response = await leaveCourse(courseId)
    if (response.success) {
      alert('成功退出课程')
      loadCourses()
    } else {
      alert(response.message || '退出失败')
    }
  } catch (error) {
    console.error('退出失败:', error)
    alert(error.message || '退出失败')
  }
}

const changePage = (newPage) => {
  if (newPage >= 1 && newPage <= Math.ceil(total.value / pageSize.value)) {
    page.value = newPage
    loadCourses()
  }
}

onMounted(() => {
  loadCourses()
})
</script>

<style scoped>
.courses-container {
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
  flex-wrap: wrap;
  gap: 15px;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
}

.filters {
  display: flex;
  gap: 10px;
  align-items: center;
}

.filter-input,
.filter-select {
  padding: 10px 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.filter-input {
  width: 120px;
}

.filter-select {
  width: 120px;
}

.filter-input:focus,
.filter-select:focus {
  outline: none;
  border-color: #667eea;
}

.create-btn,
.join-btn {
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

.create-btn:hover,
.join-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
}

.courses-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.course-card {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.course-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
  border-color: #667eea;
}

.course-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.course-title {
  font-size: 20px;
  color: #333;
  margin: 0;
  flex: 1;
}

.course-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
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

.status-badge.enrollment-0 {
  background: #fff4e5;
  color: #ffa502;
}

.status-badge.enrollment-1 {
  background: #e5ffe5;
  color: #2ed573;
}

.status-badge.enrollment-2 {
  background: #ffe5e5;
  color: #ff4757;
}

.public-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  background: #e5f3ff;
  color: #3742fa;
}

.private-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  background: #f0f0f0;
  color: #666;
}

.course-info {
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
}

.info-item .label {
  color: #666;
  font-weight: 500;
}

.info-item .value {
  color: #333;
}

.invite-code {
  font-family: monospace;
  background: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: bold;
  color: #667eea;
}

.course-description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 15px;
  max-height: 60px;
  overflow: hidden;
}

.course-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 6px 12px;
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

.action-btn.edit {
  background: #fff4e5;
  color: #ffa502;
}

.action-btn.delete {
  background: #ffe5e5;
  color: #ff4757;
}

.action-btn.leave {
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
  max-width: 600px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-bottom: 20px;
  color: #333;
}

.form-group {
  margin-bottom: 20px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
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

.form-group input[type="text"],
.form-group input[type="number"],
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input[type="checkbox"] {
  margin-right: 8px;
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

.btn-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>


