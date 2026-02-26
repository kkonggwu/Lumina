<template>
  <div class="course-detail-container">
    <div class="page-header">
      <button @click="goBack" class="back-btn">← 返回</button>
      <h1>课程详情</h1>
      <div class="header-actions" v-if="course">
        <button 
          v-if="!isStudent && (isAdmin || course.teacher_id === userInfo.id)" 
          @click="showEditModal = true" 
          class="action-btn edit"
        >
          编辑课程
        </button>
        <button 
          v-if="!isStudent && (isAdmin || course.teacher_id === userInfo.id)" 
          @click="confirmDelete" 
          class="action-btn delete"
        >
          删除课程
        </button>
        <button 
          v-if="isStudent && !isEnrolled" 
          @click="showJoinModal = true" 
          class="action-btn join"
        >
          加入课程
        </button>
        <button 
          v-if="isStudent && isEnrolled" 
          @click="confirmLeave" 
          class="action-btn leave"
        >
          退出课程
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    
    <div v-if="!loading && course" class="course-content">
      <!-- 课程基本信息 -->
      <div class="info-section">
        <h2>基本信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <label>课程名称:</label>
            <span>{{ course.course_name }}</span>
          </div>
          <div class="info-item">
            <label>教师:</label>
            <span>{{ course.teacher_name }}</span>
          </div>
          <div class="info-item">
            <label>邀请码:</label>
            <span class="invite-code">{{ course.invite_code }}</span>
          </div>
          <div class="info-item">
            <label>状态:</label>
            <span :class="['status-badge', `status-${course.status}`]">
              {{ course.status_display }}
            </span>
          </div>
          <div class="info-item" v-if="course.academic_year">
            <label>学年:</label>
            <span>{{ course.academic_year }}</span>
          </div>
          <div class="info-item" v-if="course.semester_display">
            <label>学期:</label>
            <span>{{ course.semester_display }}</span>
          </div>
          <div class="info-item">
            <label>学生数:</label>
            <span>{{ course.student_count || 0 }} / {{ course.max_students }}</span>
          </div>
          <div class="info-item">
            <label>类型:</label>
            <span v-if="course.is_public" class="public-badge">公开</span>
            <span v-else class="private-badge">私有</span>
          </div>
          <div class="info-item">
            <label>创建时间:</label>
            <span>{{ formatDate(course.created_at) }}</span>
          </div>
          <div class="info-item">
            <label>更新时间:</label>
            <span>{{ formatDate(course.updated_at) }}</span>
          </div>
        </div>
      </div>

      <!-- 课程描述 -->
      <div class="info-section" v-if="course.course_description">
        <h2>课程描述</h2>
        <div class="description-content">
          {{ course.course_description }}
        </div>
      </div>

      <!-- 封面图片 -->
      <div class="info-section" v-if="course.cover_image">
        <h2>封面图片</h2>
        <img :src="course.cover_image" alt="课程封面" class="cover-image" />
      </div>

      <!-- 学生列表（教师和管理员可见） -->
      <div class="info-section" v-if="!isStudent">
        <div class="section-header">
          <h2>学生列表</h2>
          <select v-model="studentFilter" class="filter-select" @change="loadStudents">
            <option value="">全部状态</option>
            <option value="0">待审核</option>
            <option value="1">已加入</option>
            <option value="2">已退出</option>
          </select>
        </div>
        <div class="students-table">
          <table>
            <thead>
              <tr>
                <th>学生ID</th>
                <th>学生姓名</th>
                <th>选课状态</th>
                <th>加入时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="student in students" :key="student.id">
                <td>{{ student.student_id }}</td>
                <td>{{ student.student_name }}</td>
                <td>
                  <span :class="['status-badge', `enrollment-${student.enrollment_status}`]">
                    {{ student.enrollment_status_display }}
                  </span>
                </td>
                <td>{{ formatDate(student.joined_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="students.length === 0" class="empty">暂无学生</div>
        </div>
      </div>

      <!-- 我的选课信息（学生可见） -->
      <div class="info-section" v-if="isStudent && enrollment">
        <h2>我的选课信息</h2>
        <div class="info-grid">
          <div class="info-item">
            <label>选课状态:</label>
            <span :class="['status-badge', `enrollment-${enrollment.enrollment_status}`]">
              {{ enrollment.enrollment_status_display }}
            </span>
          </div>
          <div class="info-item">
            <label>加入时间:</label>
            <span>{{ formatDate(enrollment.joined_at) }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="!loading && !course" class="empty">课程不存在</div>

    <!-- 编辑课程模态框 -->
    <div v-if="showEditModal" class="modal-overlay" @click="showEditModal = false">
      <div class="modal-content" @click.stop>
        <h2>编辑课程</h2>
        <form @submit.prevent="handleUpdate">
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
            <button type="button" @click="showEditModal = false" class="btn-cancel">取消</button>
            <button type="submit" :disabled="submitting" class="btn-submit">
              {{ submitting ? '更新中...' : '更新' }}
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
            <div v-if="course" class="hint">
              课程邀请码: <strong>{{ course.invite_code }}</strong>
            </div>
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
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  getCourseDetail,
  updateCourse,
  deleteCourse,
  joinCourse,
  leaveCourse,
  getCourseStudents,
  getStudentCourses
} from '@/api/course'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isStudent = computed(() => authStore.isStudent)
const isAdmin = computed(() => authStore.isAdmin)
const userInfo = computed(() => authStore.userInfo)

const course = ref(null)
const students = ref([])
const enrollment = ref(null)
const loading = ref(false)
const joining = ref(false)
const leaving = ref(false)
const showJoinModal = ref(false)
const showEditModal = ref(false)
const submitting = ref(false)
const studentFilter = ref('')

const joinForm = ref({
  invite_code: ''
})

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

const isEnrolled = computed(() => {
  return enrollment.value && enrollment.value.enrollment_status === 1
})

const courseId = computed(() => parseInt(route.params.id))

const loadCourseDetail = async () => {
  loading.value = true
  try {
    const response = await getCourseDetail(courseId.value)
    if (response.success) {
      course.value = response.data
      // 如果是学生，加载选课信息
      if (isStudent.value) {
        await loadEnrollment()
      } else {
        // 如果是教师或管理员，加载学生列表
        await loadStudents()
      }
    } else {
      alert(response.message || '加载课程详情失败')
    }
  } catch (error) {
    console.error('加载课程详情失败:', error)
    alert(error.message || '加载课程详情失败')
  } finally {
    loading.value = false
  }
}

const loadStudents = async () => {
  if (isStudent.value) return
  
  try {
    const params = {
      page: 1,
      page_size: 100
    }
    if (studentFilter.value !== '') {
      params.enrollment_status = parseInt(studentFilter.value)
    }
    
    const response = await getCourseStudents(courseId.value, params)
    if (response.success) {
      students.value = response.data || []
    }
  } catch (error) {
    console.error('加载学生列表失败:', error)
  }
}

const loadEnrollment = async () => {
  if (!isStudent.value) return
  
  try {
    const response = await getStudentCourses({
      page: 1,
      page_size: 100
    })
    if (response.success) {
      const enrollments = response.data || []
      enrollment.value = enrollments.find(e => e.course_id === courseId.value)
    }
  } catch (error) {
    console.error('加载选课信息失败:', error)
  }
}

const editCourse = () => {
  if (course.value) {
    courseForm.value = {
      course_name: course.value.course_name || '',
      course_description: course.value.course_description || '',
      cover_image: course.value.cover_image || '',
      academic_year: course.value.academic_year || '',
      semester: course.value.semester || null,
      max_students: course.value.max_students || 100,
      is_public: course.value.is_public || false,
      status: course.value.status !== undefined ? course.value.status : 1
    }
    showEditModal.value = true
  }
}

const handleUpdate = async () => {
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

    const response = await updateCourse(courseId.value, data)
    if (response.success) {
      alert('更新成功')
      showEditModal.value = false
      await loadCourseDetail()
    } else {
      alert(response.message || '更新失败')
    }
  } catch (error) {
    console.error('更新失败:', error)
    alert(error.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

const confirmDelete = () => {
  if (confirm(`确定要删除课程 "${course.value.course_name}" 吗？此操作不可恢复。`)) {
    handleDelete()
  }
}

const handleDelete = async () => {
  try {
    const response = await deleteCourse(courseId.value)
    if (response.success) {
      alert('删除成功')
      router.push('/courses')
    } else {
      alert(response.message || '删除失败')
    }
  } catch (error) {
    console.error('删除失败:', error)
    alert(error.message || '删除失败')
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
      await loadCourseDetail()
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

const confirmLeave = () => {
  if (confirm(`确定要退出课程 "${course.value.course_name}" 吗？`)) {
    handleLeave()
  }
}

const handleLeave = async () => {
  leaving.value = true
  try {
    const response = await leaveCourse(courseId.value)
    if (response.success) {
      alert('成功退出课程')
      await loadCourseDetail()
    } else {
      alert(response.message || '退出失败')
    }
  } catch (error) {
    console.error('退出失败:', error)
    alert(error.message || '退出失败')
  } finally {
    leaving.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const goBack = () => {
  router.push('/courses')
}

onMounted(() => {
  loadCourseDetail()
})
</script>

<style scoped>
.course-detail-container {
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

.back-btn {
  padding: 8px 16px;
  background: #f0f0f0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.back-btn:hover {
  background: #e0e0e0;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn.edit {
  background: #fff4e5;
  color: #ffa502;
}

.action-btn.delete {
  background: #ffe5e5;
  color: #ff4757;
}

.action-btn.join {
  background: #e5ffe5;
  color: #2ed573;
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

.course-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.info-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 20px;
}

.info-section h2 {
  font-size: 20px;
  color: #333;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e0e0e0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #e0e0e0;
}

.section-header h2 {
  margin: 0;
  border: none;
  padding: 0;
}

.filter-select {
  padding: 8px 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-item label {
  font-weight: 500;
  color: #666;
  font-size: 14px;
}

.info-item span {
  color: #333;
  font-size: 16px;
}

.invite-code {
  font-family: monospace;
  background: #fff;
  padding: 4px 12px;
  border-radius: 6px;
  font-weight: bold;
  color: #667eea;
  display: inline-block;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  display: inline-block;
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

.public-badge,
.private-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  display: inline-block;
}

.public-badge {
  background: #e5f3ff;
  color: #3742fa;
}

.private-badge {
  background: #f0f0f0;
  color: #666;
}

.description-content {
  color: #333;
  font-size: 16px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.cover-image {
  max-width: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.students-table {
  overflow-x: auto;
}

.students-table table {
  width: 100%;
  border-collapse: collapse;
}

.students-table th,
.students-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.students-table th {
  background: #fff;
  font-weight: bold;
  color: #333;
}

.students-table tr:hover {
  background: #f8f9fa;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.hint {
  margin-top: 8px;
  padding: 8px;
  background: #f0f0f0;
  border-radius: 6px;
  font-size: 12px;
  color: #666;
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

