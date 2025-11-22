from os import access

from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .user_service import UserService
from .serializers import (
    UserRegisterSerializer,
    UserLoginSerializer,
    ChangePasswordSerializer,
    UserSerializer, UserInfoSerializer
)


class UserRegisterView(APIView):
    """用户注册视图"""

    @extend_schema(
        summary="用户注册",
        description="""
        用户注册接口，支持管理员、教师、学生三种用户类型注册。

        **用户类型说明：**
        - 0: 管理员
        - 1: 教师  
        - 2: 学生（默认）

        **注意事项：**
        - 用户名必须唯一
        - 密码会自动加密存储
        - 邮箱和手机号为可选字段
        """,
        tags=["用户管理"],
        request=UserRegisterSerializer,
        responses={
            200: OpenApiResponse(
                description="注册成功",
                response=inline_serializer(
                    name="UserRegisterResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": UserSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="数据验证失败"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="user_register"
    )
    def post(self, request):
        """用户注册接口"""
        try:
            # 步骤1: 使用 UserRegisterSerializer 验证数据
            serializer = UserRegisterSerializer(data=request.data)

            # 验证失败会自动抛出异常并返回400错误
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "数据验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 步骤2: 获取验证后的数据（字典格式）
            validated_data = serializer.validated_data

            # 步骤3: 调用服务层进行注册
            # 使用字典解包，更简洁
            success, message, user = UserService.register(**validated_data)

            # 步骤4: 使用 UserSerializer 格式化返回数据
            if success and user:
                # UserSerializer 会自动处理：
                # - 密码不返回（write_only=True）
                # - 时间格式化
                # - user_type_name 字段生成
                user_data = UserSerializer(user).data

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "data": user_data
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"注册过程中发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserLoginView(APIView):
    """用户登录视图"""

    @extend_schema(
        summary="用户登录",
        description="""
        用户登录接口，验证用户名和密码。

        **功能说明：**
        - 验证用户凭据
        - 更新最后登录时间和IP
        - 返回用户基本信息

        **安全特性：**
        - 密码使用加密验证
        - 记录登录IP地址
        - 更新最后登录时间
        """,
        tags=["用户管理"],
        request=UserLoginSerializer,
        responses={
            200: OpenApiResponse(
                description="登录成功",
                response=inline_serializer(
                    name="UserLoginResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": UserSerializer(),
                        "access": serializers.CharField(),
                        "refresh": serializers.CharField(),
                    }
                )
            ),
            400: OpenApiResponse(description="数据验证失败"),
            401: OpenApiResponse(description="用户名或密码错误"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="user_login"
    )
    def post(self, request):
        """用户登录接口"""
        try:
            # 使用 UserLoginSerializer 验证登录数据
            serializer = UserLoginSerializer(data=request.data)

            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "数据验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取验证后的数据
            validated_data = serializer.validated_data
            username = validated_data.get("username")
            password = validated_data.get("password")

            # 获取客户端IP
            client_ip = request.META.get('REMOTE_ADDR')

            # 调用服务层进行登录
            success, message, user = UserService.login(
                username=username,
                password=password,
                ip=client_ip
            )

            # 使用 UserSerializer 格式化返回数据
            if success and user:
                user_data = UserSerializer(user).data
                
                # 为自定义UserModel创建JWT token
                # 由于UserModel不是Django的User模型，需要手动创建token
                from rest_framework_simplejwt.tokens import RefreshToken
                
                # 手动创建RefreshToken并设置user_id
                refresh = RefreshToken()
                # 根据SIMPLE_JWT配置，USER_ID_CLAIM是'user_id'
                refresh['user_id'] = user.id
                
                # access_token会自动从refresh token生成，包含相同的user_id
                access_token = refresh.access_token

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "data": user_data,
                    "access": str(access_token),
                    "refresh": str(refresh),
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"登录过程中发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserInfoView(APIView):
    """获取用户信息视图"""

    @extend_schema(
        summary="获取用户信息",
        description="""
        获取用户详细信息接口。

        **查询方式：**
        - 通过user_id查询
        - 通过username查询
        - 至少需要提供其中一个参数
        """,
        tags=["用户管理"],
        parameters=[
            {
                "name": "user_id",
                "in": "query",
                "description": "用户ID",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "username",
                "in": "query",
                "description": "用户名",
                "required": False,
                "schema": {"type": "string"}
            }
        ],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="UserInfoResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": UserSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="参数错误"),
            404: OpenApiResponse(description="用户不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_user_info"
    )
    def get(self, request):
        """获取用户信息接口"""
        try:
            # 获取请求参数
            user_id = request.GET.get("user_id")
            username = request.GET.get("username")

            # 验证参数
            if not user_id and not username:
                return JsonResponse({
                    "success": False,
                    "message": "请提供user_id或username参数"
                }, status=status.HTTP_400_BAD_REQUEST)

            # 根据参数获取用户信息
            user = None
            if user_id:
                user = UserService.get_user_by_id(user_id)
            elif username:
                user = UserService.get_user_by_username(username)

            # 使用 UserSerializer 格式化返回数据
            if user:
                # UserSerializer 会自动处理所有字段的格式化
                # 包括：时间格式、user_type_name、密码隐藏等
                user_data = UserSerializer(user).data

                return JsonResponse({
                    "success": True,
                    "message": "获取成功",
                    "data": user_data
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": "用户不存在"
                }, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取用户信息时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChangePasswordView(APIView):
    """修改密码视图"""

    @extend_schema(
        summary="修改密码",
        description="""
        修改用户密码接口。

        **功能说明：**
        - 需要验证旧密码
        - 新密码自动加密存储
        - 修改成功后建议重新登录
        """,
        tags=["用户管理"],
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="修改成功",
                response=inline_serializer(
                    name="ChangePasswordResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField()
                    }
                )
            ),
            400: OpenApiResponse(description="数据验证失败或旧密码错误"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="change_password"
    )
    def post(self, request):
        """
        修改密码接口
        :param request:
        :return:
        """
        try:
            # 使用 ChangePasswordSerializer 验证数据
            serializer = ChangePasswordSerializer(data=request.data)

            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "数据验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取验证后的数据
            validated_data = serializer.validated_data
            username = validated_data.get("username")
            old_password = validated_data.get("old_password")
            new_password = validated_data.get("new_password")
            
            # 从用户名获取用户ID（因为JWT认证可能未启用，使用username更可靠）
            user = UserService.get_user_by_username(username)
            if not user:
                return JsonResponse({
                    "success": False,
                    "message": "用户不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            user_id = user.id

            # 调用服务层修改密码
            success, message = UserService.change_password(
                user_id=user_id,
                username=username,
                old_password=old_password,
                new_password=new_password
            )

            # 返回响应
            if success:
                return JsonResponse({
                    "success": True,
                    "message": message
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"修改密码时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# 🎯 额外示例：如果需要用户列表接口
# ============================================

class UserListView(APIView):
    """用户列表视图"""

    @extend_schema(
        summary="获取用户列表",
        description="获取所有用户列表",
        tags=["用户管理"],
        parameters=[
            {
                "name": "user_type",
                "in": "query",
                "description": "用户类型筛选：0=管理员，1=教师，2=学生",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "page",
                "in": "query",
                "description": "页码",
                "required": False,
                "schema": {"type": "integer", "default": 1}
            },
            {
                "name": "page_size",
                "in": "query",
                "description": "每页数量",
                "required": False,
                "schema": {"type": "integer", "default": 10}
            }
        ],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="UserListResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": UserSerializer(many=True),  # 📌 many=True 表示列表
                        "total": serializers.IntegerField()
                    }
                )
            ),
        },
        operation_id="get_user_list"
    )
    def get(self, request):
        """获取用户列表接口"""
        try:
            # 获取查询参数
            user_type = request.GET.get("user_type")
            page = int(request.GET.get("page", 1))
            page_size = int(request.GET.get("page_size", 10))

            # 调用服务层获取用户列表
            users, total = UserService.get_user_list(
                user_type=user_type,
                page=page,
                page_size=page_size
            )

            # 📌 使用 UserSerializer 序列化多个对象
            # many=True 表示这是一个列表
            users_data = UserSerializer(users, many=True).data

            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": users_data,
                "total": total,
                "page": page,
                "page_size": page_size
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取用户列表时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# 🎯 额外示例：如果需要更新用户信息接口
# ============================================

class UserUpdateView(APIView):
    """用户信息更新视图（示例）"""

    @extend_schema(
        summary="更新用户信息",
        description="更新用户基本信息（不包括密码）",
        tags=["用户管理"],
        request=UserSerializer,  # 📌 直接使用 UserSerializer
        responses={
            200: OpenApiResponse(
                description="更新成功",
                response=inline_serializer(
                    name="UserUpdateResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": UserSerializer()
                    }
                )
            ),
        },
        operation_id="update_user"
    )
    def put(self, request, user_id):
        """更新用户信息接口"""
        try:
            # 获取用户
            user = UserService.get_user_by_id(user_id)
            if not user:
                return JsonResponse({
                    "success": False,
                    "message": "用户不存在"
                }, status=status.HTTP_404_NOT_FOUND)

            # 📌 使用 UserSerializer 验证并更新数据
            # partial=True 允许部分字段更新
            serializer = UserSerializer(user, data=request.data, partial=True)

            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "数据验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 📌 保存更新（会自动调用 serializer 的 update 方法）
            updated_user = serializer.save()

            # 返回更新后的用户数据
            user_data = UserSerializer(updated_user).data

            return JsonResponse({
                "success": True,
                "message": "更新成功",
                "data": user_data
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"更新用户信息时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================
# 🎯 删除用户接口
# ============================================

class UserDeleteView(APIView):
    """删除用户视图"""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="删除用户",
        description="""
        逻辑删除用户（仅管理员可以删除）。
        
        **功能说明：**
        - 仅管理员可以删除用户
        - 执行逻辑删除，不会物理删除数据
        - 删除后用户将无法登录
        """,
        tags=["用户管理"],
        responses={
            200: OpenApiResponse(
                description="删除成功",
                response=inline_serializer(
                    name="UserDeleteResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="权限不足，仅管理员可以删除用户"),
            404: OpenApiResponse(description="用户不存在"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="delete_user"
    )
    def delete(self, request, user_id):
        """删除用户接口"""
        try:
            # 检查认证
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 从TokenUser中获取当前用户ID
            current_user_id = request.user.id
            if not current_user_id:
                return JsonResponse({
                    "success": False,
                    "message": "无法从JWT token中获取用户ID"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 获取当前登录用户信息（用于权限检查）
            current_user = UserService.get_user_by_id(current_user_id)
            if not current_user:
                return JsonResponse({
                    "success": False,
                    "message": "当前用户不存在"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 检查权限：只有管理员可以删除用户
            if current_user.user_type != 0:  # 0 = 管理员
                return JsonResponse({
                    "success": False,
                    "message": "权限不足，仅管理员可以删除用户"
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 获取要删除的用户
            user = UserService.get_user_by_id(user_id)
            if not user:
                return JsonResponse({
                    "success": False,
                    "message": "用户不存在"
                }, status=status.HTTP_404_NOT_FOUND)
            
            # 不能删除自己
            if user.id == current_user_id:
                return JsonResponse({
                    "success": False,
                    "message": "不能删除自己的账号"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 执行逻辑删除
            success, message = UserService.delete_user(user_id)
            
            if success:
                return JsonResponse({
                    "success": True,
                    "message": message
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"删除用户时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)