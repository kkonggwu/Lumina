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
CREATE TABLE assignment (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '作业ID',
    course_id INT NOT NULL COMMENT '课程ID',
    teacher_id INT NOT NULL COMMENT '教师ID',
    title VARCHAR(200) NOT NULL COMMENT '作业标题',
    description TEXT COMMENT '作业描述',
    questions JSON NOT NULL COMMENT '题目列表(JSON格式)',
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
CREATE TABLE submission (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '提交ID',
    assignment_id INT NOT NULL COMMENT '作业ID',
    student_id INT NOT NULL COMMENT '学生ID',
    answers JSON COMMENT '学生答案(JSON格式)',
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
CREATE TABLE grade (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '评分ID',
    submission_id INT NOT NULL COMMENT '提交ID',
    grading_rubric JSON NOT NULL COMMENT '评分细则(JSON格式)',
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