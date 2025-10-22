from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from datetime import datetime


class User(models.Model):
    """
    用户模型，映射数据库中的user表
    """
    # 用户类型常量定义
    ADMIN = 0
    TEACHER = 1
    STUDENT = 2
    USER_TYPE_CHOICES = (
        (ADMIN, '管理员'),
        (TEACHER, '教师'),
        (STUDENT, '学生'),
    )

    # 状态常量定义
    DISABLED = 0
    ENABLED = 1
    STATUS_CHOICES = (
        (DISABLED, '禁用'),
        (ENABLED, '启用'),
    )

    # 逻辑删除常量定义
    NOT_DELETED = 0
    DELETED = 1
    DELETION_CHOICES = (
        (NOT_DELETED, '正常'),
        (DELETED, '删除'),
    )

    id = models.AutoField(primary_key=True, verbose_name='用户ID')
    username = models.CharField(max_length=50, unique=True, verbose_name='用户名')
    password = models.CharField(max_length=255, verbose_name='密码')
    nickname = models.CharField(max_length=50, verbose_name='昵称')
    user_type = models.IntegerField(
        choices=USER_TYPE_CHOICES,
        default=STUDENT,
        verbose_name='用户类型'
    )
    email = models.EmailField(max_length=100, blank=True, null=True, verbose_name='邮箱')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    avatar = models.CharField(max_length=255, blank=True, null=True, verbose_name='头像URL')
    status = models.IntegerField(
        choices=STATUS_CHOICES,
        default=ENABLED,
        verbose_name='状态'
    )
    is_deleted = models.IntegerField(
        choices=DELETION_CHOICES,
        default=NOT_DELETED,
        verbose_name='逻辑删除'
    )
    last_login_time = models.DateTimeField(blank=True, null=True, verbose_name='最后登录时间')
    last_login_ip = models.CharField(max_length=45, blank=True, null=True, verbose_name='最后登录IP')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        managed = False  # 不自动创建和管理表
        db_table = 'user'  # 数据库表名
        app_label = 'user'  # 明确指定应用标签
        verbose_name = '用户'
        verbose_name_plural = '用户管理'

    def set_password(self, raw_password):
        """
        设置密码，将明文密码加密存储
        """
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """
        验证密码
        """
        return check_password(raw_password, self.password)

    def update_last_login(self, ip=None):
        """
        更新最后登录信息
        """
        self.last_login_time = datetime.now()
        if ip:
            self.last_login_ip = ip
        self.save()

    def is_admin(self):
        """
        判断是否为管理员
        """
        return self.user_type == self.ADMIN

    def is_teacher(self):
        """
        判断是否为教师
        """
        return self.user_type == self.TEACHER

    def is_student(self):
        """
        判断是否为学生
        """
        return self.user_type == self.STUDENT

    def __str__(self):
        return self.nickname