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