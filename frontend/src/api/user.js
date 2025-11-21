import request from './request'

// 用户注册
export const register = (data) => {
  return request({
    url: '/users/register/',
    method: 'post',
    data
  })
}

// 用户登录
export const login = (data) => {
  return request({
    url: '/users/login/',
    method: 'post',
    data
  })
}

// 获取用户信息
export const getUserInfo = (params) => {
  return request({
    url: '/users/info/',
    method: 'get',
    params
  })
}

// 获取用户列表
export const getUserList = (params) => {
  return request({
    url: '/users/list/',
    method: 'get',
    params
  })
}

// 更新用户信息
export const updateUser = (userId, data) => {
  return request({
    url: `/users/update/${userId}/`,
    method: 'put',
    data
  })
}

// 修改密码
export const changePassword = (data) => {
  return request({
    url: '/users/change-password/',
    method: 'post',
    data
  })
}

