from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from .models import UserModel

class UserService:
    """
    用户服务类，提供用户注册、登录、查询等功能
    """

    @staticmethod
    def register(username, password, nickname, user_type=UserModel.STUDENT, email=None, phone=None):
        """
        用户注册
        
        Args:
            username: 用户名
            password: 密码
            nickname: 昵称
            user_type: 用户类型，默认为学生
            email: 邮箱
            phone: 手机号
        
        Returns:
            tuple: (是否成功, 消息, 用户对象)
        """
        try:
            # 检查用户类型是否合法
            if user_type not in [UserModel.ADMIN, UserModel.TEACHER, UserModel.STUDENT]:
                return False, "无效的用户类型", None

            # 创建用户对象
            user = UserModel(
                username=username,
                password=password,
                nickname=nickname,
                user_type=user_type,
                email=email,
                phone=phone,
                status=UserModel.ENABLED,
                is_deleted=UserModel.NOT_DELETED
            )
            # 设置密码（自动加密）
            # user.set_password(password)
            # 保存用户
            user.save()
            
            return True, "注册成功", user
        except IntegrityError:
            return False, "用户名已存在", None
        except Exception as e:
            return False, f"注册失败: {str(e)}", None

    @staticmethod
    def login(username, password, ip=None):
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            ip: 登录IP地址
        
        Returns:
            tuple: (是否成功, 消息, 用户对象)
        """
        try:
            # 查询用户
            user = UserModel.objects.get(username=username, is_deleted=UserModel.NOT_DELETED)
            
            # 检查用户状态
            if user.status == UserModel.DISABLED:
                return False, "用户已被禁用", None
            
            # 验证密码
            if not user.check_password(password):
                return False, "用户名或密码错误", None
            
            # 更新登录信息
            user.update_last_login(ip)
            
            return True, "登录成功", user
        except ObjectDoesNotExist:
            return False, "用户名或密码错误", None
        except Exception as e:
            return False, f"登录失败: {str(e)}", None

    @staticmethod
    def get_user_by_id(user_id):
        """
        根据用户ID获取用户信息
        
        Args:
            user_id: 用户ID
        
        Returns:
            User: 用户对象，如果不存在返回None
        """
        try:
            return UserModel.objects.get(id=user_id, is_deleted=UserModel.NOT_DELETED)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_user_by_username(username):
        """
        根据用户名获取用户信息
        
        Args:
            username: 用户名
        
        Returns:
            User: 用户对象，如果不存在返回None
        """
        try:
            return UserModel.objects.get(username=username, is_deleted=UserModel.NOT_DELETED)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def update_user(user_id, **kwargs):
        """
        更新用户信息
        
        Args:
            user_id: 用户ID
            **kwargs: 要更新的用户信息
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            user = UserModel.objects.get(id=user_id, is_deleted=UserModel.NOT_DELETED)
            
            # 更新用户信息
            for key, value in kwargs.items():
                if key == 'password' and value:
                    # 特殊处理密码，需要加密
                    user.set_password(value)
                elif hasattr(user, key):
                    setattr(user, key, value)
            
            user.save()
            return True, "更新成功"
        except ObjectDoesNotExist:
            return False, "用户不存在"
        except Exception as e:
            return False, f"更新失败: {str(e)}"

    @staticmethod
    def change_password(user_id,username, old_password, new_password):
        """
        修改密码
        
        Args:
            user_id: 用户ID
            username: 用户名
            old_password: 原密码
            new_password: 新密码
        
        Returns:
            tuple: (是否成功, 消息)
        """
        try:
            user = UserModel.objects.get(id=username, is_deleted=UserModel.NOT_DELETED)
            
            # 验证原密码
            if not user.check_password(old_password):
                return False, "原密码错误"
            
            # 设置新密码
            user.set_password(new_password)
            user.save()
            
            return True, "密码修改成功"
        except ObjectDoesNotExist:
            return False, "用户不存在"
        except Exception as e:
            return False, f"密码修改失败: {str(e)}"

    @staticmethod
    def disable_user(user_id):
        """
        禁用用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        return UserService.update_user(user_id, status=UserModel.DISABLED)

    @staticmethod
    def enable_user(user_id):
        """
        启用用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        return UserService.update_user(user_id, status=UserModel.ENABLED)

    @staticmethod
    def delete_user(user_id):
        """
        逻辑删除用户
        
        Args:
            user_id: 用户ID
        
        Returns:
            tuple: (是否成功, 消息)
        """
        return UserService.update_user(user_id, is_deleted=UserModel.DELETED)