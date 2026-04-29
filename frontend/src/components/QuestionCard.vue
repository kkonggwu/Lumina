<template>
  <a-card size="small" class="question-card" :bordered="true">
    <template #title>
      <div class="question-header">
        <span class="question-index">第 {{ index + 1 }} 题</span>
        <a-tag v-if="questionTypeLabel" :color="questionTypeColor" class="type-tag">
          {{ questionTypeLabel }}
        </a-tag>
        <a-tag v-if="report" :color="scoreColor" class="score-tag">
          {{ report.score }} / {{ report.max_score }}
        </a-tag>
      </div>
    </template>

    <!-- 题目内容 -->
    <div class="section">
      <div class="section-label">题目内容</div>
      <div class="section-content">{{ question.content }}</div>
    </div>

    <!-- 学生答案：代码题用代码块样式，其他用普通文本 -->
    <div class="section" v-if="studentAnswer !== undefined">
      <div class="section-label">学生答案</div>
      <pre v-if="isCodeType" class="code-block">{{ studentAnswer || '未作答' }}</pre>
      <div v-else class="section-content student-answer">{{ studentAnswer || '未作答' }}</div>
    </div>

    <!-- 评分报告详情 -->
    <template v-if="report">
      <!-- 综合评语 -->
      <div class="section" v-if="report.feedback">
        <div class="section-label">综合评语</div>
        <div class="feedback-content">{{ report.feedback }}</div>
      </div>

      <!-- 关键点分析（仅文本题展示） -->
      <div class="section" v-if="!isCodeType && !isReportType && report.keypoint_analysis">
        <div class="section-label">关键点分析</div>
        <a-row :gutter="8" style="margin-bottom: 8px">
          <a-col>
            <a-tag color="blue">标准关键点 {{ report.keypoint_analysis.total_standard }} 个</a-tag>
          </a-col>
          <a-col>
            <a-tag color="green">高度匹配 {{ report.keypoint_analysis.high_match_count }} 个</a-tag>
          </a-col>
          <a-col>
            <a-tag color="cyan">部分匹配 {{ report.keypoint_analysis.medium_match_count }} 个</a-tag>
          </a-col>
          <a-col>
            <a-tag color="red">缺失 {{ report.keypoint_analysis.missing_count }} 个</a-tag>
          </a-col>
        </a-row>

        <!-- 缺失关键点 -->
        <div v-if="missingKeypoints.length" class="keypoints-list">
          <div class="kp-label missing-label">缺失的关键点：</div>
          <div v-for="(kp, ki) in missingKeypoints" :key="'m'+ki" class="kp-item missing">
            <close-circle-outlined style="color: #f5222d; margin-right: 6px" />
            {{ formatKeypoint(kp) }}
          </div>
        </div>

        <!-- 冗余关键点 -->
        <div v-if="redundantKeypoints.length" class="keypoints-list" style="margin-top: 8px">
          <div class="kp-label redundant-label">冗余的关键点：</div>
          <div v-for="(kp, ki) in redundantKeypoints" :key="'r'+ki" class="kp-item redundant">
            <template v-if="typeof kp === 'object'">
              <a-tag :color="kp.is_valid ? 'green' : 'red'" size="small">
                {{ kp.is_valid ? '有效补充' : '无效/错误' }}
              </a-tag>
              {{ formatKeypoint(kp) }}
            </template>
            <template v-else>{{ kp }}</template>
          </div>
        </div>
      </div>

      <!-- 代码题评分明细：correctness / logic / style 或 efficiency -->
      <div class="section" v-if="isCodeType && codeBreakdown">
        <div class="section-label">{{ codeType === 'sql' ? 'SQL 评分明细' : 'Python 评分明细' }}</div>
        <div class="dimension-list">
          <div
            v-for="dim in codeDimensions"
            :key="dim.key"
            class="dimension-row"
          >
            <div class="dimension-header">
              <span class="dimension-name">{{ dim.label }}</span>
              <span class="dimension-weight">权重 {{ Math.round(dim.weight * 100) }}%</span>
              <span class="dimension-score">
                {{ dim.score }} / {{ (report.max_score * dim.weight).toFixed(2) }}
              </span>
            </div>
            <a-progress
              :percent="Math.round((dim.ratio || 0) * 100)"
              :stroke-color="getProgressColor(dim.ratio)"
              size="small"
              :show-info="true"
            />
            <div v-if="dim.comment" class="dimension-comment">{{ dim.comment }}</div>
          </div>
        </div>

        <!-- 测试用例分析 -->
        <div v-if="testCaseResults.length" class="test-results">
          <div class="kp-label">测试用例分析：</div>
          <a-list size="small" :data-source="testCaseResults">
            <template #renderItem="{ item: tc, index: ti }">
              <a-list-item>
                <a-tag :color="tc.pass === false ? 'red' : 'green'">
                  {{ tc.pass === false ? '不通过' : '通过' }}
                </a-tag>
                <span style="margin-left: 8px">
                  <strong>用例 {{ ti + 1 }}</strong>
                  <span v-if="tc.case" style="color: #999; margin-left: 6px">{{ tc.case }}</span>
                </span>
                <div v-if="tc.analysis" style="margin-top: 4px; color: #555">
                  {{ tc.analysis }}
                </div>
              </a-list-item>
            </template>
          </a-list>
        </div>
      </div>

      <!-- 报告题评分明细：structure / content / writing / innovation -->
      <div class="section" v-if="isReportType && reportBreakdown">
        <div class="section-label">报告评分明细</div>
        <div class="dimension-list">
          <div
            v-for="dim in reportDimensions"
            :key="dim.key"
            class="dimension-row"
          >
            <div class="dimension-header">
              <span class="dimension-name">{{ dim.label }}</span>
              <span class="dimension-weight">权重 {{ Math.round(dim.weight * 100) }}%</span>
              <span class="dimension-score">
                {{ dim.score }} / {{ (report.max_score * dim.weight).toFixed(2) }}
              </span>
            </div>
            <a-progress
              :percent="Math.round((dim.ratio || 0) * 100)"
              :stroke-color="getProgressColor(dim.ratio)"
              size="small"
              :show-info="true"
            />
            <div v-if="dim.comment" class="dimension-comment">{{ dim.comment }}</div>
          </div>
        </div>

        <!-- 内容覆盖知识点 -->
        <div v-if="contentKeypoints.covered.length || contentKeypoints.missing.length" class="report-keypoints">
          <div v-if="contentKeypoints.covered.length" class="keypoints-list">
            <div class="kp-label covered-label">已覆盖知识点：</div>
            <a-tag v-for="(kp, ki) in contentKeypoints.covered" :key="'c'+ki" color="green">
              {{ kp }}
            </a-tag>
          </div>
          <div v-if="contentKeypoints.missing.length" class="keypoints-list" style="margin-top: 8px">
            <div class="kp-label missing-label">缺失知识点：</div>
            <a-tag v-for="(kp, ki) in contentKeypoints.missing" :key="'mk'+ki" color="red">
              {{ kp }}
            </a-tag>
          </div>
        </div>
      </div>

      <!-- 改进建议 -->
      <div class="section" v-if="suggestions.length">
        <div class="section-label">改进建议</div>
        <a-list size="small" :data-source="suggestions">
          <template #renderItem="{ item }">
            <a-list-item>
              <bulb-outlined style="color: #faad14; margin-right: 8px" />
              {{ item }}
            </a-list-item>
          </template>
        </a-list>
      </div>
    </template>
  </a-card>
