import os
from dotenv import load_dotenv

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
MYSQL_PASSWD = os.getenv("MYSQL_PASSWD")
CACHE_PATH = "../static/DBCache"


class APIConfig:
    """API配置"""
    # 并发设置
    MAX_CONCURRENT = 5  # 最大并发数
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 0.5  # 秒  重试间隔时间

    # OpenAI配置
    OPENAI_MODEL = "gpt-4o-mini"
    OPENAI_TEMPERATURE = 0.7
    OPENAI_MAX_TOKENS = 4096

    # DeepSeek配置
    DEEPSEEK_MODEL = "deepseek-chat"
    DEEPSEEK_TEMPERATURE = 1.0
    DEEPSEEK_MAX_TOKENS = 4096

    # Qwen配置
    QWEN_MODEL = "qwen-plus"  # 可选: qwen-turbo, qwen-plus, qwen-max
    QWEN_TEMPERATURE = 0.8
    QWEN_MAX_TOKENS = 2048

    @staticmethod
    def get_config(provider: str) -> dict:
        """获取API配置"""
        if provider == "openai":
            return {
                "model": APIConfig.OPENAI_MODEL,
                "temperature": APIConfig.OPENAI_TEMPERATURE,
                "max_tokens": APIConfig.OPENAI_MAX_TOKENS,
                "api_base": "https://api.openai.com/v1"
            }
        elif provider == "deepseek":
            return {
                "model": APIConfig.DEEPSEEK_MODEL,
                "temperature": APIConfig.DEEPSEEK_TEMPERATURE,
                "max_tokens": APIConfig.DEEPSEEK_MAX_TOKENS,
                "api_base": "https://api.deepseek.com/v1"
            }
        elif provider == "qwen":
            return {
                "model": APIConfig.QWEN_MODEL,
                "temperature": APIConfig.QWEN_TEMPERATURE,
                "max_tokens": APIConfig.QWEN_MAX_TOKENS,
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"
            }
        else:
            raise ValueError(f"不支持的API提供商: {provider}")