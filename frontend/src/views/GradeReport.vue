<template>
  <div class="grade-report-container">
    <a-page-header
      title="评分报告"
      :sub-title="subtitle"
      @back="goBack"
    />

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !submission" description="暂无评分数据" />

      <template v-if="submission">
        <!-- 总分概览 -->
        <ScoreSummary
          :score="totalScore"
          :max-score="totalMaxScore"
          :grade-level="overallGradeLevel"
          :base-score="totalBaseScore"
          :redundant-penalty="totalRedundantPenalty"
        />

        <!-- 总体评语 -->
        <a-card
          v-if="overallComment"
          title="总体评语"
          :bordered="false"
          style="margin-top: 16px"
        >
          <div class="overall-comment">{{ overallComment }}</div>
        </a-card>

        <!-- 逐题评分明细 -->
        <a-card title="逐题评分明细" :bordered="false" style="margin-top: 16px">
          <a-collapse v-model:activeKey="activeKeys" accordion>
            <a-collapse-panel
              v-for="(item, index) in questionResults"
              :key="String(index)"
              :header="getQuestionHeader(item, index)"
              :class="{ 'panel-error': item.status === 'error' }"
            >
              <template #extra>
                <a-tag :color="getQuestionTagColor(item)" size="small">
                  {{ item.report?.summary?.score ?? item.score ?? '-' }} /
                  {{ item.report?.summary?.max_score ?? item.max_score ?? '-' }}
                </a-tag>
              </template>

              <QuestionCard
                :index="index"
                :question="getQuestionContent(item)"
                :student-answer="getStudentAnswer(item)"
                :report="item.report"
              />
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- Agent 流程可视化（取第一道有效题的数据来展示整体流程特征） -->
        <AgentWorkflow
          v-if="firstValidResult"
          :status="firstValidResult.status"
          :scoring-history="firstValidResult.scoring_history || []"
          :meta="firstValidResult.report?.meta"
        />
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import { getMySubmission, getAssignmentDetail } from '@/api/assignment'
import ScoreSummary from '@/components/ScoreSummary.vue'
import QuestionCard from '@/components/QuestionCard.vue'
import AgentWorkflow from '@/components/AgentWorkflow.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const assignmentId = computed(() => route.params.id)
const isStudent = computed(() => authStore.isStudent)

const loading = ref(false)
const submission = ref(null)
const assignment = ref(null)
const activeKeys = ref([])

const subtitle = computed(() => {
  if (submission.value?.student_name) {
    return `${submission.value.student_name} 的作业`
  }
  return ''
})

const gradeInfo = computed(() => submission.value?.grade_info)
const questionResults = computed(() => gradeInfo.value?.grading_rubric || [])
const overallComment = computed(() => gradeInfo.value?.overall_comment || '')
const questions = computed(() => assignment.value?.questions || [])

const totalScore = computed(() => Number(submission.value?.total_score) || 0)
const totalMaxScore = computed(() => Number(assignment.value?.total_score) || 100)

const overallGradeLevel = computed(() => {
  const pct = totalMaxScore.value > 0 ? (totalScore.value / totalMaxScore.value) * 100 : 0
  if (pct >= 90) return '优秀'
  if (pct >= 80) return '良好'
  if (pct >= 60) return '及格'
  return '不及格'
})

const totalBaseScore = computed(() => {
  return questionResults.value.reduce((sum, r) => {
    const bs = r.report?.summary?.base_score ?? r.score ?? 0
    return sum + Number(bs)
  }, 0)
})

const totalRedundantPenalty = computed(() => {
  return questionResults.value.reduce((sum, r) => {
    const rp = r.report?.summary?.redundant_penalty ?? 0
    return sum + Number(rp)
  }, 0)
})

const firstValidResult = computed(() => {
  return questionResults.value.find((r) => r.status === 'completed') || questionResults.value[0]
})

const getQuestionContent = (item) => {
  const qId = item.question_id
  const found = questions.value.find((q) => q.id === qId)
  return found || { content: `题目 ${qId}`, score: item.max_score }
}

const getStudentAnswer = (item) => {
  const answers = submission.value?.answers || {}
  const qId = String(item.question_id)
  return answers[qId] || ''
}

const getQuestionHeader = (item, index) => {
  const q = getQuestionContent(item)
  const content = q.content || ''
  const preview = content.length > 40 ? content.substring(0, 40) + '...' : content
  return `第 ${index + 1} 题：${preview}`
}

const getQuestionTagColor = (item) => {
  if (item.status === 'error') return 'red'
  const score = item.report?.summary?.score ?? item.score
  const maxScore = item.report?.summary?.max_score ?? item.max_score
  if (score == null || maxScore == null) return 'default'
  const pct = (score / maxScore) * 100
  if (pct >= 90) return 'green'
  if (pct >= 80) return 'blue'
  if (pct >= 60) return 'orange'
  return 'red'
}

const loadData = async () => {
  loading.value = true
  try {
    // Load assignment details for question content
    const assignRes = await getAssignmentDetail(assignmentId.value)
    if (assignRes.success) {
      assignment.value = assignRes.data
    }

    // Load submission data
    const subRes = await getMySubmission(assignmentId.value)
    if (subRes.success) {
      submission.value = subRes.data
    } else {
      message.warning(subRes.message || '暂无提交记录')
    }
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => router.back()

onMounted(loadData)
</script>

<style scoped>
.grade-report-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
.overall-comment {
  padding: 16px;
  background: #f6ffed;
  border-left: 3px solid #52c41a;
  border-radius: 6px;
  line-height: 1.8;
  white-space: pre-wrap;
}
.panel-error :deep(.ant-collapse-header) {
  color: #f5222d !important;
}
</style>
