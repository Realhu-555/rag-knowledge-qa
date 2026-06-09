"""配置管理"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 知识库目录
DATA_DIR = BASE_DIR / "data"
CHROMA_DB_DIR = BASE_DIR / "chroma_db"
IMAGES_DIR = BASE_DIR / "images"

# DeepSeek API配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# Embedding配置
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local")  # local 或 api
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# 切片配置
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# 检索配置
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
RRF_K = int(os.getenv("RRF_K", "60"))  # RRF参数

# LLM配置
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))

# API服务配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8080"))

# 多轮对话配置
MAX_HISTORY_ROUNDS = int(os.getenv("MAX_HISTORY_ROUNDS", "5"))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# 安全配置
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "5"))
ALLOWED_FILE_TYPES = os.getenv("ALLOWED_FILE_TYPES", ".md,.txt,.docx,.pdf,.xlsx,.png,.jpg").split(",")

# 限流配置
RATE_LIMIT_DAILY = int(os.getenv("RATE_LIMIT_DAILY", "100"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
