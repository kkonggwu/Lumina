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
              <a-popconfirm
                v-if="form.questions.length > 1"
                title="确定删除该题目？"
                @confirm="removeQuestion(index)"
              >
                <a-button type="link" danger size="small">删除</a-button>
              </a-popconfirm>
            </template>

            <a-form-item
              :label="`题目内容`"
              :name="['questions', index, 'content']"
              :rules="[{ required: true, message: '请输入题目内容' }]"
            >
              <a-textarea
                v-model:value="q.content"
                placeholder="请输入题目内容"
                :rows="2"
              />
            </a-form-item>

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
                  label="标准答案"
                  :name="['questions', index, 'standard_answer']"
                  :rules="[{ required: true, message: '请输入标准答案' }]"
                >
                  <a-textarea
                    v-model:value="q.standard_answer"
                    placeholder="请输入标准答案"
                    :rows="3"
                  />
                </a-form-item>
              </a-col>
            </a-row>
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

const makeQuestion = () => ({
  id: questionIdCounter++,
  content: '',
  score: 10,
  standard_answer: '',
})

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
    const res = await getCourseList()
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

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    const data = {
      course_id: form.course_id,
      title: form.title,
      description: form.description || '',
      start_time: form.start_time?.toISOString(),
      end_time: form.end_time?.toISOString(),
      total_score: totalScore.value,
      questions: form.questions.map((q) => ({
        id: q.id,
        content: q.content,
        score: q.score,
        standard_answer: q.standard_answer,
      })),
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
</style>
