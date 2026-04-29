<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>Lumina</h2>
        <p class="user-info">
          <span class="user-name">{{ userInfo?.nickname || userInfo?.username }}</span>
          <span class="user-type">{{ userTypeName }}</span>
        </p>
      </div>

      <nav class="sidebar-nav">
        <!-- 智能问答功能暂时下线：保留代码注释，后续需要恢复时取消注释即可。
        <router-link to="/chat" class="nav-item" :class="{ active: $route.path === '/chat' }">
          <span class="nav-icon">💬</span>
          <span class="nav-text">智能问答</span>
        </router-link>
        -->

        <router-link to="/courses" class="nav-item" :class="{ active: $route.path.startsWith('/courses') }">
          <span class="nav-icon">课</span>
          <span class="nav-text">课程管理</span>
        </router-link>

        <router-link to="/assignments" class="nav-item" :class="{ active: $route.path.startsWith('/assignments') }">
          <span class="nav-icon">作</span>
          <span class="nav-text">作业管理</span>
        </router-link>

        <router-link to="/documents" class="nav-item" :class="{ active: $route.path === '/documents' }">
          <span class="nav-icon">文</span>
          <span class="nav-text">文档管理</span>
        </router-link>

        <router-link v-if="!isStudent" to="/users" class="nav-item" :class="{ active: $route.path === '/users' }">
          <span class="nav-icon">用</span>
          <span class="nav-text">用户管理</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <button @click="handleLogout" class="logout-btn">
          <span class="nav-icon">退</span>
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
  background: #f5f7fb;
}

.sidebar {
  width: 248px;
  background: #001529;
  color: rgba(255, 255, 255, 0.88);
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 12px rgba(0, 21, 41, 0.18);
}

.sidebar-header {
  padding: 28px 22px 22px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.sidebar-header h2 {
  font-size: 22px;
  margin-bottom: 14px;
  font-weight: 700;
  letter-spacing: 0.2px;
  color: #ffffff;
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
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
  background: rgba(255, 255, 255, 0.12);
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
  color: rgba(255, 255, 255, 0.78);
  text-decoration: none;
  transition: background-color 0.2s, color 0.2s;
  margin: 4px 12px;
  border-radius: 10px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
}

.nav-item.active {
  background: #1677ff;
  color: #ffffff;
  font-weight: 600;
}

.nav-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
  font-size: 13px;
  font-weight: 600;
}

.nav-text {
  font-size: 16px;
}

.sidebar-footer {
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 15px 20px;
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.78);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.3s;
}

.logout-btn:hover {
  background: rgba(255, 77, 79, 0.16);
  color: #ffccc7;
}

.main-content {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}
</style>
