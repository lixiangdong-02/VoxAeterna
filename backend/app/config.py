
"""VoiceStudio 统一配置 —— 所有配置项从 .env 文件 / 环境变量读取"""
from pathlib import Path
from pydantic_settings import BaseSettings


# 自动找到项目根目录（包含 .env 文件的那一层）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class InferenceSettings(BaseSettings):
    """本地推理后端配置"""

    # 服务绑定
    host: str = "127.0.0.1"
    port: int = 9880

    # 推理设备
    device: str = "cuda"
    is_half: bool = True

    model_config = {
        "env_prefix": "VOX_INFERENCE_",
        "env_file": str(_PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "case_sensitive": False,
    }
