<template>
  <a-card :bordered="false" class="score-summary">
    <a-row :gutter="24" align="middle">
      <a-col :span="8" class="score-circle-col">
        <a-progress
          type="circle"
          :percent="percentage"
          :size="140"
          :stroke-color="gradeColor"
        >
          <template #format>
            <div class="score-inner">
              <div class="score-number">{{ score }}</div>
              <div class="score-max">/ {{ maxScore }}</div>
            </div>
          </template>
        </a-progress>
      </a-col>

      <a-col :span="16">
        <div class="score-details">
          <div class="grade-level">
            <a-tag :color="gradeColor" class="grade-tag">{{ gradeLevel }}</a-tag>
            <span class="percentage-text">{{ percentage.toFixed(1) }}%</span>
          </div>

          <a-row :gutter="16" style="margin-top: 16px">
            <a-col :span="8">
              <a-statistic title="基础得分" :value="baseScore" :precision="2" />
            </a-col>
            <a-col :span="8">
              <a-statistic title="冗余扣分" :precision="2" value-style="color: #cf1322">
                <template #formatter>
                  -{{ redundantPenalty }}
                </template>
              </a-statistic>
            </a-col>
            <a-col :span="8">
              <a-statistic title="最终得分" :value="score" :precision="2" value-style="color: #1890ff; font-weight: 700" />
            </a-col>
          </a-row>
        </div>
      </a-col>
    </a-row>
  </a-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  score: { type: Number, default: 0 },
  maxScore: { type: Number, default: 100 },
  gradeLevel: { type: String, default: '' },
  baseScore: { type: Number, default: 0 },
  redundantPenalty: { type: Number, default: 0 },
})

const percentage = computed(() => {
  if (!props.maxScore) return 0
  return (props.score / props.maxScore) * 100
})

const gradeColor = computed(() => {
  if (percentage.value >= 90) return '#52c41a'
  if (percentage.value >= 80) return '#1890ff'
  if (percentage.value >= 60) return '#faad14'
  return '#f5222d'
})
</script>

<style scoped>
.score-summary {
  margin-top: 16px;
}
.score-circle-col {
  display: flex;
  justify-content: center;
}
.score-inner {
  text-align: center;
}
.score-number {
  font-size: 28px;
  font-weight: 700;
  color: #333;
  line-height: 1.2;
}
.score-max {
  font-size: 14px;
  color: #999;
}
.grade-level {
  display: flex;
  align-items: center;
  gap: 12px;
}
.grade-tag {
  font-size: 18px;
  padding: 4px 16px;
  line-height: 28px;
}
.percentage-text {
  font-size: 24px;
  font-weight: 600;
  color: #666;
}
</style>
