<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>🌟 Lumina</h2>
        <p class="user-info">
          <span class="user-name">{{ userInfo?.nickname || userInfo?.username }}</span>
          <span class="user-type">{{ userTypeName }}</span>
        </p>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/chat" class="nav-item" :class="{ active: $route.path === '/chat' }">
          <span class="nav-icon">💬</span>
          <span class="nav-text">智能问答</span>
        </router-link>

        <router-link to="/courses" class="nav-item" :class="{ active: $route.path.startsWith('/courses') }">
          <span class="nav-icon">📖</span>
          <span class="nav-text">课程管理</span>
        </router-link>

        <router-link to="/documents" class="nav-item" :class="{ active: $route.path === '/documents' }">
          <span class="nav-icon">📚</span>
          <span class="nav-text">文档管理</span>
        </router-link>

        <router-link v-if="!isStudent" to="/users" class="nav-item" :class="{ active: $route.path === '/users' }">
          <span class="nav-icon">👥</span>
          <span class="nav-text">用户管理</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button @click="handleLogout" class="logout-btn">
          <span class="nav-icon">🚪</span>
          <span class="nav-text">退出登录</span>
        </button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const userInfo = computed(() => authStore.userInfo)
const isStudent = computed(() => authStore.isStudent)

const userTypeName = computed(() => {
  const type = authStore.userType
  const typeMap = {
    0: '管理员',
    1: '教师',
    2: '学生'
  }
  return typeMap[type] || '未知'
})

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
}

.sidebar-header {
  padding: 30px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.sidebar-header h2 {
  font-size: 24px;
  margin-bottom: 15px;
  font-weight: bold;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 14px;
}

.user-name {
  font-weight: 500;
  font-size: 16px;
}

.user-type {
  opacity: 0.8;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 12px;
  display: inline-block;
  width: fit-content;
}

.sidebar-nav {
  flex: 1;
  padding: 20px 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px 20px;
  color: white;
  text-decoration: none;
  transition: all 0.3s;
  margin: 5px 10px;
  border-radius: 12px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  transform: translateX(5px);
}

.nav-item.active {
  background: rgba(255, 255, 255, 0.2);
  font-weight: bold;
}

.nav-icon {
  font-size: 20px;
}

.nav-text {
  font-size: 16px;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 15px 20px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateX(5px);
}

.main-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}
</style>
