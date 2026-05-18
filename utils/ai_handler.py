#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: ai_handler.py
@Author: kkonggwu
@Date: 2025/11/10
@Version: 1.0
"""
import asyncio
import inspect
import os
from typing import List, Iterator, Optional, AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import PromptTemplate
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from config.config import APIConfig
from utils.logger import get_logger
from utils.prompt_template import CHAT_PROMPT_USING_CONTEXT

# 使用LoggerManager
logger = get_logger('ai_handler')


class AIHandler:
    def __init__(self, api_key: str, api_base: str, provider: str = "qwen"):
        """
        初始化API处理器
        :param api_key: API密钥
        :param api_base: API基础地址
        :param provider: 模型提供商 (qwen, openai, deepseek)
        """
        if not api_key:
            raise ValueError("API密钥不能为空")
        self.provider = provider
        self.config = APIConfig.get_config(provider)

        # 初始化原始客户端（保持向后兼容）
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base or self.config["api_base"],
        )

        # 初始化LangChain LLM
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=api_base or self.config["api_base"],
            model=self.config["model"],
            max_tokens=self.config.get("max_tokens"),
            temperature=self.config.get("temperature", 0.1),
            streaming=True  # 启用流式输出
        )

        # 初始化提示词模板
        self.prompt_template = PromptTemplate.from_template(CHAT_PROMPT_USING_CONTEXT)

        logger.info(f"初始化AI处理器: {provider}")

    async def aclose(self):
        """显式关闭异步 HTTP 客户端，避免 async_to_sync 关闭事件循环后再清理连接。"""
        clients = [
            self.client,
            getattr(self.llm, "async_client", None),
            getattr(self.llm, "root_async_client", None),
            getattr(getattr(self.llm, "async_client", None), "root_client", None),
        ]
        seen = set()
        for client in clients:
            if client is None or id(client) in seen:
                continue
            seen.add(id(client))
            close = getattr(client, "aclose", None) or getattr(client, "close", None)
            if not close:
                continue
            try:
                result = close()
                if inspect.isawaitable(result):
                    await result
            except Exception as e:
                logger.debug(f"关闭AI客户端时忽略异常: {str(e)}")

    @classmethod
    def create_default(cls, provider: str = "qwen") -> "AIHandler":
        """
        使用默认配置创建 AIHandler 实例（推荐 Agent 层使用）
        自动从环境变量读取 api_key，从 APIConfig 推导 api_base
        :param provider: 模型提供商 (qwen, openai, deepseek)，默认 qwen
        :return: AIHandler 实例
        """
        from config.config import DASHSCOPE_API_KEY
        config = APIConfig.get_config(provider)

        if not DASHSCOPE_API_KEY:
            raise ValueError("DASHSCOPE_API_KEY 环境变量未设置，请在 .env 文件中配置")

        return cls(
            api_key=DASHSCOPE_API_KEY,
            api_base=config["api_base"],
            provider=provider
        )

    async def chat_basic(self, query: str, prompt_template: str) -> str:
        """
        与 AI 交互
        :param query: 用户文本
        :param prompt_template: prompt 模板
        :return:
        """
        logger.info(f"处理文本: 长度={len(query)}")

        # 拼接 prompt
        prompt = prompt_template.format(query=query)

        result = await self.get_completion(prompt)
        if not result:
            raise Exception("API返回结果为空!")

        logger.info(f"处理完成，结果长度={len(result)}")
        return result

    async def get_completion(
            self,
            prompt: str,
            max_tokens: int = None,
            temperature: float = None,
    ) -> str:
        """
        获取 API 响应
        :param prompt:
        :param max_tokens:
        :param temperature:
        :return:
        """
        logger.info(f"调用API: provider={self.provider}")
        max_tokens = max_tokens or self.config["max_tokens"]
        temperature = self.config["temperature"] if temperature is None else temperature
        max_retries = self.config.get("max_retries", APIConfig.MAX_RETRIES)
        retry_delay = self.config.get("retry_delay", APIConfig.RETRY_DELAY)
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.config["model"],
                    messages=[
                        ChatCompletionSystemMessageParam(role="system", content="你是一个助手"),
                        ChatCompletionUserMessageParam(role="user", content=prompt)
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )

                result = response.choices[0].message.content
                logger.info(f"API调用成功: 结果长度={len(result)}")
                return result
            except Exception as e:
                last_error = e
                error_msg = str(e)
                error_type = type(e).__name__

                if "insufficient_user_quota" in error_msg:
                    raise Exception("API配额不足，请检查账户余额或联系服务提供商")
                elif "invalid_api_key" in error_msg:
                    raise Exception("API密钥无效，请检查API Key是否正确")
                elif "model_not_found" in error_msg:
                    raise Exception(f"模型 {self.config['model']} 不可用，请尝试其他模型")
                elif "Invalid max_tokens" in error_msg:
                    raise Exception(f"Token数量超出限制，当前提供商最大支持 {self.config['max_tokens']} tokens")

                if attempt < max_retries and error_type in {"APIConnectionError", "APITimeoutError", "ConnectError", "ReadTimeout"}:
                    logger.warning(
                        f"API连接失败，准备重试 {attempt}/{max_retries}: "
                        f"{error_type}: {error_msg}"
                    )
                    await asyncio.sleep(retry_delay * attempt)
                    continue

                logger.error(f"API调用错误: {error_type}: {error_msg}", exc_info=True)
                raise Exception(f"API调用失败: {error_type}: {error_msg}") from e

        raise Exception(f"API调用失败: {str(last_error)}")

    def chat_with_docs_stream(self, query: str, context_docs: List[Document]) -> Iterator[str]:
        """
        流式生成回答，带上下文（使用LangChain重构）
        :param query: 用户查询信息
        :param context_docs: 上下文文档
        :return: 流式传输片段
        """
        try:
            # 构建上下文
            context = self._build_context(context_docs)

            # 创建LangChain处理链
            chain = (
                    {
                        "query": RunnablePassthrough(),
                        "context": lambda x: context
                    }
                    | self.prompt_template
                    | self.llm
                    | StrOutputParser()
            )

            # 流式输出
            for chunk in chain.stream(query):
                yield chunk

        except Exception as e:
            logger.error(f"流式对话错误: {str(e)}")
            yield f"抱歉，生成回答时出现错误: {str(e)}"

    async def chat_with_docs_stream_async(self, query: str, context_docs: List[Document]) -> AsyncIterator[str]:
        """
        异步流式生成回答，带上下文
        :param query: 用户查询信息
        :param context_docs: 上下文文档
        :return: 异步流式传输片段
        """
        try:
            # 构建上下文
            context = self._build_context(context_docs)

            # 创建LangChain处理链
            chain = (
                    {
                        "query": RunnablePassthrough(),
                        "context": lambda x: context
                    }
                    | self.prompt_template
                    | self.llm
                    | StrOutputParser()
            )

            # 异步流式输出
            async for chunk in chain.astream(query):
                yield chunk

        except Exception as e:
            logger.error(f"异步流式对话错误: {str(e)}")
            yield f"抱歉，生成回答时出现错误: {str(e)}"

    def chat_with_docs(self, query: str, context_docs: List[Document]) -> str:
        """
        非流式生成回答，带上下文
        :param query: 用户查询信息
        :param context_docs: 上下文文档
        :return: 完整回答
        """
        try:
            # 构建上下文
            context = self._build_context(context_docs)

            # 创建LangChain处理链
            chain = (
                    {
                        "query": RunnablePassthrough(),
                        "context": lambda x: context
                    }
                    | self.prompt_template
                    | self.llm
                    | StrOutputParser()
            )

            # 同步调用
            result = chain.invoke(query)
            logger.info(f"文档对话完成: 结果长度={len(result)}")
            return result

        except Exception as e:
            logger.error(f"文档对话错误: {str(e)}")
            raise Exception(f"生成回答时出现错误: {str(e)}")

    def _build_context(self, docs: List[Document], max_length: int = 2048) -> str:
        """
        构建上下文（保持原有实现）
        :param docs: 上下文文档
        :param max_length: 最大长度
        :return: 格式化后的上下文
        """
        if not docs:
            return "没有相关的文档"

        context = []
        current_length = 0

        for i, doc in enumerate(docs, 1):
            metadata_info = f"[文档 {i}]"
            if 'course_name' in doc.metadata:
                metadata_info += f" {doc.metadata['course_name']}"
            if 'category' in doc.metadata:
                metadata_info += f" {doc.metadata['category']}"

            remaining = max_length - current_length
            if remaining <= 0:
                break

            content = doc.page_content or ""
            doc_text = f"{metadata_info}\n{content}\n"

            if len(doc_text) > remaining:
                # 控制上下文长度，避免超长 chunk 触发 LLM 上下文超限。
                min_reserved = len(metadata_info) + 16
                if remaining <= min_reserved:
                    break
                allowed_content_len = max(remaining - min_reserved, 0)
                truncated = content[:allowed_content_len].rstrip()
                doc_text = f"{metadata_info}\n{truncated}\n...(内容已截断)\n"
                context.append(doc_text)
                current_length += len(doc_text)
                break

            context.append(doc_text)
            current_length += len(doc_text)

        return "\n" + "=" * 50 + "\n".join(context)

    def get_chain(self, custom_prompt: Optional[str] = None):
        """
        获取配置好的处理链，方便自定义使用
        :param custom_prompt: 自定义提示词模板
        :return: 配置好的LangChain链
        """
        prompt_template = self.prompt_template
        if custom_prompt:
            prompt_template = PromptTemplate.from_template(custom_prompt)

        return (
                {
                    "query": RunnablePassthrough(),
                    "context": lambda x: self._build_context(x.get("context_docs", []))
                }
                | prompt_template
                | self.llm
                | StrOutputParser()
        )

