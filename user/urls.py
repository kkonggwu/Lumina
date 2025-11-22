from django.urls import path
from .views import (
    UserRegisterView,
    UserLoginView,
    UserInfoView,
    ChangePasswordView,
    UserListView,
    UserUpdateView,
    UserDeleteView
)

# app_name 用于反向解析 URL
app_name = 'users'

urlpatterns = [
    # 用户注册
    # URL: /api/users/register/
    # 方法: POST
    path('register/', UserRegisterView.as_view(), name='register'),

    # 用户登录
    # URL: /api/users/login/
    # 方法: POST
    path('login/', UserLoginView.as_view(), name='login'),

    # 获取用户信息
    # URL: /api/users/info/?user_id=1 或 /api/users/info/?username=zhangsan
    # 方法: GET
    path('info/', UserInfoView.as_view(), name='user_info'),

    # 修改密码
    # URL: /api/users/change-password/
    # 方法: POST
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),

    # 用户列表（可选）
    # URL: /api/users/list/?page=1&page_size=10&user_type=2
    # 方法: GET
    path('list/', UserListView.as_view(), name='user_list'),
    
    # 更新用户信息
    # URL: /api/users/update/<user_id>/
    # 方法: PUT
    path('update/<int:user_id>/', UserUpdateView.as_view(), name='update_user'),
    
    # 删除用户
    # URL: /api/users/delete/<user_id>/
    # 方法: DELETE
    path('delete/<int:user_id>/', UserDeleteView.as_view(), name='delete_user'),
]