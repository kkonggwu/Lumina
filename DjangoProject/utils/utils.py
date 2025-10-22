from pydantic import SecretStr

from DjangoProject.config.config import API_KEY


def get_api_key() -> SecretStr:
    """
    获取 api_key
    :return: api_key
    """
    api_key = API_KEY
    return api_key

