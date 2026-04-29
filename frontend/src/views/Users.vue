<template>
  <div class="users-container">
    <div class="page-header">
      <h1>用户管理</h1>
      <div class="header-actions">
        <select v-model="filters.user_type" @change="loadUsers" class="filter-select">
          <option value="">全部用户</option>
          <option :value="0">管理员</option>
          <option :value="1">教师</option>
          <option :value="2">学生</option>
        </select>
        <button @click="showAddModal = true" class="add-btn">+ 添加用户</button>
      </div>
    </div>

    <div class="table-container">
      <table class="users-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>用户名</th>
            <th>昵称</th>
            <th>用户类型</th>
            <th>邮箱</th>
            <th>手机号</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ user.nickname }}</td>
            <td>
              <span :class="['user-type-badge', `type-${user.user_type}`]">
                {{ getUserTypeName(user.user_type) }}
              </span>
            </td>
            <td>{{ user.email || '-' }}</td>
            <td>{{ user.phone || '-' }}</td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td>
              <button @click="editUser(user)" class="action-btn edit">编辑</button>
              <button @click="changePassword(user)" class="action-btn password">改密</button>
              <button v-if="isAdmin" @click="confirmDelete(user)" class="action-btn delete">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      
      <div v-if="loading" class="loading">加载中...</div>
      <div v-if="!loading && users.length === 0" class="empty">暂无数据</div>
    </div>

    <!-- 添加/编辑用户模态框 -->
    <div v-if="showAddModal || editingUser" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <h2>{{ editingUser ? '编辑用户' : '添加用户' }}</h2>
        <form @submit.prevent="saveUser">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="userForm.username" type="text" required :disabled="!!editingUser" />
          </div>
          <div class="form-group">
            <label>昵称</label>
            <input v-model="userForm.nickname" type="text" required />
          </div>
          <div class="form-group">
            <label>用户类型</label>
            <select v-model="userForm.user_type">
              <option :value="0">管理员</option>
              <option :value="1">教师</option>
              <option :value="2">学生</option>
            </select>
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="userForm.email" type="email" />
          </div>
          <div class="form-group">
            <label>手机号</label>
            <input v-model="userForm.phone" type="tel" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="closeModal" class="btn-cancel">取消</button>
            <button type="submit" class="btn-submit">保存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 修改密码模态框 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click="showPasswordModal = false">
      <div class="modal-content" @click.stop>
        <h2>修改密码</h2>
        <form @submit.prevent="handleChangePassword">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="passwordForm.username" type="text" required />
          </div>
          <div class="form-group">
            <label>旧密码</label>
            <input v-model="passwordForm.old_password" type="password" required />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input v-model="passwordForm.new_password" type="password" required minlength="6" />
          </div>
          <div class="modal-actions">
            <button type="button" @click="showPasswordModal = false" class="btn-cancel">取消</button>
            <button type="submit" class="btn-submit">确认修改</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { getUserList, updateUser, changePassword as changePasswordApi, deleteUser as deleteUserApi } from '@/api/user'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

const users = ref([])
const loading = ref(false)
const showAddModal = ref(false)
const showPasswordModal = ref(false)
const editingUser = ref(null)

const filters = ref({
  user_type: ''
})

const userForm = ref({
  username: '',
  nickname: '',
  user_type: 2,
  email: '',
  phone: ''
})

const passwordForm = ref({
  username: '',
  old_password: '',
  new_password: ''
})

