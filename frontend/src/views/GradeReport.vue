<template>
  <div class="grade-report-container">
    <a-page-header title="评分报告" :sub-title="subtitle" @back="goBack" />

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !submission" description="暂无评分数据" />

      <template v-if="submission">
        <!-- 总分概览 -->
        <ScoreSummary :score="totalScore" :max-score="totalMaxScore" :grade-level="overallGradeLevel"
          :base-score="totalBaseScore" :redundant-penalty="totalRedundantPenalty" />

        <!-- 总体评语 -->
        <a-card v-if="overallComment" title="总体评语" :bordered="false" style="margin-top: 16px">
          <div class="overall-comment">{{ overallComment }}</div>
        </a-card>

        <!-- 逐题评分明细 -->
        <a-card title="逐题评分明细" :bordered="false" style="margin-top: 16px">
          <a-collapse v-model="activeKeys" accordion>
            <a-collapse-panel v-for="(item, index) in questionResults" :key="String(index)"
              :header="getQuestionHeader(item, index)"
              :class="{ 'panel-error': item.status === 'error', 'panel-ungraded': item._ungraded }">
              <template #extra>
                <a-tag v-if="item._ungraded" color="default" size="small">暂未批改</a-tag>
                <a-tag v-else :color="getQuestionTagColor(item)" size="small">
                  {{ item.report?.summary?.score ?? item.score ?? '-' }} /
                  {{ item.report?.summary?.max_score ?? item.max_score ?? '-' }}
                </a-tag>
              </template>

              <!-- 未评分占位 -->
              <a-empty v-if="item._ungraded" description="该题目暂未批改" :image="false" style="padding: 16px 0" />

              <!-- 人工评分 / AI 判题 均用 QuestionCard 渲染 -->
              <template v-else>
                <!-- 人工评分维度分（仅 dimension_scores 有数据时显示） -->
                <div
                  v-if="item.report?.scoring_details?.manual_dimension_scores"
                  class="manual-dimension-scores"
                >
                  <div class="section-label">人工评分维度</div>
                  <div class="dimension-list">
                    <div
                      v-for="(dimScore, dimName) in item.report.scoring_details.manual_dimension_scores"
                      :key="dimName"
                      class="dimension-row"
                    >
                      <div class="dimension-header">
                        <span class="dimension-name">{{ dimName }}</span>
                        <span class="dimension-score">{{ dimScore }} 分</span>
                      </div>
                    </div>
                  </div>
                </div>

                <QuestionCard
                  :index="index"
                  :question="getQuestionContent(item)"
                  :student-answer="getStudentAnswer(item)"
                  :report="item.report"
                />
              </template>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 推荐阅读文档（基于检索到的参考资料） -->
        <a-card v-if="recommendedDocuments.length > 0" title="推荐阅读资料" :bordered="false" style="margin-top: 16px">
          <p class="recommended-docs-hint">
            下列资料按本次判题时检索结果的<strong>相关度从高到低</strong>排列；「第 N 位」仅表示在本次返回的几条中的顺序，不代表绝对相似度百分比。
          </p>
          <a-list :data-source="recommendedDocuments" item-layout="horizontal">
            <template #renderItem="{ item, index }">
              <a-list-item>
                <a-list-item-meta>
                  <template #title>
                    <span class="recommended-doc-title">
                      <a-tag :color="index === 0 ? 'gold' : 'default'" class="rank-tag">
                        第 {{ index + 1 }} 位
                      </a-tag>
                      {{ item.title || '课程相关文档' }}
                    </span>
                  </template>
                  <template #description>
                    <div v-if="item.snippet" class="recommended-doc-snippet">
                      {{ item.snippet }}
                    </div>
                  </template>
                </a-list-item-meta>
              </a-list-item>
            </template>
          </a-list>
        </a-card>

        <!-- Agent 流程可视化（取第一道有效题的数据来展示整体流程特征） -->
        <AgentWorkflow v-if="firstValidResult" :status="firstValidResult.status"
          :scoring-history="firstValidResult.scoring_history || []" :meta="firstValidResult.report?.meta" />
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import {
  getMySubmission,
  getSubmissionDetail,
  getAssignmentDetail,
} from '@/api/assignment'
import ScoreSummary from '@/components/ScoreSummary.vue'
import QuestionCard from '@/components/QuestionCard.vue'
import AgentWorkflow from '@/components/AgentWorkflow.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const assignmentId = computed(() => route.params.id)
const isStudent = computed(() => authStore.isStudent)
const submissionId = computed(() => route.query.submission_id || null)

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
const overallComment = computed(() => gradeInfo.value?.overall_comment || '')
const questions = computed(() => assignment.value?.questions || [])

