<template>
  <div class="assignment-form-container">
    <a-page-header title="编辑作业" @back="goBack" />

    <a-spin :spinning="pageLoading">
      <a-card :bordered="false" v-if="loaded">
        <a-form
          :model="form"
          :rules="rules"
          ref="formRef"
          layout="vertical"
          @finish="handleSubmit"
        >
          <a-row :gutter="24">
            <a-col :span="12">
              <a-form-item label="作业标题" name="title">
                <a-input v-model:value="form.title" placeholder="请输入作业标题" :maxlength="200" />
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item label="作业总分">
                <a-input-number :value="totalScore" disabled style="width: 100%" />
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

          <a-divider>题目列表（总分：{{ totalScore }}）</a-divider>

          <div v-for="(q, index) in form.questions" :key="q.id" class="question-block">
            <a-card size="small" :title="`第 ${index + 1} 题`" class="question-card">
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
                label="题目内容"
                :name="['questions', index, 'content']"
                :rules="[{ required: true, message: '请输入题目内容' }]"
              >
                <a-textarea v-model:value="q.content" placeholder="请输入题目内容" :rows="2" />
              </a-form-item>

              <a-row :gutter="16">
                <a-col :span="6">
                  <a-form-item
                    label="分值"
                    :name="['questions', index, 'score']"
                    :rules="[{ required: true, message: '请输入分值' }]"
                  >
                    <a-input-number v-model:value="q.score" :min="1" :max="100" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :span="18">
                  <a-form-item
                    label="标准答案"
                    :name="['questions', index, 'standard_answer']"
                    :rules="[{ required: true, message: '请输入标准答案' }]"
                  >
                    <a-textarea v-model:value="q.standard_answer" placeholder="请输入标准答案" :rows="3" />
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
                保存修改
              </a-button>
              <a-button @click="goBack" size="large">取消</a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-card>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { getAssignmentDetail, updateAssignment } from '@/api/assignment'

const route = useRoute()
const router = useRouter()
const formRef = ref()
const submitting = ref(false)
const pageLoading = ref(false)
const loaded = ref(false)

const assignmentId = computed(() => route.params.id)

let questionIdCounter = 100

const form = reactive({
  title: '',
  description: '',
  start_time: null,
  end_time: null,
  questions: [],
})

const rules = {
  title: [{ required: true, message: '请输入作业标题' }],
  start_time: [{ required: true, message: '请选择开始时间' }],
  end_time: [{ required: true, message: '请选择截止时间' }],
}

const totalScore = computed(() => {
  return form.questions.reduce((sum, q) => sum + (Number(q.score) || 0), 0)
})

const loadAssignment = async () => {
  pageLoading.value = true
  try {
    const res = await getAssignmentDetail(assignmentId.value)
    if (res.success) {
      const data = res.data
      form.title = data.title
      form.description = data.description || ''
      form.start_time = data.start_time ? dayjs(data.start_time) : null
      form.end_time = data.end_time ? dayjs(data.end_time) : null
      form.questions = (data.questions || []).map((q) => ({
        id: q.id,
        content: q.content || '',
        score: q.score || 10,
        standard_answer: q.standard_answer || '',
      }))
      if (form.questions.length > 0) {
        questionIdCounter = Math.max(...form.questions.map((q) => q.id)) + 1
      }
      loaded.value = true
    } else {
      message.error(res.message || '加载失败')
    }
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    pageLoading.value = false
  }
}

const addQuestion = () => {
  form.questions.push({
    id: questionIdCounter++,
    content: '',
    score: 10,
    standard_answer: '',
  })
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
    const res = await updateAssignment(assignmentId.value, data)
    if (res.success) {
      message.success('更新成功')
      router.push({ name: 'AssignmentDetail', params: { id: assignmentId.value } })
    } else {
      message.error(res.message || '更新失败')
    }
  } catch (e) {
    message.error(e.message || '更新失败')
  } finally {
    submitting.value = false
  }
}

const goBack = () => router.back()

onMounted(loadAssignment)
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