const loadUsers = async () => {
  loading.value = true
  try {
    const response = await getUserList({
      user_type: filters.value.user_type || undefined,
      page: 1,
      page_size: 100
    })
    if (response.success) {
      users.value = response.data || []
    }
  } catch (error) {
    console.error('加载用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

const getUserTypeName = (type) => {
  const typeMap = {
    0: '管理员',
    1: '教师',
    2: '学生'
  }
  return typeMap[type] || '未知'
}

const formatDate = (dateString) => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('zh-CN')
}

const editUser = (user) => {
  editingUser.value = user
  userForm.value = {
    username: user.username,
    nickname: user.nickname,
    user_type: user.user_type,
    email: user.email || '',
    phone: user.phone || ''
  }
}

const changePassword = (user) => {
  passwordForm.value = {
    username: user.username,
    old_password: '',
    new_password: ''
  }
  showPasswordModal.value = true
}

const saveUser = async () => {
  try {
    if (editingUser.value) {
      // 更新用户
      const response = await updateUser(editingUser.value.id, userForm.value)
      if (response.success) {
        alert('更新成功')
        closeModal()
        loadUsers()
      } else {
        alert(response.message || '更新失败')
      }
    } else {
      // 添加用户（这里需要调用注册接口，但通常管理员添加用户不需要密码）
      // 暂时提示需要用户自己注册
      alert('请使用注册功能添加新用户')
      closeModal()
    }
  } catch (error) {
    alert(error.message || '操作失败')
  }
}

const handleChangePassword = async () => {
  try {
    const response = await changePasswordApi(passwordForm.value)
    if (response.success) {
      alert('密码修改成功')
      showPasswordModal.value = false
    } else {
      alert(response.message || '密码修改失败')
    }
  } catch (error) {
    alert(error.message || '密码修改失败')
  }
}

const confirmDelete = (user) => {
  if (confirm(`确定要删除用户 "${user.nickname || user.username}" 吗？此操作不可恢复！`)) {
    handleDelete(user.id)
  }
}

const handleDelete = async (userId) => {
  try {
    const response = await deleteUserApi(userId)
    if (response.success) {
      alert('删除成功')
      loadUsers()
    } else {
      alert(response.message || '删除失败')
    }
  } catch (error) {
    console.error('删除失败:', error)
    alert(error.message || '删除失败')
  }
}

const closeModal = () => {
  showAddModal.value = false
  editingUser.value = null
  userForm.value = {
    username: '',
    nickname: '',
    user_type: 2,
    email: '',
    phone: ''
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-container {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 2px solid #f0f0f0;
}

.page-header h1 {
  font-size: 28px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.filter-select {
  padding: 10px 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}

.add-btn {
  padding: 10px 20px;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s, box-shadow 0.2s;
}

.add-btn:hover {
  background: #1d4ed8;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
}

.table-container {
  overflow-x: auto;
}

.users-table {
  width: 100%;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: 15px;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.users-table th {
  background: #f8f9fa;
  font-weight: bold;
  color: #333;
}

.users-table tr:hover {
  background: #f8f9fa;
}

.user-type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
}

.user-type-badge.type-0 {
  background: #ffe5e5;
  color: #ff4757;
}

.user-type-badge.type-1 {
  background: #e5f3ff;
  color: #3742fa;
}

.user-type-badge.type-2 {
  background: #e5ffe5;
  color: #2ed573;
}

.action-btn {
  padding: 6px 12px;
  margin-right: 8px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn.edit {
  background: #e5f3ff;
  color: #3742fa;
}

.action-btn.password {
  background: #fff4e5;
  color: #ffa502;
}

.action-btn.delete {
  background: #ffe5e5;
  color: #ff4757;
}

.action-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 30px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-content h2 {
  margin-bottom: 20px;
  color: #333;
}

.modal-content .form-group {
  margin-bottom: 20px;
}

.modal-content label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-weight: 500;
}

.modal-content input,
.modal-content select {
  width: 100%;
  padding: 10px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
}

.modal-content input:focus,
.modal-content select:focus {
  outline: none;
  border-color: #2563eb;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}

.btn-cancel,
.btn-submit {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-cancel {
  background: #f0f0f0;
  color: #333;
}

.btn-submit {
  background: #2563eb;
  color: white;
}

.btn-submit:hover {
  background: #1d4ed8;
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.22);
}
</style>

