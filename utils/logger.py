#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: logger.py
@Author: kkonggwu
@Date: 2025/11/13
@Version: 1.0
"""
import logging
import traceback
from typing import Optional, Any


class LoggerManager:
    """
    日志管理器，提供便捷的日志记录功能
    """
    
    def __init__(self, name: str = 'app'):
        """
        初始化日志管理器
        
        Args:
            name: 日志记录器名称
        """
        self.logger = logging.getLogger(name)
        self.name = name
    
    def debug(self, message: str, **kwargs):
        """
        记录调试级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        if kwargs:
            message = f"{message} | 上下文: {kwargs}"
        self.logger.debug(message)
    
    def info(self, message: str, **kwargs):
        """
        记录信息级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        if kwargs:
            message = f"{message} | 上下文: {kwargs}"
        self.logger.info(message)
    
    def warning(self, message: str, **kwargs):
        """
        记录警告级别日志
        
        Args:
            message: 日志消息
            **kwargs: 额外的上下文信息
        """
        if kwargs:
            message = f"{message} | 上下文: {kwargs}"
        self.logger.warning(message)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """
        记录错误级别日志
        
        Args:
            message: 日志消息
            exception: 异常对象（可选）
            **kwargs: 额外的上下文信息
        """
        if exception:
            error_trace = traceback.format_exc()
            message = f"{message} | 异常: {str(exception)} | 堆栈: {error_trace}"
        elif kwargs:
            message = f"{message} | 上下文: {kwargs}"
        self.logger.error(message)
    
    def critical(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """
        记录严重错误级别日志
        
        Args:
            message: 日志消息
            exception: 异常对象（可选）
            **kwargs: 额外的上下文信息
        """
        if exception:
            error_trace = traceback.format_exc()
            message = f"{message} | 异常: {str(exception)} | 堆栈: {error_trace}"
        elif kwargs:
            message = f"{message} | 上下文: {kwargs}"
        self.logger.critical(message)
    
    def log_request(self, request_method: str, request_path: str, status_code: int, 
                    duration: float = None, user_id: Any = None):
        """
        记录HTTP请求日志
        
        Args:
            request_method: HTTP方法
            request_path: 请求路径
            status_code: 状态码
            duration: 请求处理时间（秒，可选）
            user_id: 用户ID（可选）
        """
        message = f"HTTP {request_method} {request_path} - {status_code}"
        
        extra = {}
        if duration is not None:
            extra['duration_ms'] = round(duration * 1000, 2)
        if user_id is not None:
            extra['user_id'] = user_id
            
        if 200 <= status_code < 400:
            self.info(message, **extra)
        elif 400 <= status_code < 500:
            self.warning(message, **extra)
        else:
            self.error(message, **extra)


# 创建默认的日志管理器实例
def get_logger(name: str = 'app') -> LoggerManager:
    """
    获取日志管理器实例的便捷函数
    
    Args:
        name: 日志记录器名称
        
    Returns:
        LoggerManager实例
    """
    return LoggerManager(name)


# 创建全局默认日志记录器
logger = get_logger()