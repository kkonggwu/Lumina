<template>
  <a-card size="small" class="question-card" :bordered="true">
    <template #title>
      <div class="question-header">
        <span class="question-index">第 {{ index + 1 }} 题</span>
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

    <!-- 学生答案 -->
    <div class="section" v-if="studentAnswer !== undefined">
      <div class="section-label">学生答案</div>
      <div class="section-content student-answer">{{ studentAnswer || '未作答' }}</div>
    </div>

    <!-- 评分报告详情 -->
    <template v-if="report">
      <!-- 综合评语 -->
      <div class="section" v-if="report.feedback">
        <div class="section-label">综合评语</div>
        <div class="feedback-content">{{ report.feedback }}</div>
      </div>

      <!-- 关键点分析 -->
      <div class="section" v-if="report.keypoint_analysis">
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

const missingKeypoints = computed(() => {
  return props.report?.keypoint_analysis?.missing_keypoints || []
})

const redundantKeypoints = computed(() => {
  return props.report?.keypoint_analysis?.redundant_keypoints || []
})

const suggestions = computed(() => {
  return props.report?.improvement_suggestions || []
})

const scoreColor = computed(() => {
  if (!props.report) return 'default'
  const pct = (props.report.score / props.report.max_score) * 100
  if (pct >= 90) return 'green'
  if (pct >= 80) return 'blue'
  if (pct >= 60) return 'orange'
  return 'red'
})

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
  justify-content: space-between;
}
.question-index {
  font-weight: 600;
}
.score-tag {
  font-size: 14px;
  padding: 2px 10px;
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
.kp-item {
  padding: 4px 0;
  font-size: 13px;
  display: flex;
  align-items: flex-start;
}
</style>
