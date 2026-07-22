
"""VoxAeterna 云端服务统一配置"""
from pathlib import Path
from pydantic_settings import BaseSettings


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class CloudSettings(BaseSettings):
    """云端服务配置"""

    # 服务绑定
    host: str = "0.0.0.0"
    port: int = 8000

    # JWT
    secret_key: str = "voxaeterna-secret-change-in-production-use-env-var"

    # 数据库
    db_user: str = "root"
    db_pass: str = ""
    db_host: str = "127.0.0.1"
    db_port: str = "3306"
    db_name: str = "voxaeterna"

    # SMTP 邮件
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = ""

    # 支付宝当面付
    alipay_app_id: str = ""
    alipay_private_key: str = ""   # 应用私钥（PKCS1 或 PKCS8）
    alipay_public_key: str = ""    # 支付宝公钥
    alipay_notify_url: str = ""    # 异步通知地址

    model_config = {
        "env_prefix": "VOX_",
        "env_file": str(_PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
