<template>
  <div class="assignment-detail-container">
    <a-page-header
      :title="assignment?.title || '作业详情'"
      @back="goBack"
    >
      <template #tags>
        <a-tag :color="assignment?.assignment_status === 1 ? 'green' : 'orange'">
          {{ assignment?.status_display || '' }}
        </a-tag>
      </template>
      <template #extra v-if="assignment">
        <!-- 教师/管理员操作 -->
        <template v-if="!isStudent">
          <a-button
            v-if="assignment.assignment_status === 0"
            @click="goEdit"
          >编辑</a-button>
          <a-popconfirm
            v-if="assignment.assignment_status === 0"
            title="发布后不可修改，确定发布？"
            @confirm="handlePublish"
          >
            <a-button type="primary">发布作业</a-button>
          </a-popconfirm>
          <a-button
            :loading="analyzing"
            @click="handleAnalyze"
          >预分析标准答案</a-button>
          <a-button
            v-if="assignment.assignment_status === 1"
            type="primary"
            :loading="grading"
            @click="handleGradeAll"
          >批量判题</a-button>
          <a-button
            v-if="assignment.assignment_status === 1"
            @click="goSubmissions"
          >查看提交</a-button>
        </template>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <template v-if="assignment">
        <!-- 作业基本信息 -->
        <a-card :bordered="false" class="info-card">
          <a-descriptions :column="{ xs: 1, sm: 2, md: 3 }">
            <a-descriptions-item label="课程">{{ assignment.course_name }}</a-descriptions-item>
            <a-descriptions-item label="教师">{{ assignment.teacher_name }}</a-descriptions-item>
            <a-descriptions-item label="总分">{{ assignment.total_score }}</a-descriptions-item>
            <a-descriptions-item label="开始时间">{{ formatDate(assignment.start_time) }}</a-descriptions-item>
            <a-descriptions-item label="截止时间">{{ formatDate(assignment.end_time) }}</a-descriptions-item>
            <a-descriptions-item label="题目数">{{ questions.length }}</a-descriptions-item>
          </a-descriptions>
          <div v-if="assignment.description" style="margin-top: 12px; color: #666">
            {{ assignment.description }}
          </div>
        </a-card>

        <!-- 教师视角：题目展示（含标准答案 + 关键点编辑） -->
        <template v-if="!isStudent">
          <a-card title="题目列表" :bordered="false" style="margin-top: 16px">
            <a-collapse>
              <a-collapse-panel
                v-for="(q, index) in questions"
                :key="q.id"
                :header="`第 ${index + 1} 题（${q.score} 分）`"
              >
                <a-descriptions :column="1" bordered size="small">
                  <a-descriptions-item label="题目内容">
                    <div style="white-space: pre-wrap">{{ q.content }}</div>
                  </a-descriptions-item>
                  <a-descriptions-item label="标准答案">
                    <div style="white-space: pre-wrap">{{ q.standard_answer || '未设置' }}</div>
                  </a-descriptions-item>
                  <a-descriptions-item label="分析状态">
                    <a-tag :color="q.analyzed ? 'green' : 'default'">
                      {{ q.analyzed ? '已分析' : '未分析' }}
                    </a-tag>
                    <span v-if="q.analyzed && q.answer_keypoints?.length" style="margin-left: 8px; color: #999">
                      {{ q.answer_keypoints.length }} 个关键点
                    </span>
                  </a-descriptions-item>
                  <a-descriptions-item v-if="q.analyzed && q.answer_keypoints?.length" label="关键点">
                    <a-tag
                      v-for="(kp, ki) in q.answer_keypoints"
                      :key="ki"
                      color="blue"
                      style="margin-bottom: 4px"
                    >{{ typeof kp === 'string' ? kp : kp.point || kp.description || JSON.stringify(kp) }}</a-tag>
                  </a-descriptions-item>
                  <a-descriptions-item label="操作">
                    <a-button type="link" size="small" @click="openEditKeypoints(q)">
                      编辑关键点
                    </a-button>
                  </a-descriptions-item>
                </a-descriptions>
              </a-collapse-panel>
            </a-collapse>
          </a-card>

          <!-- 编辑关键点弹窗 -->
          <a-modal
            v-model:open="editKpVisible"
            title="编辑标准答案关键点"
            ok-text="保存"
            cancel-text="取消"
            :confirm-loading="savingKp"
            @ok="handleSaveKeypoints"
          >
            <div v-if="currentQuestion">
              <p>
                题目：<strong>{{ currentQuestion.content }}</strong>
              </p>
              <p style="margin: 8px 0; color: #999">
                提示：每一行代表一个关键点，回车换行即可新增/删除关键点。
              </p>
              <a-textarea
                v-model:value="keypointsText"
                :rows="8"
                placeholder="每行一个关键点"
              />
            </div>
          </a-modal>
        </template>

        <!-- 学生视角：答题 -->
        <template v-if="isStudent">
          <!-- 已批改，显示入口 -->
          <a-alert
            v-if="mySubmission && mySubmission.submission_status === 2"
            type="success"
            show-icon
            style="margin-top: 16px"
          >
            <template #message>
              作业已批改，得分：{{ mySubmission.total_score }} / {{ assignment.total_score }}
              <a-button type="link" @click="goMyReport">查看评分报告</a-button>
            </template>
          </a-alert>

          <a-alert
            v-if="mySubmission && mySubmission.submission_status === 1"
            type="info"
            show-icon
            message="答案已提交，等待批改中..."
            style="margin-top: 16px"
          />

          <a-card title="答题区" :bordered="false" style="margin-top: 16px">
            <div v-for="(q, index) in questions" :key="q.id" class="student-question">
              <h4>第 {{ index + 1 }} 题（{{ q.score }} 分）</h4>
              <div class="question-content">{{ q.content }}</div>
              <a-textarea
                v-model:value="studentAnswers[String(q.id)]"
                :placeholder="`请输入第 ${index + 1} 题的答案`"
                :rows="4"
                :disabled="mySubmission?.submission_status === 2"
              />
            </div>

            <a-button
              type="primary"
              size="large"
              :loading="submittingAnswers"
              :disabled="mySubmission?.submission_status === 2"
              @click="handleSubmitAnswers"
              style="margin-top: 16px"
            >
              {{ mySubmission ? '重新提交' : '提交答案' }}
            </a-button>
          </a-card>
        </template>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import {
  getAssignmentDetail,
  publishAssignment,
  analyzeStandardAnswers,
  gradeAllSubmissions,
  submitAnswers,
  getMySubmission,
  updateQuestionKeypoints,
} from '@/api/assignment'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isStudent = computed(() => authStore.isStudent)
const assignmentId = computed(() => route.params.id)

