"""
自定义JWT认证规则
用于支持自定义UserModel
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.models import TokenUser
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class CustomJWTAuthentication(JWTAuthentication):
    """
    自定义JWT认证类
    支持自定义UserModel（不需要Django User模型）
    """
    
    def get_user(self, validated_token):
        """
        重写get_user方法，不验证用户是否存在
        因为UserModel不是Django User，我们只需要从token中获取user_id
        直接返回TokenUser对象，不尝试从数据库获取用户
        """
        try:
            # 从token中获取user_id
            user_id = validated_token.get(api_settings.USER_ID_CLAIM)
            if not user_id:
                raise InvalidToken('Token contained no recognizable user identification')
        except KeyError:
            raise InvalidToken('Token contained no recognizable user identification')

        # 创建TokenUser对象
        # TokenUser的构造函数接受validated_token作为参数
        # 它会从token中提取user_id并设置到id属性
        return TokenUser(validated_token)


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    自定义JWT认证的OpenAPI扩展
    用于在Swagger UI中显示认证按钮
    """
    target_class = 'user.jwt_auth.CustomJWTAuthentication'  # 目标认证类
    name = 'BearerAuth'  # 认证名称

    def get_security_definition(self, auto_schema):
        """定义安全方案"""
        security_scheme = build_bearer_security_scheme_object(
            header_name='Authorization',
            token_prefix='Bearer',
            bearer_format='JWT'
        )
        # 手动添加description
        security_scheme['description'] = '输入JWT令牌，格式为：Bearer <token>'
        return security_scheme

