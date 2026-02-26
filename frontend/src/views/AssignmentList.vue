<template>
  <div class="assignment-list-container">
    <a-page-header
      title="作业管理"
      :sub-title="selectedCourseName || '全部作业'"
    >
      <template #extra>
        <a-select
          v-model:value="selectedCourseId"
          placeholder="按课程筛选"
          allow-clear
          show-search
          option-filter-prop="label"
          style="width: 240px; margin-right: 12px"
          :options="courseOptions"
          @change="onCourseChange"
        />
        <a-button v-if="!isStudent" type="primary" @click="goCreate">
          <template #icon><plus-outlined /></template>
          创建作业
        </a-button>
      </template>
    </a-page-header>

    <a-card :bordered="false">
      <a-table
        :columns="columns"
        :data-source="assignments"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'title'">
            <a @click="goDetail(record.id)">{{ record.title }}</a>
          </template>

          <template v-if="column.key === 'status'">
            <a-tag :color="record.assignment_status === 1 ? 'green' : 'orange'">
              {{ record.status_display }}
            </a-tag>
          </template>

          <template v-if="column.key === 'end_time'">
            {{ formatDate(record.end_time) }}
          </template>

          <template v-if="column.key === 'action'">
            <a-space v-if="!isStudent" wrap>
              <a-button size="small" @click="goDetail(record.id)">查看</a-button>
              <a-button
                v-if="record.assignment_status === 0"
                size="small"
                type="primary"
                ghost
                @click="goEdit(record.id)"
              >编辑</a-button>
              <a-popconfirm
                v-if="record.assignment_status === 0"
                title="确定发布该作业？发布后不可修改。"
                @confirm="handlePublish(record.id)"
              >
                <a-button size="small" type="primary">发布</a-button>
              </a-popconfirm>
              <a-button
                size="small"
                :loading="analyzingId === record.id"
                @click="handleAnalyze(record.id)"
              >分析</a-button>
              <a-button
                v-if="record.assignment_status === 1"
                size="small"
                @click="goSubmissions(record.id)"
              >提交列表</a-button>
              <a-popconfirm
                title="确定删除该作业？"
                @confirm="handleDelete(record.id)"
              >
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
            <a-space v-else>
              <a-button size="small" type="primary" @click="goDetail(record.id)">
                {{ record.assignment_status === 1 ? '去答题' : '查看' }}
              </a-button>
              <a-button size="small" @click="goMyReport(record.id)">查看成绩</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import {
  getAssignmentList,
  deleteAssignment,
  publishAssignment,
  analyzeStandardAnswers,
} from '@/api/assignment'
import { getCourseList } from '@/api/course'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isStudent = computed(() => authStore.isStudent)

const assignments = ref([])
const loading = ref(false)
const analyzingId = ref(null)

const courseOptions = ref([])
const selectedCourseId = ref(route.query.course_id ? Number(route.query.course_id) : undefined)

const selectedCourseName = computed(() => {
  if (!selectedCourseId.value) return ''
  const found = courseOptions.value.find((c) => c.value === selectedCourseId.value)
  return found ? `课程：${found.label}` : ''
})

const columns = computed(() => {
  const base = [
    { title: '标题', key: 'title', dataIndex: 'title' },
    { title: '课程', dataIndex: 'course_name', key: 'course_name' },
    { title: '题目数', dataIndex: 'question_count', key: 'question_count', width: 80, align: 'center' },
    { title: '总分', dataIndex: 'total_score', key: 'total_score', width: 80, align: 'center' },
    { title: '状态', key: 'status', width: 100, align: 'center' },
    { title: '截止时间', key: 'end_time', width: 180 },
  ]
  if (!isStudent.value) {
    base.push({ title: '提交数', dataIndex: 'submission_count', key: 'submission_count', width: 80, align: 'center' })
  }
  base.push({ title: '操作', key: 'action', width: 320 })
  return base
})

const loadCourses = async () => {
  try {
    const res = await getCourseList()
    if (res.success) {
      courseOptions.value = (res.data || []).map((c) => ({
        value: c.id,
        label: c.course_name,
      }))
    }
  } catch {
    // silent
  }
}

const loadAssignments = async () => {
  loading.value = true
  try {
    const params = {}
    if (selectedCourseId.value) params.course_id = selectedCourseId.value
    const res = await getAssignmentList(params)
    if (res.success) {
      assignments.value = res.data || []
    } else {
      message.error(res.message || '加载失败')
    }
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const onCourseChange = () => {
  loadAssignments()
}

const handlePublish = async (id) => {
  try {
    const res = await publishAssignment(id)
    if (res.success) {
      message.success('发布成功')
      await loadAssignments()
    } else {
      message.error(res.message || '发布失败')
    }
  } catch (e) {
    message.error(e.message || '发布失败')
  }
}

const handleDelete = async (id) => {
  try {
    const res = await deleteAssignment(id)
    if (res.success) {
      message.success('删除成功')
      await loadAssignments()
    } else {
      message.error(res.message || '删除失败')
    }
  } catch (e) {
    message.error(e.message || '删除失败')
  }
}

const handleAnalyze = async (id) => {
  analyzingId.value = id
  message.loading({ content: '正在预分析标准答案，请稍候...', key: 'analyze', duration: 0 })
  try {
    const res = await analyzeStandardAnswers(id)
    if (res.success) {
      message.success({ content: res.message || '预分析完成', key: 'analyze' })
      await loadAssignments()
    } else {
      message.error({ content: res.message || '预分析失败', key: 'analyze' })
    }
  } catch (e) {
    message.error({ content: e.message || '预分析失败', key: 'analyze' })
  } finally {
    analyzingId.value = null
  }
}

const formatDate = (str) => {
  if (!str) return '-'
  return new Date(str).toLocaleString('zh-CN')
}

const goCreate = () => {
  const query = selectedCourseId.value ? { course_id: selectedCourseId.value } : {}
  router.push({ name: 'AssignmentCreate', query })
}
const goDetail = (id) => router.push({ name: 'AssignmentDetail', params: { id } })
const goEdit = (id) => router.push({ name: 'AssignmentEdit', params: { id } })
const goSubmissions = (id) => router.push({ name: 'SubmissionList', params: { id } })
const goMyReport = (id) => router.push({ name: 'GradeReport', params: { id } })

onMounted(async () => {
  await loadCourses()
  await loadAssignments()
})
</script>

<style scoped>
.assignment-list-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
</style>
