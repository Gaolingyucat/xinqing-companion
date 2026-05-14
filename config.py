"""配置文件：集中管理项目运行参数与环境变量读取。"""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool_env(name, default=False):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    DEBUG = True
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    REPORT_FOLDER = BASE_DIR / "reports"
    DATA_FILE = BASE_DIR / "data" / "records.csv"
    MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")
    MIMO_BASE_URL = os.getenv("MIMO_BASE_URL", "")
    MIMO_MODEL = os.getenv("MIMO_MODEL", "")
    ENABLE_LLM_ADVISOR = _bool_env("ENABLE_LLM_ADVISOR", False)
    MIMO_TIMEOUT_SECONDS = int(os.getenv("MIMO_TIMEOUT_SECONDS", "15"))
    # DeepFace 独立服务配置：主应用优先走远程识别，避免部署时被重依赖阻塞。
    DEEPFACE_API_URL = os.getenv("DEEPFACE_API_URL", "")
    LOCAL_DEEPFACE_ENABLED = _bool_env("LOCAL_DEEPFACE_ENABLED", False)
    DEEPFACE_TIMEOUT_SECONDS = int(os.getenv("DEEPFACE_TIMEOUT_SECONDS", "30"))
