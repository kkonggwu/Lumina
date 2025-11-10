#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: ai_handler.py
@Author: kkonggwu
@Date: 2025/11/10
@Version: 1.0
"""
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from Lumina.config.config import APIConfig


class AIHandler:
    def __init__(self, api_key: str, api_base: str, provider: str = "qwen"):
        """
        初始化API处理器
        :param api_key:
        :param api_base:
        :param provider:
        """
        if not api_key:
            raise ValueError("API密钥不能为空")
        self.provider = provider
        self.config = APIConfig.get_config(provider)
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=api_base,
        )

        print(f"初始化AI处理器: {provider}")

    async def chat(self, text: str, prompt_template: str) -> str:
        """
        与 AI 交互
        :param text: 用户文本
        :param prompt_template: prompt 模板
        :return:
        """
        print(f"处理文本: 长度={len(text)}")

        # 拼接 prompt
        prompt = prompt_template.format(text=text)

        result = await self.get_completion(prompt)
        if not result:
            raise Exception("API返回结果为空!")

        print(f"处理完成，结果长度={len(result)}")
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
        try:
            print(f"调用API: provider={self.provider}")
            max_tokens = max_tokens or self.config["max_tokens"]
            temperature = temperature or self.config["temperature"]

            response = await self.client.chat.completions.create(
                model=self.config["model"],
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content="你是一个助手"),
                    ChatCompletionUserMessageParam(role="user", content=prompt)
                ],
                max_tokens=max_tokens,
                temperature=temperature or self.config["temperature"]
            )

            result = response.choices[0].message.content
            print(f"API调用成功: 结果长度={len(result)}")  # 添加日志
            return result
        except Exception as e:
            error_msg = str(e)
            print(f"API调用错误: {error_msg}")  # 添加日志

            if "insufficient_user_quota" in error_msg:
                raise Exception("API配额不足，请检查账户余额或联系服务提供商")
            elif "invalid_api_key" in error_msg:
                raise Exception("API密钥无效，请检查API Key是否正确")
            elif "model_not_found" in error_msg:
                raise Exception(f"模型 {self.config['model']} 不可用，请尝试其他模型")
            elif "Invalid max_tokens" in error_msg:
                raise Exception(f"Token数量超出限制，当前提供商最大支持 {self.config['max_tokens']} tokens")
            else:
                raise Exception(f"API调用失败: {error_msg}")

