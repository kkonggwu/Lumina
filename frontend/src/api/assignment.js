import request from "./request";

// ==================== 作业 CRUD ====================

export const createAssignment = (data) => {
  return request({
    url: "/assignment/",
    method: "post",
    data,
  });
};

export const getAssignmentList = (params) => {
  return request({
    url: "/assignment/list/",
    method: "get",
    params,
  });
};

export const getAssignmentDetail = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/`,
    method: "get",
  });
};

export const updateAssignment = (assignmentId, data) => {
  return request({
    url: `/assignment/${assignmentId}/`,
    method: "put",
    data,
  });
};

export const deleteAssignment = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/delete/`,
    method: "delete",
  });
};

export const publishAssignment = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/publish/`,
    method: "post",
  });
};

// ==================== 提交与判题 ====================

export const submitAnswers = (assignmentId, answers) => {
  return request({
    url: `/assignment/${assignmentId}/submit/`,
    method: "post",
    data: { answers },
  });
};

export const analyzeStandardAnswers = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/analyze/`,
    method: "post",
    timeout: 300000,
  });
};

export const gradeAllSubmissions = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/grade-all/`,
    method: "post",
    timeout: 600000,
  });
};

// ==================== 查询 ====================

export const getSubmissionList = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/submissions/`,
    method: "get",
  });
};

export const getMySubmission = (assignmentId) => {
  return request({
    url: `/assignment/${assignmentId}/my-submission/`,
    method: "get",
  });
};