</template>

<script setup>
import { computed } from 'vue'
import { CloseCircleOutlined, BulbOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  index: { type: Number, required: true },
  question: { type: Object, required: true },
  studentAnswer: { type: String, default: undefined },
  report: { type: Object, default: null },
})

const QUESTION_TYPE_LABEL = {
  essay: '论述题',
  short_answer: '简答题',
  python: 'Python',
  sql: 'SQL',
  report: '课程报告',
}

const QUESTION_TYPE_COLOR = {
  essay: 'blue',
  short_answer: 'cyan',
  python: 'geekblue',
  sql: 'purple',
  report: 'gold',
}

const detailType = computed(() => props.report?.scoring_details?.type || '')

const codeType = computed(() => {
  if (detailType.value === 'python' || detailType.value === 'sql') return detailType.value
  return props.question.question_type || ''
})

const isCodeType = computed(() =>
  codeType.value === 'python' || codeType.value === 'sql'
)

const isReportType = computed(() =>
  detailType.value === 'report' || props.question.question_type === 'report'
)

const questionTypeLabel = computed(() => {
  const t = props.question.question_type
  if (!t) return ''
  return QUESTION_TYPE_LABEL[t] || t
})

const questionTypeColor = computed(() => {
  const t = props.question.question_type
  return QUESTION_TYPE_COLOR[t] || 'default'
})

const codeBreakdown = computed(() => props.report?.scoring_details?.scoring_breakdown || null)
const reportBreakdown = computed(() => props.report?.scoring_details?.scoring_breakdown || null)

// Python: correctness 50 / logic 30 / style 20
// SQL:    correctness 60 / logic 30 / efficiency 10
const codeDimensions = computed(() => {
  const bd = codeBreakdown.value
  if (!bd) return []
  if (codeType.value === 'sql') {
    return [
      { key: 'correctness', label: '正确性', weight: 0.6, ...(bd.correctness || {}) },
      { key: 'logic', label: '逻辑性', weight: 0.3, ...(bd.logic || {}) },
      { key: 'efficiency', label: '高效性', weight: 0.1, ...(bd.efficiency || {}) },
    ]
  }
  return [
    { key: 'correctness', label: '正确性', weight: 0.5, ...(bd.correctness || {}) },
    { key: 'logic', label: '逻辑性', weight: 0.3, ...(bd.logic || {}) },
    { key: 'style', label: '规范性', weight: 0.2, ...(bd.style || {}) },
  ]
})

