<template>
  <div class="assignment-form-container">
    <a-page-header title="创建作业" @back="goBack" />

    <a-card :bordered="false">
      <a-form
        :model="form"
        :rules="rules"
        ref="formRef"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="所属课程" name="course_id">
              <a-select
                v-model:value="form.course_id"
                placeholder="请选择课程"
                show-search
                option-filter-prop="label"
                :options="courseOptions"
                :loading="coursesLoading"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="作业标题" name="title">
              <a-input v-model:value="form.title" placeholder="请输入作业标题" :maxlength="200" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="作业描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="请输入作业描述（选填）" :rows="3" />
        </a-form-item>

        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="开始时间" name="start_time">
              <a-date-picker
                v-model:value="form.start_time"
                show-time
                format="YYYY-MM-DD HH:mm:ss"
                placeholder="选择开始时间"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="截止时间" name="end_time">
              <a-date-picker
                v-model:value="form.end_time"
                show-time
                format="YYYY-MM-DD HH:mm:ss"
                placeholder="选择截止时间"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 动态题目列表 -->
        <a-divider>题目列表（总分：{{ totalScore }}）</a-divider>

        <div v-for="(q, index) in form.questions" :key="q.id" class="question-block">
          <a-card
            size="small"
            :title="`第 ${index + 1} 题`"
            class="question-card"
          >
            <template #extra>
              <a-space>
                <a-tag :color="QUESTION_TYPE_COLOR[q.question_type] || 'default'">
                  {{ QUESTION_TYPE_LABEL[q.question_type] || q.question_type }}
                </a-tag>
                <a-popconfirm
                  v-if="form.questions.length > 1"
                  title="确定删除该题目？"
                  @confirm="removeQuestion(index)"
                >
                  <a-button type="link" danger size="small">删除</a-button>
                </a-popconfirm>
              </a-space>
            </template>

            <a-row :gutter="16">
              <a-col :span="8">
                <a-form-item
                  label="题目类型"
                  :name="['questions', index, 'question_type']"
                  :rules="[{ required: true, message: '请选择题目类型' }]"
                >
                  <a-select
                    v-model:value="q.question_type"
                    :options="QUESTION_TYPE_OPTIONS"
                    style="width: 100%"
                    @change="handleTypeChange(q)"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="16">
                <a-form-item
                  label="题目内容"
                  :name="['questions', index, 'content']"
                  :rules="[{ required: true, message: '请输入题目内容' }]"
                >
                  <a-textarea
                    v-model:value="q.content"
                    placeholder="请输入题目内容/作业要求"
                    :rows="2"
                  />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="16">
              <a-col :span="6">
                <a-form-item
                  label="分值"
                  :name="['questions', index, 'score']"
                  :rules="[{ required: true, message: '请输入分值' }]"
                >
                  <a-input-number
                    v-model:value="q.score"
                    :min="1"
                    :max="100"
                    placeholder="分值"
                    style="width: 100%"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="18">
                <a-form-item
                  :label="getStandardAnswerLabel(q.question_type)"
                  :name="['questions', index, 'standard_answer']"
                  :rules="[{ required: true, message: '请输入标准答案/参考实现' }]"
                >
                  <a-textarea
                    v-model:value="q.standard_answer"
                    :placeholder="getStandardAnswerPlaceholder(q.question_type)"
                    :rows="getStandardAnswerRows(q.question_type)"
                    :class="{ 'code-input': isCodeType(q.question_type) }"
                  />
                </a-form-item>
              </a-col>
            </a-row>

            <!-- Python / SQL 题：测试用例编辑 -->
            <template v-if="isCodeType(q.question_type)">
              <a-divider orientation="left" plain>测试用例（必填）</a-divider>
              <div class="test-cases-block">
                <div
                  v-for="(tc, ti) in q.test_cases"
                  :key="ti"
                  class="test-case-row"
                >
                  <span class="test-case-index">用例 {{ ti + 1 }}</span>
                  <a-input
                    v-model:value="tc.input"
                    placeholder="输入"
                    style="flex: 1; margin-right: 8px"
                  />
                  <a-input
                    v-model:value="tc.output"
                    :placeholder="q.question_type === 'sql' ? '期望结果集说明' : '期望输出'"
                    style="flex: 1; margin-right: 8px"
                  />
                  <a-input
                    v-model:value="tc.description"
                    placeholder="说明（可选）"
                    style="flex: 1; margin-right: 8px"
                  />
                  <a-button
                    type="link"
                    danger
                    size="small"
                    :disabled="q.test_cases.length <= 1"
                    @click="removeTestCase(q, ti)"
                  >
                    删除
                  </a-button>
                </div>
                <a-button
                  type="dashed"
                  block
                  size="small"
                  @click="addTestCase(q)"
                >
                  <plus-outlined /> 添加测试用例
                </a-button>
              </div>
            </template>

            <!-- 报告题：评分细则 -->
            <template v-if="q.question_type === 'report'">
              <a-form-item
                label="评分细则（选填）"
                :name="['questions', index, 'grading_rubric']"
                extra="可填写本报告的评分细则、要求和侧重点。留空则按通用学术标准评分。"
              >
                <a-textarea
                  v-model:value="q.grading_rubric"
                  placeholder="例如：1. 报告须包含背景、方法、结果、结论四个部分; 2. 重点考察对XX知识点的理解; 3. 鼓励结合实例论述。"
                  :rows="3"
                />
              </a-form-item>
            </template>
          </a-card>
        </div>

        <a-button type="dashed" block @click="addQuestion" class="add-question-btn">
          <template #icon><plus-outlined /></template>
          添加题目
        </a-button>

        <a-form-item style="margin-top: 24px">
          <a-space>
            <a-button type="primary" html-type="submit" :loading="submitting" size="large">
              创建作业
            </a-button>
            <a-button @click="goBack" size="large">取消</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import { createAssignment } from '@/api/assignment'
