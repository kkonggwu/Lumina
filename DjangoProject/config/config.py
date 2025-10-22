import os
from dotenv import load_dotenv

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
MYSQL_PASSWD = os.getenv("MYSQL_PASSWD")
CACHE_PATH = "../static/DBCache"