/**
 * 将 grading_rubric 条目规范化，确保每条都有可供 QuestionCard 使用的 report 字段。
 * 兼容两种来源：
 *   - AI 判题：已含完整 report（feedback / keypoint_analysis / scoring_details 等）
 *   - 人工评分：只有 {score, comment, dimension_scores}，需补出 synthetic report
 */
const normalizeRubricItem = (item, question) => {
  if (item.report) return item                          // AI 判题：直接使用

  // 人工评分：从 comment / dimension_scores 构造 report
  const syntheticReport = {
    score: item.score ?? null,
    max_score: item.max_score ?? question?.score ?? null,
    summary: {
      score: item.score ?? 0,
      max_score: item.max_score ?? question?.score ?? 0,
    },
  }

  if (item.comment) {
    syntheticReport.feedback = item.comment
  }

  // 将 dimension_scores 转为 scoring_details.scoring_breakdown
  if (item.dimension_scores && typeof item.dimension_scores === 'object') {
    const breakdown = {}
    for (const [dimName, dimScore] of Object.entries(item.dimension_scores)) {
      breakdown[dimName] = { score_ratio: null, comment: `${dimName}: ${dimScore} 分` }
    }
    syntheticReport.scoring_details = {
      type: question?.question_type === 'report' ? 'report'
          : question?.question_type === 'python' ? 'python'
          : question?.question_type === 'sql' ? 'sql'
          : 'manual',
      scoring_breakdown: breakdown,
      manual_dimension_scores: item.dimension_scores,   // 原始维度分，供自定义展示
    }
  }

  return { ...item, report: syntheticReport }
}

/**
 * 以作业题目列表为基准，逐题合并评分细则。
 * 保证即使 grading_rubric 只有部分题目，所有题目都会出现在报告中。
 */
const questionResults = computed(() => {
  const rubric = gradeInfo.value?.grading_rubric || []
  const allQuestions = questions.value

  // 构建 question_id → rubric item 映射（支持数字和字符串 id）
  const rubricMap = {}
  for (const item of rubric) {
    rubricMap[String(item.question_id)] = item
  }

  // 有作业题目时，以题目顺序为准，合并评分数据
  if (allQuestions.length > 0) {
    return allQuestions.map((q) => {
      const qid = String(q.id)
      const rubricItem = rubricMap[qid]
      if (rubricItem) {
        return normalizeRubricItem(rubricItem, q)
      }
      // 该题目暂无评分记录
      return {
        question_id: q.id,
        status: 'pending',
        score: null,
        max_score: q.score,
        report: null,
        _ungraded: true,
      }
    })
  }

  // 作业题目列表为空时降级：直接渲染 rubric（规范化处理）
  return rubric.map((item) => normalizeRubricItem(item, null))
})

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

// 从第一道有效题的报告中抽取推荐文档列表
const recommendedDocuments = computed(() => {
  const base = firstValidResult.value
  if (!base || !base.report || !Array.isArray(base.report.recommended_documents)) {
    return []
  }
  return base.report.recommended_documents
})

const getQuestionContent = (item) => {
  const qId = item.question_id
  const found = questions.value.find((q) => q.id === qId)
  return found || { content: `题目 ${qId}`, score: item.max_score }
}

const getStudentAnswer = (item) => {
  const answers = submission.value?.answers || {}
  const qId = String(item.question_id)
  return answers[qId] !== undefined ? answers[qId] : ''
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
    let subRes
    if (isStudent.value || !submissionId.value) {
      // 学生视角或无 submission_id 时，使用“我的提交”接口
      subRes = await getMySubmission(assignmentId.value)
    } else {
      // 教师视角：通过 submission_id 精确获取指定学生的提交
      subRes = await getSubmissionDetail(assignmentId.value, submissionId.value)
    }

    if (subRes.success) {
      submission.value = subRes.data
    } else {
      message.warning(subRes.message || '暂无提交记录或尚未批改')
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

.panel-ungraded :deep(.ant-collapse-header) {
  color: #999 !important;
}

.manual-dimension-scores {
  margin-bottom: 16px;
}

.section-label {
  font-weight: 600;
  color: #333;
  margin-bottom: 8px;
  font-size: 13px;
}

.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dimension-row {
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 6px;
}

.dimension-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
}

.dimension-name {
  font-weight: 500;
  color: #333;
}

.dimension-score {
  font-weight: 600;
  color: #1890ff;
}

.recommended-docs-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: rgba(0, 0, 0, 0.55);
  line-height: 1.6;
}

.recommended-doc-title {
  display: inline-flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.rank-tag {
  margin-inline-end: 0;
}

.recommended-doc-snippet {
  margin-top: 4px;
}
</style>
