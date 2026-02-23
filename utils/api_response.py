#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: api_response.py
@Author: kkonggwu
@Date: 2026/2/21
@Version: 1.0
"""
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, \
    HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一 API 响应工具类
用于规范化所有接口的返回格式，避免在 views 中重复构造 JsonResponse
"""
from django.http import JsonResponse
from rest_framework import status

class ApiResponse:
    """
    统一响应格式：
    {
        "success": true/false,
        "code": 200,
        "message": "提示信息",
        "data": { ... }
    }
    """

    @staticmethod
    def success(data=None, message="操作成功", http_status=HTTP_200_OK )-> JsonResponse:
        """
        成功响应
        :param data: 返回的数据体，默认为 None
        :param message: 提示信息
        :param code: 业务状态码
        :param http_status: HTTP 状态码
        """
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "data": data,
            },
            status=http_status,
        )

    @staticmethod
    def error(message="操作失败",data=None, http_status=HTTP_400_BAD_REQUEST) -> JsonResponse:
        """
        失败响应
        :param message: 错误提示信息
        :param code: 业务状态码
        :param data: 可选的错误详情（如序列化器错误字段）
        :param http_status: HTTP 状态码
        """
        return JsonResponse(
            {
                "success": False,
                "message": message,
                "data": data,
            },
            status=http_status,
        )

    @staticmethod
    def bad_request(message="请求参数错误", data=None) -> JsonResponse:
        """400 参数校验失败"""
        return ApiResponse.error(message=message, code=400, data=data, http_status=HTTP_400_BAD_REQUEST)

    @staticmethod
    def unauthorized(message="请先登录") -> JsonResponse:
        """401 未认证"""
        return ApiResponse.error(message=message, code=401, http_status=HTTP_401_UNAUTHORIZED)

    @staticmethod
    def forbidden(message="无权限执行此操作") -> JsonResponse:
        """403 无权限"""
        return ApiResponse.error(message=message, code=403, http_status=HTTP_403_FORBIDDEN)

    @staticmethod
    def not_found(message="资源不存在") -> JsonResponse:
        """404 资源不存在"""
        return ApiResponse.error(message=message, code=404, http_status=HTTP_404_NOT_FOUND)

    @staticmethod
    def server_error(message="服务器内部错误") -> JsonResponse:
        """500 服务器错误"""
        return ApiResponse.error(message=message, code=500, http_status=HTTP_500_INTERNAL_SERVER_ERROR)