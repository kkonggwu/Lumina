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

// 更新单题标准答案关键点
export const updateQuestionKeypoints = (
  assignmentId,
  questionId,
  keypoints
) => {
  return request({
    url: `/assignment/${assignmentId}/questions/${questionId}/keypoints/`,
    method: "put",
    data: { keypoints },
  });
};

// ==================== 提交与判题 ====================

export const submitAnswers = (assignmentId, answers, reportFiles = {}) => {
  const hasFiles = Object.values(reportFiles || {}).some((file) => !!file);
  if (!hasFiles) {
    return request({
      url: `/assignment/${assignmentId}/submit/`,
      method: "post",
      data: { answers },
    });
  }

  const formData = new FormData();
  formData.append("answers", JSON.stringify(answers || {}));
  Object.entries(reportFiles).forEach(([questionId, file]) => {
    if (file) {
      formData.append(`report_files_${questionId}`, file);
    }
  });

  return request({
    url: `/assignment/${assignmentId}/submit/`,
    method: "post",
    data: formData,
    timeout: 300000,
    headers: { "Content-Type": "multipart/form-data" },
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

// ==================== 教师人工判题 ====================

export const manualGradeSubmission = (assignmentId, submissionId, data) => {
  return request({
    url: `/assignment/${assignmentId}/submissions/${submissionId}/manual-grade/`,
    method: "post",
    data,
  });
};

// ==================== 教师查看指定提交详情 ====================

export const getSubmissionDetail = (assignmentId, submissionId) => {
  return request({
    url: `/assignment/${assignmentId}/submissions/${submissionId}/`,
    method: "get",
  });
};
