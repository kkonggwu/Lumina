from langchain_openai import ChatOpenAI
from langchain_community.cache import SQLiteCache
import langchain
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from Lumina.config.config import CACHE_PATH

# 启用全局缓存
langchain.llm_cache = SQLiteCache(database_path=CACHE_PATH + "/langchain.db")


class DashscopeClient:
    def __init__(self, api_key: SecretStr):
        self.chatLLM = ChatOpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
            cache=True,  # 关键：显式开启缓存
        )

    def chat(self, human_message: HumanMessage):
        """
        基础版，与大模型进行交互
        :param human_message: 用户输入的内容
        :return: 大模型返回的内容，json格式
        """
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            human_message,
        ]
        response = self.chatLLM.invoke(messages)
        return response.model_dump_json()

