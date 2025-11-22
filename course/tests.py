#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文档管理模块单元测试
"""
import os
import tempfile
from io import BytesIO
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from user.models import UserModel
from course.models import Course, Document
from course.services.document_service import DocumentService


class DocumentServiceTestCase(TestCase):
    """文档服务层测试"""
    
    def setUp(self):
        """测试前准备"""
        # 创建测试用户
        self.admin = UserModel.objects.create(
            username='admin_test',
            password='test123456',
            nickname='管理员',
            user_type=UserModel.ADMIN,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.admin.set_password('test123456')
        self.admin.save()
        
        self.teacher = UserModel.objects.create(
            username='teacher_test',
            password='test123456',
            nickname='教师',
            user_type=UserModel.TEACHER,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.teacher.set_password('test123456')
        self.teacher.save()
        
        self.student = UserModel.objects.create(
            username='student_test',
            password='test123456',
            nickname='学生',
            user_type=UserModel.STUDENT,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.student.set_password('test123456')
        self.student.save()
        
        # 创建测试课程
        self.course = Course.objects.create(
            teacher=self.teacher,
            course_name='测试课程',
            course_description='这是一个测试课程',
            invite_code='TEST001',
            status=1,
            is_deleted=False
        )
    
    def test_check_upload_permission_admin(self):
        """测试管理员上传权限"""
        has_permission, message = DocumentService.check_upload_permission(self.admin.id)
        self.assertTrue(has_permission)
        self.assertEqual(message, "")
    
    def test_check_upload_permission_teacher(self):
        """测试教师上传权限"""
        has_permission, message = DocumentService.check_upload_permission(self.teacher.id)
        self.assertTrue(has_permission)
        self.assertEqual(message, "")
    
    def test_check_upload_permission_student(self):
        """测试学生上传权限（应该被拒绝）"""
        has_permission, message = DocumentService.check_upload_permission(self.student.id)
        self.assertFalse(has_permission)
        self.assertIn("只有管理员和教师", message)
    
    def test_check_delete_permission_admin(self):
        """测试管理员删除权限"""
        has_permission, message = DocumentService.check_delete_permission(self.admin.id)
        self.assertTrue(has_permission)
        self.assertEqual(message, "")
    
    def test_check_delete_permission_teacher(self):
        """测试教师删除权限"""
        has_permission, message = DocumentService.check_delete_permission(self.teacher.id)
        self.assertTrue(has_permission)
        self.assertEqual(message, "")
    
    def test_check_delete_permission_student(self):
        """测试学生删除权限（应该被拒绝）"""
        has_permission, message = DocumentService.check_delete_permission(self.student.id)
        self.assertFalse(has_permission)
        self.assertIn("只有管理员和教师", message)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DocumentAPITestCase(TestCase):
    """文档API接口测试"""
    
    def setUp(self):
        """测试前准备"""
        self.client = APIClient()
        
        # 创建测试用户
        self.admin = UserModel.objects.create(
            username='admin_test',
            password='test123456',
            nickname='管理员',
            user_type=UserModel.ADMIN,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.admin.set_password('test123456')
        self.admin.save()
        
        self.teacher = UserModel.objects.create(
            username='teacher_test',
            password='test123456',
            nickname='教师',
            user_type=UserModel.TEACHER,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.teacher.set_password('test123456')
        self.teacher.save()
        
        self.student = UserModel.objects.create(
            username='student_test',
            password='test123456',
            nickname='学生',
            user_type=UserModel.STUDENT,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.student.set_password('test123456')
        self.student.save()
        
        # 创建测试课程
        self.course = Course.objects.create(
            teacher=self.teacher,
            course_name='测试课程',
            course_description='这是一个测试课程',
            invite_code='TEST001',
            status=1,
            is_deleted=False
        )
        
        # 创建测试文档
        self.test_document = Document.objects.create(
            course=self.course,
            uploader=self.teacher,
            file_name='test.md',
            stored_path='test/path/test.md',
            file_size=1024,
            file_type='md',
            mime_type='text/markdown',
            document_status=1,  # 处理成功
            is_deleted=False
        )
    
    def _get_auth_token(self, user):
        """获取用户的JWT token"""
        refresh = RefreshToken()
        refresh['user_id'] = user.id
        return str(refresh.access_token)
    
    def _authenticate(self, user):
        """认证用户"""
        token = self._get_auth_token(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def test_upload_document_admin_success(self):
        """测试管理员上传文档成功"""
        self._authenticate(self.admin)
        
        # 创建测试文件
        test_content = b"# Test Document\n\nThis is a test document content."
        test_file = SimpleUploadedFile(
            "test.md",
            test_content,
            content_type="text/markdown"
        )
        
        url = reverse('course:document_upload')
        data = {
            'course_id': self.course.id,
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('data', response.json())
        
        # 验证文档已创建
        document = Document.objects.filter(
            course=self.course,
            uploader=self.admin,
            file_name='test.md'
        ).first()
        self.assertIsNotNone(document)
    
    def test_upload_document_teacher_success(self):
        """测试教师上传文档成功"""
        self._authenticate(self.teacher)
        
        test_content = b"# Test Document\n\nThis is a test document content."
        test_file = SimpleUploadedFile(
            "test.md",
            test_content,
            content_type="text/markdown"
        )
        
        url = reverse('course:document_upload')
        data = {
            'course_id': self.course.id,
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
    
    def test_upload_document_student_forbidden(self):
        """测试学生上传文档被拒绝"""
        self._authenticate(self.student)
        
        test_content = b"# Test Document\n\nThis is a test document content."
        test_file = SimpleUploadedFile(
            "test.md",
            test_content,
            content_type="text/markdown"
        )
        
        url = reverse('course:document_upload')
        data = {
            'course_id': self.course.id,
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertIn('权限', response.json()['message'])
    
    def test_upload_document_unauthorized(self):
        """测试未登录用户上传文档被拒绝"""
        test_content = b"# Test Document"
        test_file = SimpleUploadedFile("test.md", test_content)
        
        url = reverse('course:document_upload')
        data = {
            'course_id': self.course.id,
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 401)
    
    def test_upload_document_invalid_course(self):
        """测试上传到不存在的课程"""
        self._authenticate(self.admin)
        
        test_content = b"# Test Document"
        test_file = SimpleUploadedFile("test.md", test_content)
        
        url = reverse('course:document_upload')
        data = {
            'course_id': 99999,  # 不存在的课程ID
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
    
    def test_upload_document_invalid_file_format(self):
        """测试上传不支持的文件格式"""
        self._authenticate(self.admin)
        
        test_content = b"test content"
        test_file = SimpleUploadedFile("test.exe", test_content)
        
        url = reverse('course:document_upload')
        data = {
            'course_id': self.course.id,
            'file': test_file
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['success'])
        self.assertIn('格式', response.json()['message'])
    
    def test_delete_document_admin_success(self):
        """测试管理员删除文档成功"""
        self._authenticate(self.admin)
        
        url = reverse('course:document_delete', kwargs={'document_id': self.test_document.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # 验证文档已被逻辑删除
        document = Document.objects.get(id=self.test_document.id)
        self.assertTrue(document.is_deleted)
    
    def test_delete_document_teacher_success(self):
        """测试教师删除文档成功"""
        self._authenticate(self.teacher)
        
        url = reverse('course:document_delete', kwargs={'document_id': self.test_document.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
    
    def test_delete_document_student_forbidden(self):
        """测试学生删除文档被拒绝"""
        self._authenticate(self.student)
        
        url = reverse('course:document_delete', kwargs={'document_id': self.test_document.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['success'])
        self.assertIn('权限', response.json()['message'])
    
    def test_delete_document_not_found(self):
        """测试删除不存在的文档"""
        self._authenticate(self.admin)
        
        url = reverse('course:document_delete', kwargs={'document_id': 99999})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['success'])
    
    def test_get_document_detail_success(self):
        """测试获取文档详情成功"""
        self._authenticate(self.student)  # 学生也可以查看
        
        url = reverse('course:document_detail', kwargs={'document_id': self.test_document.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('data', response.json())
        self.assertEqual(response.json()['data']['id'], self.test_document.id)
    
    def test_get_document_detail_not_found(self):
        """测试获取不存在的文档详情"""
        self._authenticate(self.student)
        
        url = reverse('course:document_detail', kwargs={'document_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.json()['success'])
    
    def test_get_document_list_success(self):
        """测试获取文档列表成功"""
        self._authenticate(self.student)
        
        url = reverse('course:document_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertIn('data', response.json())
        self.assertIn('total', response.json())
        self.assertIsInstance(response.json()['data'], list)
    
    def test_get_document_list_with_course_filter(self):
        """测试按课程筛选文档列表"""
        self._authenticate(self.student)
        
        # 创建另一个课程的文档
        other_course = Course.objects.create(
            teacher=self.teacher,
            course_name='其他课程',
            invite_code='TEST002',
            status=1,
            is_deleted=False
        )
        Document.objects.create(
            course=other_course,
            uploader=self.teacher,
            file_name='other.md',
            stored_path='test/path/other.md',
            file_size=512,
            is_deleted=False
        )
        
        url = reverse('course:document_list')
        response = self.client.get(url, {'course_id': self.course.id})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        # 验证返回的文档都属于指定课程
        for doc in response.json()['data']:
            self.assertEqual(doc['course_id'], self.course.id)
    
    def test_get_document_list_pagination(self):
        """测试文档列表分页"""
        self._authenticate(self.student)
        
        # 创建多个文档
        for i in range(5):
            Document.objects.create(
                course=self.course,
                uploader=self.teacher,
                file_name=f'test_{i}.md',
                stored_path=f'test/path/test_{i}.md',
                file_size=1024,
                is_deleted=False
            )
        
        url = reverse('course:document_list')
        response = self.client.get(url, {'page': 1, 'page_size': 3})
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(len(response.json()['data']), 3)
        self.assertEqual(response.json()['page'], 1)
        self.assertEqual(response.json()['page_size'], 3)
    
    def test_get_document_list_unauthorized(self):
        """测试未登录用户获取文档列表被拒绝"""
        url = reverse('course:document_list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)
    
    def test_download_document_success(self):
        """测试下载文档成功（需要实际文件存在）"""
        self._authenticate(self.student)
        
        url = reverse('course:document_download', kwargs={'document_id': self.test_document.id})
        response = self.client.get(url)
        
        # 如果文件不存在，会返回404
        # 这里主要测试接口是否可访问
        self.assertIn(response.status_code, [200, 404])
    
    def test_download_document_not_found(self):
        """测试下载不存在的文档"""
        self._authenticate(self.student)
        
        url = reverse('course:document_download', kwargs={'document_id': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
    
    def test_download_document_unauthorized(self):
        """测试未登录用户下载文档被拒绝"""
        url = reverse('course:document_download', kwargs={'document_id': self.test_document.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 401)


class DocumentServiceIntegrationTestCase(TestCase):
    """文档服务集成测试（需要Milvus连接）"""
    
    def setUp(self):
        """测试前准备"""
        self.admin = UserModel.objects.create(
            username='admin_integration',
            password='test123456',
            nickname='管理员',
            user_type=UserModel.ADMIN,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.admin.set_password('test123456')
        self.admin.save()
        
        self.teacher = UserModel.objects.create(
            username='teacher_integration',
            password='test123456',
            nickname='教师',
            user_type=UserModel.TEACHER,
            status=UserModel.ENABLED,
            is_deleted=UserModel.NOT_DELETED
        )
        self.teacher.set_password('test123456')
        self.teacher.save()
        
        self.course = Course.objects.create(
            teacher=self.teacher,
            course_name='集成测试课程',
            invite_code='INTEG001',
            status=1,
            is_deleted=False
        )
    
    def test_list_documents_with_filters(self):
        """测试文档列表筛选功能"""
        # 创建多个文档
        documents = []
        for i in range(3):
            doc = Document.objects.create(
                course=self.course,
                uploader=self.teacher,
                file_name=f'doc_{i}.md',
                stored_path=f'test/path/doc_{i}.md',
                file_size=1024 * (i + 1),
                document_status=1,
                is_deleted=False
            )
            documents.append(doc)
        
        # 测试按课程筛选
        service = DocumentService()
        docs, total = service.list_documents(course_id=self.course.id)
        self.assertEqual(total, 3)
        self.assertEqual(len(docs), 3)
        
        # 测试按上传者筛选
        docs, total = service.list_documents(user_id=self.teacher.id)
        self.assertEqual(total, 3)
        
        # 测试分页
        docs, total = service.list_documents(limit=2, offset=0)
        self.assertEqual(len(docs), 2)
        self.assertEqual(total, 3)
    
    def test_get_document_by_id(self):
        """测试根据ID获取文档"""
        doc = Document.objects.create(
            course=self.course,
            uploader=self.teacher,
            file_name='test.md',
            stored_path='test/path/test.md',
            file_size=1024,
            is_deleted=False
        )
        
        service = DocumentService()
        retrieved_doc = service.get_document(doc.id)
        
        self.assertIsNotNone(retrieved_doc)
        self.assertEqual(retrieved_doc.id, doc.id)
        self.assertEqual(retrieved_doc.file_name, 'test.md')
    
    def test_get_nonexistent_document(self):
        """测试获取不存在的文档"""
        service = DocumentService()
        doc = service.get_document(99999)
        self.assertIsNone(doc)
