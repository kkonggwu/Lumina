import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

from sentence_transformers import SentenceTransformer

# 现在可以正常下载了
model = SentenceTransformer('all-MiniLM-L6-v2')