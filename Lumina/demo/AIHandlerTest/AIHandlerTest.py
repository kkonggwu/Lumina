#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@FileName: AIHandlerTest.py
@Author: kkonggwu
@Date: 2025/11/11
@Version: 1.0
"""
import asyncio
from Lumina.config.config import APIConfig
from utils.ai_handler import AIHandler
from utils.prompt_template import CONCISE_SUMMARY_PROMPT
import os
DASHSCOPE_API_KEY=os.getenv("DASHSCOPE_API_KEY")

async def main():
    print("正在初始化 AI handler...")
    config = APIConfig.get_config("qwen")
    api_key = DASHSCOPE_API_KEY
    handler = AIHandler(api_key=api_key, provider="qwen", api_base=config["api_base"])
    prompt = CONCISE_SUMMARY_PROMPT
    print("成功初始化 AI handler...")
    print("正在与大模型交互")

    # 使用 await 调用异步方法
    result = await handler.chat("你好，可以介绍一下你自己吗?", prompt)

    print("返回结果为：")
    print("==================================")
    print(result)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())