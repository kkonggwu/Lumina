import request from './request'

// ==================== 课程管理接口 ====================

// 获取课程列表
export const getCourseList = (params) => {
  return request({
    url: '/course/courses/',
    method: 'get',
    params
  })
}

// 创建课程
export const createCourse = (data) => {
  return request({
    url: '/course/courses/',
    method: 'post',
    data
  })
}

// 获取课程详情
export const getCourseDetail = (courseId) => {
  return request({
    url: `/course/courses/${courseId}/`,
    method: 'get'
  })
}

// 更新课程
export const updateCourse = (courseId, data) => {
  return request({
    url: `/course/courses/${courseId}/`,
    method: 'put',
    data
  })
}

// 删除课程
export const deleteCourse = (courseId) => {
  return request({
    url: `/course/courses/${courseId}/delete/`,
    method: 'delete'
  })
}

// ==================== 选课管理接口 ====================

// 加入课程（通过邀请码）
export const joinCourse = (data) => {
  return request({
    url: '/course/enrollments/join/',
    method: 'post',
    data
  })
}

// 退出课程
export const leaveCourse = (courseId) => {
  return request({
    url: `/course/enrollments/${courseId}/leave/`,
    method: 'delete'
  })
}

// 获取课程学生列表
export const getCourseStudents = (courseId, params) => {
  return request({
    url: `/course/courses/${courseId}/students/`,
    method: 'get',
    params
  })
}

// 获取学生选课列表
export const getStudentCourses = (params) => {
  return request({
    url: '/course/enrollments/',
    method: 'get',
    params
  })
}


