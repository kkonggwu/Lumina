from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework.views import APIView
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    QAHistorySerializer
)
from .services.rag_service import RAGService


class ChatView(APIView):
    """
    普通问答视图
    支持学生和教师与大模型进行普通问答
    """
    permission_classes = [IsAuthenticated]  # 需要JWT认证

    @extend_schema(
        summary="普通问答",
        description="""
        普通问答接口，学生和教师都可以使用。
        
        **功能说明：**
        - 直接调用大模型进行问答，不依赖课程文档
        - 支持会话管理（通过session_id）
        - 自动保存问答历史
        
        **使用场景：**
        - 学生提问一般性问题
        - 教师咨询教学相关问题
        - 不需要基于课程文档的问答
        
        **注意事项：**
        - 需要登录认证
        - session_id可选，不提供时会自动生成
        - course_id可选，普通问答时可为空
        """,
        tags=["RAG问答"],
        request=ChatRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="问答成功",
                response=inline_serializer(
                    name="ChatResponseData",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": ChatResponseSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="chat"
    )
    def post(self, request):
        """
        普通问答接口
        """
        try:
            # 先检查认证状态（在验证数据之前）
            if not request.user.is_authenticated:
                # 尝试从请求头获取token信息用于调试
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token",
                    "debug": {
                        "auth_header_present": bool(auth_header),
                        "auth_header_prefix": auth_header[:10] if auth_header else None,
                        "user_type": str(type(request.user)),
                        "is_authenticated": request.user.is_authenticated
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 验证请求数据
            serializer = ChatRequestSerializer(data=request.data)
            
            if not serializer.is_valid():
                return JsonResponse({
                    "success": False,
                    "message": "请求参数验证失败",
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取验证后的数据
            validated_data = serializer.validated_data
            question = validated_data.get("question")
            session_id = validated_data.get("session_id")
            course_id = validated_data.get("course_id")
            
            # 从TokenUser中获取user_id
            # TokenUser对象：根据SIMPLE_JWT配置，USER_ID_CLAIM是'user_id'
            # TokenUser.id 属性就是token中的user_id值
            user_id = request.user.id
            
            if not user_id:
                # 调试信息：如果无法获取user_id，返回详细信息
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"无法获取user_id. request.user类型: {type(request.user)}, 属性: {dir(request.user)}")
                
                return JsonResponse({
                    "success": False,
                    "message": "无法从JWT token中获取用户ID",
                    "debug": {
                        "user_type": str(type(request.user)),
                        "user_attrs": [attr for attr in dir(request.user) if not attr.startswith('_')]
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)

            # 调用RAG服务进行问答
            rag_service = RAGService()
            success, message, qa_history = rag_service.chat_sync_basic(
                user_id=user_id,
                question=question,
                session_id=session_id,
                course_id=course_id
            )

            if success and qa_history:
                # 序列化返回数据
                response_data = ChatResponseSerializer(qa_history).data

                return JsonResponse({
                    "success": True,
                    "message": message,
                    "data": response_data
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": message
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"问答过程中发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatRagView(APIView):
    """
    RAG 对话
    """
    permission_classes = [IsAuthenticated]
    @extend_schema(
        summary="RAG 问答",
        description="""
        RAG增强问答接口，学生和教师都可以使用。
        
        **功能说明：**
        - 使用RAG技术增强大模型回答
        - 基于课程文档进行问答
        - 支持会话管理（通过session_id）
        - 自动保存问答历史
        
        **使用场景：**
        - 学生提问课程相关问题
        - 教师咨询教学资料相关问题
        - 需要基于课程文档的问答
        
        **注意事项：**
        - 需要登录认证
        - session_id可选，不提供时会自动生成
        - course_id必填，用于指定查询的课程文档范围
        """,
        tags = ["RAG问答"],
        request=ChatRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="RAG问答成功",
                response=inline_serializer(
                    name="RAGChatResponseData",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": ChatResponseSerializer()
                    }
                )
            ),
            400: OpenApiResponse(description="请求参数错误"),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        }
    )
    def post(self, request):
        """
        使用 RAG 来增强 AI 回答（流式响应）
        :param request:
        :return: StreamingHttpResponse 对象（SSE格式）
        """
        try:
            # 先检查认证状态（在验证数据之前）
            if not request.user.is_authenticated:
                # 尝试从请求头获取token信息用于调试
                auth_header = request.META.get('HTTP_AUTHORIZATION', '')
                return Response({
                    'code': 401,
                    'message': '未登录，请先登录获取JWT token',
                    'data': {
                        'debug': {
                            'auth_header_present': bool(auth_header),
                            'auth_header_prefix': auth_header[:10] if auth_header else None,
                            'user_type': str(type(request.user)),
                            'is_authenticated': request.user.is_authenticated
                        }
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)

            # 验证请求数据
            serializer = ChatRequestSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response({
                    'code': 400,
                    'message': '请求参数验证失败',
                    'data': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            # 获取验证后的数据
            validated_data = serializer.validated_data
            question = validated_data.get("question")
            session_id = validated_data.get("session_id")
            course_id = validated_data.get("course_id")
            
            # 从TokenUser中获取user_id
            user_id = request.user.id
            
            if not user_id:
                return Response({
                    'code': 401,
                    'message': '无法从JWT token中获取用户ID',
                    'data': None
                }, status=status.HTTP_401_UNAUTHORIZED)

            # 调用RAG服务进行增强问答（流式响应）
            rag_service = RAGService()
            response = rag_service.chat_using_rag(
                user_id=user_id,
                question=question,
                session_id=session_id,
                course_id=course_id,
                top_k=3
            )

            # 如果返回的是StreamingHttpResponse对象，直接返回
            if hasattr(response, '__class__') and response.__class__.__name__ == 'StreamingHttpResponse':
                return response
            # 处理错误情况（如果返回了错误元组）
            elif isinstance(response, tuple) and len(response) == 3:
                success, message, _ = response
                if not success:
                    return Response({
                        'code': 500,
                        'message': message or 'RAG问答失败',
                        'data': None
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # 默认错误响应
            return Response({
                'code': 500,
                'message': 'RAG问答服务返回了未知格式的响应',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f'RAG问答接口错误: {str(e)}', exc_info=True)
            return Response({
                'code': 500,
                'message': f'服务器内部错误: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ChatHistoryView(APIView):
    """
    获取问答历史视图
    """
    permission_classes = [IsAuthenticated]  # 需要JWT认证

    @extend_schema(
        summary="获取问答历史",
        description="""
        获取用户的问答历史记录。
        
        **功能说明：**
        - 可以按会话ID筛选
        - 可以按课程ID筛选
        - 支持分页（通过limit参数）
        
        **查询参数：**
        - session_id: 会话ID（可选）
        - course_id: 课程ID（可选）
        - limit: 返回记录数量（默认10，最大100）
        """,
        tags=["RAG问答"],
        parameters=[
            {
                "name": "session_id",
                "in": "query",
                "description": "会话ID",
                "required": False,
                "schema": {"type": "string"}
            },
            {
                "name": "course_id",
                "in": "query",
                "description": "课程ID",
                "required": False,
                "schema": {"type": "integer"}
            },
            {
                "name": "limit",
                "in": "query",
                "description": "返回记录数量（默认10，最大100）",
                "required": False,
                "schema": {"type": "integer", "default": 10, "maximum": 100}
            }
        ],
        responses={
            200: OpenApiResponse(
                description="获取成功",
                response=inline_serializer(
                    name="ChatHistoryResponse",
                    fields={
                        "success": serializers.BooleanField(),
                        "message": serializers.CharField(),
                        "data": QAHistorySerializer(many=True),
                        "total": serializers.IntegerField()
                    }
                )
            ),
            401: OpenApiResponse(description="未登录"),
            500: OpenApiResponse(description="服务器内部错误")
        },
        operation_id="get_chat_history"
    )
    def get(self, request):
        """
        获取问答历史接口
        """
        try:
            # 从JWT token中获取用户ID
            if not request.user.is_authenticated:
                return JsonResponse({
                    "success": False,
                    "message": "未登录，请先登录获取JWT token"
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # 从TokenUser中获取user_id
            user_id = getattr(request.user, 'id', None) or getattr(request.user, 'user_id', None)
            
            if not user_id:
                return JsonResponse({
                    "success": False,
                    "message": "无法从JWT token中获取用户ID"
                }, status=status.HTTP_401_UNAUTHORIZED)

            # 获取查询参数
            session_id = request.GET.get("session_id")
            course_id = request.GET.get("course_id")
            limit = int(request.GET.get("limit", 10))

            # 限制最大数量
            if limit > 100:
                limit = 100
            if limit < 1:
                limit = 10

            # 转换course_id为整数（如果提供）
            if course_id:
                try:
                    course_id = int(course_id)
                except (ValueError, TypeError):
                    course_id = None

            # 调用服务获取历史记录
            rag_service = RAGService()
            history = rag_service.get_chat_history(
                user_id=user_id,
                session_id=session_id,
                course_id=course_id,
                limit=limit
            )

            # 序列化数据
            history_data = QAHistorySerializer(history, many=True).data

            return JsonResponse({
                "success": True,
                "message": "获取成功",
                "data": history_data,
                "total": len(history_data)
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"获取问答历史时发生错误: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
