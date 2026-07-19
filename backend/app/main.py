"""VoiceStudio Backend —— FastAPI 启动入口"""

import sys
from pathlib import Path

# 确保 backend/ 可导入
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn as _uvicorn

from app.api.routes import router

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("voicestudio")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭时的生命周期管理"""
    logger.info("VoiceStudio Backend 启动")
    yield
    logger.info("VoiceStudio Backend 停止")
    # 清理
    from app.services.file_service import FileService
    FileService().cleanup_temp()


app = FastAPI(
    title="VoiceStudio",
    description="GPT-SoVITS TTS 推理服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS —— Electron 前端默认 localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn as _uvicorn
    _uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=9880,
        reload=False,
        log_level="info",
        timeout_keep_alive=120,
        limit_max_requests=None,
    )
