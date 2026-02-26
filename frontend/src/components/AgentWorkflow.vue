<template>
  <a-card title="Agent 判题流程" :bordered="false" class="agent-workflow">
    <a-steps :current="currentStep" :status="stepStatus" size="small">
      <a-step title="检索" description="RetrieverAgent">
        <template #icon>
          <search-outlined />
        </template>
      </a-step>
      <a-step title="分析" description="AnalyzerAgent">
        <template #icon>
          <experiment-outlined />
        </template>
      </a-step>
      <a-step title="评分" description="ScorerAgent">
        <template #icon>
          <calculator-outlined />
        </template>
      </a-step>
      <a-step title="质量检查" :description="qualityCheckDesc">
        <template #icon>
          <safety-certificate-outlined />
        </template>
      </a-step>
      <a-step title="生成报告" description="ReporterAgent">
        <template #icon>
          <file-done-outlined />
        </template>
      </a-step>
    </a-steps>

    <!-- 评分历史时间线 -->
    <div v-if="scoringHistory.length > 0" class="scoring-timeline">
      <a-divider orientation="left" plain>评分历史</a-divider>
      <a-timeline>
        <a-timeline-item
          v-for="(item, index) in scoringHistory"
          :key="index"
          :color="item.is_rescore ? 'orange' : 'blue'"
        >
          <div class="timeline-content">
            <span class="timeline-label">
              {{ item.is_rescore ? '重新评分' : '首次评分' }}
              #{{ item.attempt || index + 1 }}
            </span>
            <span class="timeline-score">{{ item.score }} 分</span>
            <a-tag v-if="item.confidence" :color="confidenceColor(item.confidence)" size="small">
              置信度 {{ (item.confidence * 100).toFixed(0) }}%
            </a-tag>
            <span class="timeline-time" v-if="item.timestamp">
              {{ formatTime(item.timestamp) }}
            </span>
          </div>
        </a-timeline-item>
      </a-timeline>
    </div>

    <!-- 元信息 -->
    <div v-if="meta" class="meta-info">
      <a-divider orientation="left" plain>流程元信息</a-divider>
      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic title="评分次数" :value="meta.total_attempts || 0" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="重评次数" :value="meta.rescore_count || 0" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="最终置信度" :precision="0" suffix="%">
            <template #formatter>
              {{ meta.final_confidence ? (meta.final_confidence * 100).toFixed(0) : '-' }}
            </template>
          </a-statistic>
        </a-col>
        <a-col :span="6">
          <a-statistic title="人工审核">
            <template #formatter>
              <a-tag :color="meta.has_human_feedback ? 'orange' : 'green'">
                {{ meta.has_human_feedback ? '是' : '否' }}
              </a-tag>
            </template>
          </a-statistic>
        </a-col>
      </a-row>
    </div>
  </a-card>
</template>

<script setup>
import { computed } from 'vue'
import {
  SearchOutlined,
  ExperimentOutlined,
  CalculatorOutlined,
  SafetyCertificateOutlined,
  FileDoneOutlined,
} from '@ant-design/icons-vue'

const props = defineProps({
  status: { type: String, default: 'completed' },
  scoringHistory: { type: Array, default: () => [] },
  meta: { type: Object, default: null },
})

const currentStep = computed(() => {
  if (props.status === 'error') return 0
  if (props.status === 'completed') return 4
  if (props.status === 'scored' || props.status === 'reviewing' || props.status === 'reviewed') return 3
  if (props.status === 'analyzed') return 2
  if (props.status === 'retrieved') return 1
  return 0
})

const stepStatus = computed(() => {
  if (props.status === 'error') return 'error'
  if (props.status === 'completed') return 'finish'
  return 'process'
})

const qualityCheckDesc = computed(() => {
  const rescoreCount = props.meta?.rescore_count || 0
  const hasHuman = props.meta?.has_human_feedback
  if (hasHuman) return '经人工审核'
  if (rescoreCount > 0) return `重评 ${rescoreCount} 次`
  return '质量合格'
})

const confidenceColor = (c) => {
  if (c >= 0.8) return 'green'
  if (c >= 0.6) return 'blue'
  return 'orange'
}

const formatTime = (ts) => {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN')
}
</script>

<style scoped>
.agent-workflow {
  margin-top: 16px;
}
.scoring-timeline {
  margin-top: 16px;
}
.timeline-content {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.timeline-label {
  font-weight: 500;
}
.timeline-score {
  font-size: 16px;
  font-weight: 600;
  color: #1890ff;
}
.timeline-time {
  color: #999;
  font-size: 12px;
}
.meta-info {
  margin-top: 8px;
}
</style>