const assignment = ref(null)
const questions = ref([])
const loading = ref(false)
const analyzing = ref(false)
const grading = ref(false)
const submittingAnswers = ref(false)
const mySubmission = ref(null)
const studentAnswers = reactive({})

// 编辑关键点相关状态
const editKpVisible = ref(false)
const savingKp = ref(false)
const currentQuestion = ref(null)
const keypointsText = ref('')

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAssignmentDetail(assignmentId.value)
    if (res.success) {
      assignment.value = res.data
      questions.value = res.data.questions || []

      if (isStudent.value) {
        await loadMySubmission()
      }
    } else {
      message.error(res.message || '加载失败')
    }
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const loadMySubmission = async () => {
  try {
    const res = await getMySubmission(assignmentId.value)
    if (res.success) {
      mySubmission.value = res.data
      const answers = res.data.answers || {}
      Object.keys(answers).forEach((k) => {
        studentAnswers[k] = answers[k]
      })
    }
  } catch {
    // student may not have submitted yet
  }
}

const handlePublish = async () => {
  try {
    const res = await publishAssignment(assignmentId.value)
    if (res.success) {
      message.success('发布成功')
      await loadData()
    } else {
      message.error(res.message || '发布失败')
    }
  } catch (e) {
    message.error(e.message || '发布失败')
  }
}

const handleAnalyze = async () => {
  analyzing.value = true
  message.loading({ content: '正在预分析标准答案，可能需要一些时间...', key: 'analyze', duration: 0 })
  try {
    const res = await analyzeStandardAnswers(assignmentId.value)
    if (res.success) {
      message.success({ content: res.message || '预分析完成', key: 'analyze' })
      await loadData()
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
  message.loading({ content: '正在批量判题，请耐心等待...', key: 'grade', duration: 0 })
  try {
    const res = await gradeAllSubmissions(assignmentId.value)
    if (res.success) {
      message.success({ content: res.message || '批量判题完成', key: 'grade' })
    } else {
      message.error({ content: res.message || '判题失败', key: 'grade' })
    }
  } catch (e) {
    message.error({ content: e.message || '判题失败', key: 'grade' })
  } finally {
    grading.value = false
  }
}

const handleSubmitAnswers = async () => {
  const filled = Object.values(studentAnswers).some((v) => v && v.trim())
  if (!filled) {
    message.warning('请至少作答一题')
    return
  }

  submittingAnswers.value = true
  try {
    const res = await submitAnswers(assignmentId.value, studentAnswers)
    if (res.success) {
      message.success('提交成功')
      await loadMySubmission()
    } else {
      message.error(res.message || '提交失败')
    }
  } catch (e) {
    message.error(e.message || '提交失败')
  } finally {
    submittingAnswers.value = false
  }
}

const formatDate = (str) => {
  if (!str) return '-'
  return new Date(str).toLocaleString('zh-CN')
}

const goBack = () => router.back()
const goEdit = () => router.push({ name: 'AssignmentEdit', params: { id: assignmentId.value } })
const goSubmissions = () => router.push({ name: 'SubmissionList', params: { id: assignmentId.value } })
const goMyReport = () => router.push({ name: 'GradeReport', params: { id: assignmentId.value } })

const openEditKeypoints = (q) => {
  currentQuestion.value = q
  const kps = q.answer_keypoints || []
  // 将当前关键点列表转为多行文本
  keypointsText.value = kps
    .map((kp) => (typeof kp === 'string' ? kp : kp.point || kp.description || kp.content || JSON.stringify(kp)))
    .join('\n')
  editKpVisible.value = true
}

const handleSaveKeypoints = async () => {
  if (!currentQuestion.value) return
  const rawLines = keypointsText.value.split('\n').map((l) => l.trim())
  const keypoints = rawLines.filter((l) => l.length > 0)

  savingKp.value = true
  try {
    const res = await updateQuestionKeypoints(assignmentId.value, currentQuestion.value.id, keypoints)
    if (res.success) {
      message.success(res.message || '关键点已更新')
      // 用后端返回的最新作业数据刷新本地 questions
      assignment.value = res.data
      questions.value = res.data.questions || []
      editKpVisible.value = false
      currentQuestion.value = null
    } else {
      message.error(res.message || '更新关键点失败')
    }
  } catch (e) {
    message.error(e.message || '更新关键点失败')
  } finally {
    savingKp.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.assignment-detail-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
.info-card {
  margin-top: 16px;
}
.student-question {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}
.student-question h4 {
  margin-bottom: 8px;
  font-weight: 600;
}
.question-content {
  margin-bottom: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
