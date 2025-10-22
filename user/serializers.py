from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    用户序列化器，用于用户数据的序列化和反序列化
    """
    # 只读字段
    user_type_name = serializers.SerializerMethodField()
    last_login_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    
    # 密码字段只写，不返回给前端
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'nickname', 'user_type', 'user_type_name',
            'email', 'phone', 'avatar', 'status', 'last_login_time',
            'last_login_ip', 'created_at', 'updated_at', 'password'
        ]
        read_only_fields = ['id', 'last_login_time', 'created_at', 'updated_at']
    
    def get_user_type_name(self, obj):
        """
        获取用户类型的中文名称
        """
        return dict(User.USER_TYPE_CHOICES).get(obj.user_type)
    
    def validate_username(self, value):
        """
        验证用户名
        """
        if not value or len(value) < 2 or len(value) > 50:
            raise serializers.ValidationError("用户名长度必须在2-50个字符之间")
        
        # 如果是更新操作，排除当前用户
        if self.instance:
            if User.objects.filter(username=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError("用户名已存在")
        else:
            # 注册操作，检查用户名是否已存在
            if User.objects.filter(username=value).exists():
                raise serializers.ValidationError("用户名已存在")
        
        return value
    
    def validate_password(self, value):
        """
        验证密码
        """
        if value and len(value) < 6:
            raise serializers.ValidationError("密码长度不能少于6个字符")
        return value
    
    def validate_user_type(self, value):
        """
        验证用户类型
        """
        valid_types = [User.ADMIN, User.TEACHER, User.STUDENT]
        if value not in valid_types:
            raise serializers.ValidationError("无效的用户类型")
        return value
    
    def create(self, validated_data):
        """
        创建用户时处理密码加密
        """
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        """
        更新用户时处理密码加密
        """
        password = validated_data.pop('password', None)
        
        # 更新其他字段
        for key, value in validated_data.items():
            setattr(instance, key, value)
        
        # 处理密码更新
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class UserRegisterSerializer(serializers.Serializer):
    """
    用户注册序列化器
    """
    username = serializers.CharField(
        max_length=50, 
        min_length=2,
        help_text="用户名，长度2-50个字符，必须唯一"
    )
    password = serializers.CharField(
        min_length=6,
        help_text="密码，至少6个字符"
    )
    nickname = serializers.CharField(
        max_length=50,
        help_text="昵称，长度不超过50个字符"
    )
    user_type = serializers.IntegerField(
        default=User.STUDENT,
        help_text="用户类型：0=管理员，1=教师，2=学生（默认）"
    )
    email = serializers.EmailField(
        allow_blank=True, 
        required=False,
        help_text="邮箱地址（可选）"
    )
    phone = serializers.CharField(
        max_length=20, 
        allow_blank=True, 
        required=False,
        help_text="手机号码（可选）"
    )
    
    def validate_username(self, value):
        """
        验证用户名是否已存在
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("用户名已存在")
        return value
    
    def validate_user_type(self, value):
        """
        验证用户类型是否有效
        """
        valid_types = [User.ADMIN, User.TEACHER, User.STUDENT]
        if value not in valid_types:
            raise serializers.ValidationError("无效的用户类型")
        return value


class UserLoginSerializer(serializers.Serializer):
    """
    用户登录序列化器
    """
    username = serializers.CharField(
        max_length=50,
        help_text="用户名，长度2-50个字符"
    )
    password = serializers.CharField(
        min_length=6,
        help_text="密码，至少6个字符"
    )


class ChangePasswordSerializer(serializers.Serializer):
    """
    修改密码序列化器
    """
    user_id = serializers.IntegerField(
        help_text="用户ID"
    )
    old_password = serializers.CharField(
        help_text="当前密码"
    )
    new_password = serializers.CharField(
        min_length=6,
        help_text="新密码，至少6个字符"
    )