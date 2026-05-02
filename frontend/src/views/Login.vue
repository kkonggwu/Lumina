<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h1>Lumina</h1>
        <p>高校课程与作业管理系统</p>
      </div>

      <a-segmented :value="activeTab" :options="tabOptions" block class="auth-tabs"
        @update:value="activeTab = $event" />

      <!-- 登录表单 -->
      <a-form v-if="activeTab === 'login'" :model="loginForm" :rules="loginRules" layout="vertical" class="auth-form"
        @finish="handleLogin">
        <a-form-item label="用户名" name="username">
          <a-input :value="loginForm.username" @update:value="loginForm.username = $event" placeholder="请输入用户名"
            size="large" allow-clear />
        </a-form-item>

        <a-form-item label="密码" name="password">
          <a-input-password :value="loginForm.password" @update:value="loginForm.password = $event" placeholder="请输入密码"
            size="large" autocomplete="current-password" />
        </a-form-item>

        <a-button type="primary" html-type="submit" :loading="loading" block size="large" class="auth-submit">
          登录
        </a-button>
        <div v-if="error" class="error-message">{{ error }}</div>
      </a-form>

      <!-- 注册表单 -->
      <a-form v-else ref="registerFormRef" :model="registerForm" :rules="registerRules" layout="vertical"
        class="auth-form" @finish="handleRegister">
        <a-form-item label="用户名" name="username" has-feedback>
          <a-input :value="registerForm.username" @update:value="registerForm.username = $event"
            placeholder="请输入用户名（2-50个字符）" :maxlength="50" size="large" allow-clear />
        </a-form-item>

        <a-form-item label="昵称" name="nickname" has-feedback>
          <a-input :value="registerForm.nickname" @update:value="registerForm.nickname = $event" placeholder="请输入昵称"
            :maxlength="50" size="large" allow-clear />
        </a-form-item>

        <a-form-item label="密码" name="password" has-feedback>
          <a-input-password :value="registerForm.password" @update:value="registerForm.password = $event"
            placeholder="请输入密码（至少6个字符）" size="large" autocomplete="new-password" />
        </a-form-item>

        <a-form-item label="确认密码" name="confirm_password" has-feedback>
          <a-input-password :value="registerForm.confirm_password"
            @update:value="registerForm.confirm_password = $event" placeholder="请再次输入密码" size="large"
            autocomplete="new-password" />
        </a-form-item>

        <a-form-item label="用户类型" name="user_type">
          <a-select :value="registerForm.user_type" @update:value="registerForm.user_type = $event"
            placeholder="请选择用户类型" size="large" :options="userTypeOptions" />
        </a-form-item>

        <a-form-item label="邮箱" name="email">
          <a-input :value="registerForm.email" @update:value="registerForm.email = $event" placeholder="请输入邮箱"
            size="large" allow-clear />
        </a-form-item>

        <a-form-item label="手机号" name="phone">
          <a-input :value="registerForm.phone" @update:value="registerForm.phone = $event" placeholder="请输入手机号"
            :maxlength="20" size="large" allow-clear />
        </a-form-item>

        <a-button type="primary" html-type="submit" :loading="loading" block size="large" class="auth-submit">
          注册
        </a-button>
        <div v-if="error" class="error-message">{{ error }}</div>
      </a-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('login')
const loading = ref(false)
const error = ref('')
const registerFormRef = ref()

const tabOptions = [
  { value: 'login', label: '登录' },
  { value: 'register', label: '注册' }
]

const loginForm = ref({
  username: '',
  password: ''
})

const registerForm = ref({
  username: '',
  nickname: '',
  password: '',
  confirm_password: '',
  user_type: 2,
  email: '',
  phone: ''
})

const userTypeOptions = [
  { value: 2, label: '学生' },
  { value: 1, label: '教师' }
]

const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const validateConfirmPassword = async (_rule, value) => {
  if (!value) {
    return Promise.reject(new Error('请再次输入密码'))
  }
  if (value !== registerForm.value.password) {
    return Promise.reject(new Error('两次输入的密码不一致'))
  }
  return Promise.resolve()
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 50, message: '用户名长度需为 2-50 个字符', trigger: 'blur' }
  ],
  nickname: [
    { required: true, message: '请输入昵称', trigger: 'blur' },
    { max: 50, message: '昵称不能超过 50 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 个字符', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, validator: validateConfirmPassword, trigger: ['blur', 'change'] }
  ],
  user_type: [
    { required: true, message: '请选择用户类型', trigger: 'change' }
  ],
  email: [
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  phone: [
    { max: 20, message: '手机号不能超过 20 个字符', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  loading.value = true
  error.value = ''

  try {
    const result = await authStore.login(loginForm.value)
    if (result.success) {
      router.push('/')
    } else {
      error.value = result.message || '登录失败'
    }
  } catch (err) {
    error.value = err.message || '登录失败'
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  loading.value = true
  error.value = ''

  try {
    const payload = { ...registerForm.value }
    delete payload.confirm_password
    const result = await authStore.register(payload)
    if (result.success) {
      router.push('/')
    } else {
      error.value = result.message || '注册失败'
    }
  } catch (err) {
    error.value = err.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top left, rgba(22, 119, 255, 0.16), transparent 34%),
    linear-gradient(135deg, #eef4ff 0%, #f7f9fc 48%, #eaf1ff 100%);
  padding: 20px;
}

.login-box {
  background: white;
  border-radius: 16px;
  padding: 40px;
  width: 100%;
  max-width: 450px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.12);
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.login-header {
  text-align: center;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 34px;
  color: #111827;
  margin-bottom: 10px;
  font-weight: 700;
}

.login-header p {
  color: #666;
  font-size: 14px;
}

.auth-tabs {
  margin-bottom: 28px;
  padding: 4px;
  background: #f3f6fb;
  border-radius: 10px;
}

.auth-tabs :deep(.ant-segmented-item) {
  border-radius: 8px;
}

.auth-tabs :deep(.ant-segmented-item-label) {
  min-height: 38px;
  line-height: 38px;
  font-size: 15px;
  font-weight: 500;
}

.auth-form {
  margin-top: 2px;
}

.auth-form :deep(.ant-form-item) {
  margin-bottom: 18px;
}

.auth-form :deep(.ant-form-item-label > label) {
  color: #333;
  font-weight: 500;
}

.auth-submit {
  margin-top: 4px;
  height: 46px;
  border-radius: 8px;
  font-weight: 600;
}

.error-message {
  color: #ff4757;
  font-size: 14px;
  text-align: center;
  margin-top: 10px;
  padding: 10px;
  background: #ffe5e5;
  border-radius: 8px;
}
</style>
