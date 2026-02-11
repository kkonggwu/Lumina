create schema rag_project;
-- 创建用户表
CREATE TABLE user (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password VARCHAR(255) NOT NULL COMMENT '密码',
    nickname VARCHAR(50) NOT NULL COMMENT '昵称',
    user_type TINYINT NOT NULL DEFAULT 2 COMMENT '用户类型：0-管理员，1-教师，2-学生',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    avatar VARCHAR(255) COMMENT '头像URL',
    status TINYINT DEFAULT 1 COMMENT '状态：0-禁用，1-启用',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除：0-正常，1-删除',
    last_login_time DATETIME COMMENT '最后登录时间',
    last_login_ip VARCHAR(45) COMMENT '最后登录IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_username (username),
    INDEX idx_user_type (user_type),
    INDEX idx_status (status),
    INDEX idx_is_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 插入示例数据
INSERT INTO user (username, password, nickname, user_type, email, phone) VALUES
('admin', '123456789', '系统管理员', 0, 'admin@example.com', '13800138000'),
('teacher1', '123456789', '张老师', 1, 'teacher1@example.com', '13800138001'),
('teacher2', '123456789', '李老师', 1, 'teacher2@example.com', '13800138002'),
('student1', '123456789', '小明', 2, 'student1@example.com', '13800138003'),
('student2', '123456789', '小红', 2, 'student2@example.com', '13800138004');


-- 课程表（保持不变）
CREATE TABLE course (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '课程ID',
    teacher_id INT NOT NULL COMMENT '教师ID',
    course_name VARCHAR(100) NOT NULL COMMENT '课程名称',
    course_description TEXT COMMENT '课程描述',
    cover_image VARCHAR(255) COMMENT '封面图片URL',
    invite_code VARCHAR(20) NOT NULL UNIQUE COMMENT '课程邀请码',
    academic_year VARCHAR(20) COMMENT '学年',
    semester TINYINT COMMENT '学期：1-春季，2-秋季',
    max_students INT DEFAULT 100 COMMENT '最大学生数',
    is_public TINYINT DEFAULT 0 COMMENT '是否公开：0-私有，1-公开',
    status TINYINT DEFAULT 1 COMMENT '状态：0-草稿，1-已发布',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_invite_code (invite_code),
    INDEX idx_status (status)
#     FOREIGN KEY (teacher_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程表';

-- 选课关系表（直接关联课程）
CREATE TABLE enrollment (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '选课ID',
    course_id INT NOT NULL COMMENT '课程ID',
    student_id INT NOT NULL COMMENT '学生ID',
    enrollment_status TINYINT DEFAULT 1 COMMENT '选课状态：0-待审核，1-已加入，2-已退出',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '加入时间',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    UNIQUE KEY uk_course_student (course_id, student_id),
    INDEX idx_student_id (student_id),
    INDEX idx_course_id (course_id)
#     FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
#     FOREIGN KEY (student_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='选课关系表';

-- 文档表（关联课程）
CREATE TABLE document (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '文档ID',
    course_id INT NOT NULL COMMENT '课程ID',
    uploader_id INT NOT NULL COMMENT '上传者ID',
    file_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
    stored_path VARCHAR(500) NOT NULL COMMENT '存储路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    file_type VARCHAR(50) COMMENT '文件类型',
    mime_type VARCHAR(100) COMMENT 'MIME类型',
    document_status TINYINT DEFAULT 0 COMMENT '状态：0-上传中，1-处理成功，2-处理失败',
    processing_log TEXT COMMENT '处理日志',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_course_id (course_id),
    INDEX idx_uploader_id (uploader_id)
#     FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
#     FOREIGN KEY (uploader_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文档表';

-- 作业表（直接关联课程）
-- questions JSON 字段格式说明：
-- questions 是一个JSON数组，包含所有题目的信息。每个题目对象的结构如下：
-- {
--   "id": 1,                                          // 题目编号（整数）
--   "content": "题目内容描述",                         // 题目内容（字符串）
--   "score": 10,                                      // 该题分值（数字）
--   "question_type": "essay",                         // 题目类型：essay|coding|short_answer|multiple_choice
--   "standard_answer": "标准答案的完整文本",           // 标准答案（字符串）
--   "options": ["选项A", "选项B"],                     // 选项（可选，用于选择题）
--   "answer_keypoints": ["关键点1", "关键点2"],        // 分析出的关键点数组（由Analyzer自动生成）
--   "analysis_summary": "答案概括",                    // 答案总体概括（由Analyzer自动生成）
--   "analysis_quality": 0.95,                         // 分析质量评分 0-1（由Analyzer自动生成）
--   "difficulty_estimate": "medium",                  // 难度估计：easy|medium|hard（由Analyzer自动生成）
--   "analyzed": true,                                 // 是否已分析过（布尔值）
--   "analyzed_at": "2026-02-09T10:00:00"              // 分析时间（ISO时间戳）
-- }
-- 示例：
-- [
--   {
--     "id": 1,
--     "content": "请解释什么是冒泡排序",
--     "score": 10,
--     "question_type": "essay",
--     "standard_answer": "冒泡排序是一种简单的排序算法...",
--     "answer_keypoints": ["比较相邻元素", "交换位置", "多轮遍历"],
--     "analysis_quality": 0.92,
--     "analyzed": true
--   }
-- ]
CREATE TABLE assignment (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '作业ID',
    course_id INT NOT NULL COMMENT '课程ID',
    teacher_id INT NOT NULL COMMENT '教师ID',
    title VARCHAR(200) NOT NULL COMMENT '作业标题',
    description TEXT COMMENT '作业描述',
    questions JSON NOT NULL COMMENT '题目列表(JSON数组格式)-包含题目内容、标准答案、和Analyzer自动分析的关键点',
    total_score DECIMAL(5,2) NOT NULL COMMENT '作业总分',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '截止时间',
    assignment_status TINYINT DEFAULT 0 COMMENT '状态：0-草稿，1-已发布',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_course_id (course_id),
    INDEX idx_teacher_id (teacher_id),
    INDEX idx_end_time (end_time)
#     FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
#     FOREIGN KEY (teacher_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业表';

-- 作业提交表
-- answers JSON 字段格式说明：
-- answers 是一个JSON对象，key是题目ID，value是学生的答案内容（字符串）
-- 示例：
-- {
--   "1": "冒泡排序是一种简单的排序算法，通过比较相邻元素...",
--   "2": "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n)...",
--   "3": "正确答案是B"
-- }
CREATE TABLE submission (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '提交ID',
    assignment_id INT NOT NULL COMMENT '作业ID',
    student_id INT NOT NULL COMMENT '学生ID',
    answers JSON COMMENT '学生答案(JSON对象格式)-key为题目ID，value为答案内容',
    total_score DECIMAL(5,2) DEFAULT 0 COMMENT '得分',
    submission_status TINYINT DEFAULT 0 COMMENT '状态：0-未提交，1-已提交待批改，2-已批改，3-已过期',
    submitted_at DATETIME COMMENT '提交时间',
    graded_at DATETIME COMMENT '批改时间',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_assignment_student (assignment_id, student_id),
    INDEX idx_student_id (student_id),
    INDEX idx_assignment_id (assignment_id),
    INDEX idx_status (submission_status)
#     FOREIGN KEY (assignment_id) REFERENCES assignment(id) ON DELETE CASCADE,
#     FOREIGN KEY (student_id) REFERENCES user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='作业提交表';

-- 评分详情表
-- grading_rubric JSON 字段格式说明：
-- grading_rubric 是一个JSON对象，包含对每个题目的详细评分信息和反馈
-- 示例：
-- {
--   "1": {
--     "question_id": 1,
--     "student_answer": "学生的答案内容",
--     "score": 8,
--     "max_score": 10,
--     "comment": "缺少了一些关键点，但总体思路正确",
--     "missing_keypoints": ["关键点1", "关键点2"],
--     "extracted_keypoints": ["题目中提到的关键点"]
--   },
--   "2": {
--     "question_id": 2,
--     ...
--   }
-- }
CREATE TABLE grade (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '评分ID',
    submission_id INT NOT NULL COMMENT '提交ID',
    grading_rubric JSON NOT NULL COMMENT '评分细则(JSON对象格式)-包含每个题目的评分、反馈、缺失关键点等信息',
    overall_comment TEXT COMMENT '总体评语',
    voice_feedback_path VARCHAR(500) COMMENT '语音评语路径',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_submission (submission_id)
#     FOREIGN KEY (submission_id) REFERENCES submission(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='评分详情表';

-- 问答历史表
CREATE TABLE qa_history (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '历史ID',
    user_id INT NOT NULL COMMENT '用户ID',
    course_id INT COMMENT '关联课程ID',
    session_id VARCHAR(50) NOT NULL COMMENT '会话ID',
    question TEXT NOT NULL COMMENT '用户问题',
    answer TEXT NOT NULL COMMENT '系统回答',
    context_docs JSON COMMENT '参考文档信息',
    source_documents JSON COMMENT '来源文档(JSON格式)',
    prompt_tokens INT COMMENT '提示令牌数',
    completion_tokens INT COMMENT '完成令牌数',
    total_tokens INT COMMENT '总令牌数',
    feedback TINYINT COMMENT '用户反馈：0-否定，1-肯定',
    is_deleted TINYINT DEFAULT 0 COMMENT '逻辑删除',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_course_id (course_id),
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
#     FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
#     FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='问答历史表';