import { getCourseList } from '@/api/course'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const submitting = ref(false)
const coursesLoading = ref(false)
const courseOptions = ref([])

let questionIdCounter = 1

// 题目类型常量
const QUESTION_TYPE_OPTIONS = [
  { value: 'essay', label: '论述题' },
  { value: 'short_answer', label: '简答题' },
  { value: 'python', label: 'Python 编程题' },
  { value: 'sql', label: 'SQL 语句题' },
  { value: 'report', label: '课程报告' },
]

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

const isCodeType = (t) => t === 'python' || t === 'sql'

const makeQuestion = () => ({
  id: questionIdCounter++,
  question_type: 'essay',
  content: '',
  score: 10,
  standard_answer: '',
  test_cases: [],
  grading_rubric: '',
})

const makeEmptyTestCase = () => ({ input: '', output: '', description: '' })

const form = reactive({
  course_id: route.query.course_id ? Number(route.query.course_id) : undefined,
  title: '',
  description: '',
  start_time: null,
  end_time: null,
  questions: [makeQuestion()],
})

const rules = {
  course_id: [{ required: true, message: '请选择所属课程', type: 'number' }],
  title: [{ required: true, message: '请输入作业标题' }],
  start_time: [{ required: true, message: '请选择开始时间' }],
  end_time: [{ required: true, message: '请选择截止时间' }],
}

const loadCourses = async () => {
  coursesLoading.value = true
  try {
    const res = await getCourseList({ mine: true, page_size: 100 })
    if (res.success) {
      courseOptions.value = (res.data || []).map((c) => ({
        value: c.id,
        label: c.course_name,
      }))
    }
  } catch {
    // silent
  } finally {
    coursesLoading.value = false
  }
}

onMounted(loadCourses)

const totalScore = computed(() => {
  return form.questions.reduce((sum, q) => sum + (Number(q.score) || 0), 0)
})

