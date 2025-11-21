import { defineStore } from 'pinia'
import { login, register, getUserInfo } from '@/api/user'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    accessToken: localStorage.getItem('accessToken') || '',
    refreshToken: localStorage.getItem('refreshToken') || '',
    userInfo: JSON.parse(localStorage.getItem('userInfo') || 'null')
  }),

  getters: {
    isLoggedIn: (state) => !!state.accessToken,
    userType: (state) => state.userInfo?.user_type,
    isStudent: (state) => state.userInfo?.user_type === 2,
    isTeacher: (state) => state.userInfo?.user_type === 1,
    isAdmin: (state) => state.userInfo?.user_type === 0
  },

  actions: {
    async login(credentials) {
      try {
        const response = await login(credentials)
        if (response.success) {
          this.accessToken = response.access
          this.refreshToken = response.refresh
          this.userInfo = response.data
          
          localStorage.setItem('accessToken', response.access)
          localStorage.setItem('refreshToken', response.refresh)
          localStorage.setItem('userInfo', JSON.stringify(response.data))
          
          return { success: true, data: response.data }
        } else {
          return { success: false, message: response.message }
        }
      } catch (error) {
        return { success: false, message: error.message || '登录失败' }
      }
    },

    async register(userData) {
      try {
        const response = await register(userData)
        if (response.success) {
          // 注册成功后自动登录
          const loginResponse = await this.login({
            username: userData.username,
            password: userData.password
          })
          return loginResponse
        } else {
          return { success: false, message: response.message }
        }
      } catch (error) {
        return { success: false, message: error.message || '注册失败' }
      }
    },

    async fetchUserInfo() {
      try {
        const response = await getUserInfo({ username: this.userInfo?.username })
        if (response.success) {
          this.userInfo = response.data
          localStorage.setItem('userInfo', JSON.stringify(response.data))
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
      }
    },

    logout() {
      this.accessToken = ''
      this.refreshToken = ''
      this.userInfo = null
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('userInfo')
    }
  }
})

