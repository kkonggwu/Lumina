<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-header">
        <h1>Lumina</h1>
        <p>高校课程与作业管理系统</p>
      </div>
      
      <div class="tabs">
        <button 
          :class="['tab', { active: activeTab === 'login' }]"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button 
          :class="['tab', { active: activeTab === 'register' }]"
          @click="activeTab = 'register'"
        >
          注册
        </button>
      </div>

      <!-- 登录表单 -->
      <form v-if="activeTab === 'login'" @submit.prevent="handleLogin" class="form">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="loginForm.username" 
            type="text" 
            placeholder="请输入用户名"
            required
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码"
            required
          />
        </div>
        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <div v-if="error" class="error-message">{{ error }}</div>
      </form>

      <!-- 注册表单 -->
      <form v-else @submit.prevent="handleRegister" class="form">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="registerForm.username" 
            type="text" 
            placeholder="请输入用户名（2-50个字符）"
            required
            minlength="2"
            maxlength="50"
          />
        </div>
        <div class="form-group">
          <label>昵称</label>
          <input 
            v-model="registerForm.nickname" 
            type="text" 
            placeholder="请输入昵称"
            required
            maxlength="50"
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="registerForm.password" 
            type="password" 
            placeholder="请输入密码（至少6个字符）"
            required
            minlength="6"
          />
        </div>
        <div class="form-group">
          <label>用户类型</label>
          <select v-model="registerForm.user_type">
            <option :value="2">学生</option>
            <option :value="1">教师</option>
            <option :value="0">管理员</option>
          </select>
        </div>
        <div class="form-group">
          <label>邮箱（可选）</label>
          <input 
            v-model="registerForm.email" 
            type="email" 
            placeholder="请输入邮箱"
          />
        </div>
        <div class="form-group">
          <label>手机号（可选）</label>
          <input 
            v-model="registerForm.phone" 
            type="tel" 
            placeholder="请输入手机号"
            maxlength="20"
          />
        </div>
        <button type="submit" :disabled="loading" class="submit-btn">
          {{ loading ? '注册中...' : '注册' }}
        </button>
        <div v-if="error" class="error-message">{{ error }}</div>
      </form>
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

const loginForm = ref({
  username: '',
  password: ''
})

const registerForm = ref({
  username: '',
  nickname: '',
  password: '',
  user_type: 2,
  email: '',
  phone: ''
})

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
    const result = await authStore.register(registerForm.value)
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

.tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 30px;
  border-bottom: 2px solid #f0f0f0;
}

.tab {
  flex: 1;
  padding: 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  transition: all 0.3s;
  position: relative;
}

.tab.active {
  color: #2563eb;
  font-weight: 600;
}

.tab.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 0;
  right: 0;
  height: 2px;
  background: #2563eb;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.form-group input,
.form-group select {
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.submit-btn {
  padding: 14px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, box-shadow 0.2s;
  margin-top: 10px;
}

.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