const addQuestion = () => {
  form.questions.push(makeQuestion())
}

const removeQuestion = (index) => {
  form.questions.splice(index, 1)
}

// 切换题目类型时同步初始化对应的字段
const handleTypeChange = (q) => {
  if (isCodeType(q.question_type)) {
    if (!q.test_cases || q.test_cases.length === 0) {
      q.test_cases = [makeEmptyTestCase()]
    }
  } else {
    q.test_cases = []
  }
  if (q.question_type !== 'report') {
    q.grading_rubric = ''
  }
}

const addTestCase = (q) => {
  if (!q.test_cases) q.test_cases = []
  q.test_cases.push(makeEmptyTestCase())
}

const removeTestCase = (q, index) => {
  q.test_cases.splice(index, 1)
}

const getStandardAnswerLabel = (type) => {
  if (type === 'python') return '参考实现（Python 代码）'
  if (type === 'sql') return '参考 SQL 语句'
  if (type === 'report') return '参考标准 / 评分要点'
  return '标准答案'
}

const getStandardAnswerPlaceholder = (type) => {
  if (type === 'python') return '请输入参考的 Python 实现代码'
  if (type === 'sql') return '请输入参考的 SQL 语句'
  if (type === 'report') return '请描述报告的评分要求、参考要点等'
  return '请输入标准答案'
}

const getStandardAnswerRows = (type) => {
  if (isCodeType(type)) return 6
  if (type === 'report') return 5
  return 3
}

// 校验代码题必须有非空测试用例
const validateCodeQuestions = () => {
  for (let i = 0; i < form.questions.length; i++) {
    const q = form.questions[i]
    if (isCodeType(q.question_type)) {
      const valid = (q.test_cases || []).some(
        (tc) => (tc.input || tc.output || tc.description || '').toString().trim()
      )
      if (!valid) {
        message.error(`第 ${i + 1} 题（${QUESTION_TYPE_LABEL[q.question_type]}）必须至少填写一个非空测试用例`)
        return false
      }
    }
  }
  return true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!validateCodeQuestions()) return

  submitting.value = true
  try {
    const data = {
      course_id: form.course_id,
      title: form.title,
      description: form.description || '',
      start_time: form.start_time?.toISOString(),
      end_time: form.end_time?.toISOString(),
      total_score: totalScore.value,
      questions: form.questions.map((q) => {
        const item = {
          id: q.id,
          question_type: q.question_type,
          content: q.content,
          score: q.score,
          standard_answer: q.standard_answer,
        }
        if (isCodeType(q.question_type)) {
          item.test_cases = (q.test_cases || [])
            .filter((tc) => (tc.input || tc.output || tc.description || '').toString().trim())
            .map((tc) => ({
              input: tc.input || '',
              output: tc.output || '',
              description: tc.description || '',
            }))
        }
        if (q.question_type === 'report' && q.grading_rubric) {
          item.grading_rubric = q.grading_rubric
        }
        return item
      }),
    }

    const res = await createAssignment(data)
    if (res.success) {
      message.success('创建成功')
      router.push({ name: 'AssignmentDetail', params: { id: res.data.id } })
    } else {
      message.error(res.message || '创建失败')
    }
  } catch (e) {
    message.error(e.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

const goBack = () => router.back()
</script>

<style scoped>
.assignment-form-container {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}
.question-block {
  margin-bottom: 16px;
}
.question-card {
  border: 1px solid #e8e8e8;
}
.add-question-btn {
  margin-top: 8px;
  margin-bottom: 16px;
}
.code-input :deep(textarea) {
  font-family: 'Fira Code', 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  background: #f6f8fa;
}
.test-cases-block {
  margin-bottom: 16px;
}
.test-case-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.test-case-index {
  display: inline-block;
  width: 60px;
  font-size: 13px;
  color: #666;
  flex-shrink: 0;
}
</style>
