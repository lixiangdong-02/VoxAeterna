"""VoxAeterna 云端服务 —— 启动入口"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cloud.api.routes import router
from cloud.config import CloudSettings

settings = CloudSettings()

app = FastAPI(
    title="VoxAeterna Cloud",
    description="用户管理 · 订阅 · 试用次数 · 管理后台",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "cloud.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level="info",
    )