// Report: structure 20 / content 40 / writing 20 / innovation 20
const reportDimensions = computed(() => {
  const bd = reportBreakdown.value
  if (!bd) return []
  return [
    { key: 'structure', label: '结构完整性', weight: 0.2, ...(bd.structure || {}) },
    { key: 'content', label: '内容质量', weight: 0.4, ...(bd.content || {}) },
    { key: 'writing', label: '语言表达', weight: 0.2, ...(bd.writing || {}) },
    { key: 'innovation', label: '创新思考', weight: 0.2, ...(bd.innovation || {}) },
  ]
})

const testCaseResults = computed(() => {
  const bd = codeBreakdown.value
  if (!bd) return []
  return bd.correctness?.test_case_results || []
})

const contentKeypoints = computed(() => {
  const bd = reportBreakdown.value
  return {
    covered: bd?.content?.key_points_covered || [],
    missing: bd?.content?.key_points_missing || [],
  }
})

const missingKeypoints = computed(() => props.report?.keypoint_analysis?.missing_keypoints || [])
const redundantKeypoints = computed(() => props.report?.keypoint_analysis?.redundant_keypoints || [])

// 改进建议：兼容多种字段位置
const suggestions = computed(() => {
  if (Array.isArray(props.report?.suggestions)) return props.report.suggestions
  if (Array.isArray(props.report?.improvement_suggestions)) return props.report.improvement_suggestions
  if (Array.isArray(props.report?.scoring_details?.suggestions)) return props.report.scoring_details.suggestions
  return []
})

const scoreColor = computed(() => {
  if (!props.report) return 'default'
  const pct = (props.report.score / props.report.max_score) * 100
  if (pct >= 90) return 'green'
  if (pct >= 80) return 'blue'
  if (pct >= 60) return 'orange'
  return 'red'
})

const getProgressColor = (ratio) => {
  const r = Number(ratio) || 0
  if (r >= 0.9) return '#52c41a'
  if (r >= 0.7) return '#1890ff'
  if (r >= 0.5) return '#faad14'
  return '#f5222d'
}

const formatKeypoint = (kp) => {
  if (typeof kp === 'string') return kp
  return kp.point || kp.description || kp.content || JSON.stringify(kp)
}
</script>

<style scoped>
.question-card {
  margin-bottom: 16px;
}
.question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-start;
}
.question-index {
  font-weight: 600;
}
.type-tag {
  margin-left: 4px;
}
.score-tag {
  font-size: 14px;
  padding: 2px 10px;
  margin-left: auto;
}
.section {
  margin-bottom: 16px;
}
.section-label {
  font-weight: 600;
  color: #333;
  margin-bottom: 6px;
  font-size: 13px;
}
.section-content {
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
  white-space: pre-wrap;
  line-height: 1.6;
}
.student-answer {
  background: #f0f5ff;
  border-left: 3px solid #1890ff;
}
.code-block {
  margin: 0;
  padding: 10px 12px;
  background: #f6f8fa;
  border-radius: 6px;
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
  border-left: 3px solid #1890ff;
  max-height: 360px;
  overflow: auto;
}
.feedback-content {
  padding: 12px;
  background: #fffbe6;
  border-left: 3px solid #faad14;
  border-radius: 6px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.keypoints-list {
  padding: 8px 12px;
  background: #fff;
  border-radius: 4px;
}
.kp-label {
  font-weight: 500;
  margin-bottom: 4px;
  font-size: 13px;
}
.missing-label { color: #f5222d; }
.redundant-label { color: #faad14; }
.covered-label { color: #389e0d; }
.kp-item {
  padding: 4px 0;
  font-size: 13px;
  display: flex;
  align-items: flex-start;
}
.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dimension-row {
  padding: 10px 12px;
  background: #fafafa;
  border-radius: 6px;
}
.dimension-header {
  display: flex;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  gap: 8px;
}
.dimension-name {
  font-weight: 600;
  color: #333;
}
.dimension-weight {
  color: #999;
  font-size: 12px;
}
.dimension-score {
  margin-left: auto;
  font-weight: 600;
  color: #1890ff;
}
.dimension-comment {
  margin-top: 6px;
  padding: 6px 8px;
  background: #fff;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
  line-height: 1.6;
}
.test-results {
  margin-top: 16px;
  padding: 8px 12px;
  background: #fff;
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
}
.report-keypoints {
  margin-top: 12px;
}
</style>
