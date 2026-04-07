<template>
  <div class="submission-list-container">
    <a-page-header
      title="提交列表"
      :sub-title="assignmentTitle"
      @back="goBack"
    >
      <template #extra>
        <a-button :loading="analyzing" @click="handleAnalyze">
          预分析标准答案
        </a-button>
        <a-button type="primary" :loading="grading" @click="handleGradeAll">
          一键批量判题
        </a-button>
      </template>
    </a-page-header>

    <a-card :bordered="false">
      <!-- 判题结果摘要 -->
      <a-alert
        v-if="gradeResult"
        :type="gradeResult.error_count > 0 ? 'warning' : 'success'"
        show-icon
        closable
        style="margin-bottom: 16px"
      >
        <template #message>
          批量判题完成：共 {{ gradeResult.total }} 份，成功 {{ gradeResult.success_count }} 份
          <span v-if="gradeResult.error_count > 0">，失败 {{ gradeResult.error_count }} 份</span>
        </template>
      </a-alert>

      <a-table
        :columns="columns"
        :data-source="submissions"
        :loading="loading"
        row-key="id"
        :pagination="{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.submission_status)">
              {{ record.status_display }}
            </a-tag>
          </template>

          <template v-if="column.key === 'total_score'">
            <span v-if="record.submission_status === 2" class="score-text">
              {{ record.total_score }}
            </span>
            <span v-else style="color: #999">-</span>
          </template>

          <template v-if="column.key === 'submitted_at'">
            {{ formatDate(record.submitted_at) }}
          </template>

          <template v-if="column.key === 'graded_at'">
            {{ formatDate(record.graded_at) }}
          </template>

          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                v-if="record.has_grade"
                type="link"
                size="small"
                @click="goGradeReport(record)"
              >
                查看评分报告
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="openManualGrade(record)"
              >
                人工评分
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 人工评分对话框 -->
    <a-modal
      v-model:open="manualVisible"
      title="人工评分"
      :confirm-loading="manualLoading"
      @ok="handleManualSubmit"
      @cancel="handleManualCancel"
      ok-text="保存评分"
      cancel-text="取消"
    >
      <div v-if="currentRecord">
        <p>
          学生：<strong>{{ currentRecord.student_name }}</strong>
        </p>
        <p>
          当前总分：
          <strong>
            {{ currentRecord.total_score != null ? currentRecord.total_score : '-' }}
          </strong>
        </p>

        <a-form layout="vertical">
          <a-form-item label="新的总分" required>
            <a-input-number
              v-model:value="manualForm.total_score"
              :min="0"
              :max="assignmentTotalScore"
              :step="0.5"
              style="width: 100%"
            />
          </a-form-item>
          <a-form-item label="总体评语">
            <a-textarea
              v-model:value="manualForm.overall_comment"
              :rows="4"
              placeholder="可填写对本次作业的总体评价和建议（可选）"
            />
          </a-form-item>
        </a-form>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  getSubmissionList,
  analyzeStandardAnswers,
  gradeAllSubmissions,
  manualGradeSubmission,
} from '@/api/assignment'

const route = useRoute()
const router = useRouter()

const assignmentId = computed(() => route.params.id)
const assignmentTitle = ref('')
const assignmentTotalScore = ref(null)

const submissions = ref([])
const loading = ref(false)
const analyzing = ref(false)
const grading = ref(false)
const gradeResult = ref(null)

// 人工评分相关状态
const manualVisible = ref(false)
const manualLoading = ref(false)
const currentRecord = ref(null)
const manualForm = ref({
  total_score: null,
  overall_comment: '',
})

const columns = [
  { title: '学生ID', dataIndex: 'student_id', key: 'student_id', width: 80 },
  { title: '学生姓名', dataIndex: 'student_name', key: 'student_name' },
  { title: '状态', key: 'status', width: 120, align: 'center' },
  { title: '总分', key: 'total_score', width: 100, align: 'center' },
  { title: '提交时间', key: 'submitted_at', width: 180 },
  { title: '批改时间', key: 'graded_at', width: 180 },
  { title: '操作', key: 'action', width: 200 },
]

const statusColor = (status) => {
  const map = { 0: 'default', 1: 'processing', 2: 'success', 3: 'error' }
  return map[status] || 'default'
}

const loadSubmissions = async () => {
  loading.value = true
  try {
    const res = await getSubmissionList(assignmentId.value)
    if (res.success) {
      submissions.value = res.data || []
    } else {
      message.error(res.message || '加载失败')
    }
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

// 初始化时从路由 meta 或后续接口中获取作业总分（可选增强）
// 这里简单从第一个有成绩的记录中推断，如果后端列表加上 total_score 字段可以进一步完善

const handleAnalyze = async () => {
  analyzing.value = true
  message.loading({ content: '正在预分析标准答案...', key: 'analyze', duration: 0 })
  try {
    const res = await analyzeStandardAnswers(assignmentId.value)
    if (res.success) {
      message.success({ content: res.message || '预分析完成', key: 'analyze' })
    } else {
      message.error({ content: res.message || '预分析失败', key: 'analyze' })
    }
  } catch (e) {
    message.error({ content: e.message || '预分析失败', key: 'analyze' })
  } finally {
    analyzing.value = false
  }
}

const handleGradeAll = async () => {
  grading.value = true
  gradeResult.value = null
  message.loading({ content: '正在批量判题，请耐心等待...', key: 'grade', duration: 0 })
  try {
    const res = await gradeAllSubmissions(assignmentId.value)
    if (res.success) {
      message.success({ content: res.message || '判题完成', key: 'grade' })
      gradeResult.value = res.data
      await loadSubmissions()
    } else {
      message.error({ content: res.message || '判题失败', key: 'grade' })
    }
  } catch (e) {
    message.error({ content: e.message || '判题失败', key: 'grade' })
  } finally {
    grading.value = false
  }
}

const formatDate = (str) => {
  if (!str) return '-'
  return new Date(str).toLocaleString('zh-CN')
}

const goBack = () => router.back()
const goGradeReport = (record) => {
  router.push({
    name: 'GradeReport',
    params: { id: assignmentId.value },
    query: { submission_id: record.id },
  })
}

const openManualGrade = (record) => {
  currentRecord.value = record
  manualForm.value.total_score =
    record.total_score != null ? Number(record.total_score) : null
  manualForm.value.overall_comment = ''
  manualVisible.value = true
}

const handleManualCancel = () => {
  manualVisible.value = false
  currentRecord.value = null
}

const handleManualSubmit = async () => {
  if (!currentRecord.value) return
  const score = manualForm.value.total_score
  if (score === null || score === undefined || score === '') {
    message.warning('请填写新的总分')
    return
  }

  manualLoading.value = true
  try {
    const payload = {
      total_score: score,
      grading_rubric: [], // 前端暂不编辑细则，留空数组
      overall_comment: manualForm.value.overall_comment || '',
    }
    const res = await manualGradeSubmission(
      assignmentId.value,
      currentRecord.value.id,
      payload,
    )
    if (res.success) {
      message.success(res.message || '人工评分完成')
      manualVisible.value = false
      currentRecord.value = null
      await loadSubmissions()
    } else {
      message.error(res.message || '人工评分失败')
    }
  } catch (e) {
    message.error(e.message || '人工评分失败')
  } finally {
    manualLoading.value = false
  }
}

onMounted(loadSubmissions)
</script>

<style scoped>
.submission-list-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
.score-text {
  font-weight: 600;
  color: #1890ff;
  font-size: 16px;
}
</style>
