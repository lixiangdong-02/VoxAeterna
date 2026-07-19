"""文件管理服务 —— 负责模型存储、临时文件管理"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile

from app.schemas.requests import ModelInfo

# 项目根目录 → F:\etc\VoiceStudio
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class FileService:
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"

    ALLOWED_T2S_EXT = {".ckpt"}
    ALLOWED_VITS_EXT = {".pth"}

    def __init__(self):
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # ========== 模型文件 ==========

    async def save_model(self, file: UploadFile) -> ModelInfo:
        """保存上传的模型文件，返回模型信息"""
        ext = Path(file.filename).suffix.lower()
        if ext not in (self.ALLOWED_T2S_EXT | self.ALLOWED_VITS_EXT):
            raise ValueError(f"不支持的模型格式: {ext}，仅支持 .ckpt / .pth")

        model_type = "t2s" if ext in self.ALLOWED_T2S_EXT else "vits"
        dest = self.MODELS_DIR / file.filename

        # 避免覆盖，加数字后缀
        counter = 1
        while dest.exists():
            stem = Path(file.filename).stem
            dest = self.MODELS_DIR / f"{stem}_{counter}{ext}"
            counter += 1

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                f.write(chunk)

        size_mb = dest.stat().st_size / (1024 * 1024)
        return ModelInfo(
            filename=dest.name,
            type=model_type,
            size_mb=round(size_mb, 2),
            path=str(dest),
        )

    def list_models(self) -> dict:
        """列出 models/ 下所有模型文件"""
        t2s_models: List[ModelInfo] = []
        vits_models: List[ModelInfo] = []

        if self.MODELS_DIR.exists():
            for fpath in sorted(self.MODELS_DIR.iterdir()):
                if not fpath.is_file():
                    continue
                ext = fpath.suffix.lower()
                size_mb = fpath.stat().st_size / (1024 * 1024)
                info = ModelInfo(
                    filename=fpath.name,
                    type="t2s" if ext == ".ckpt" else "vits",
                    size_mb=round(size_mb, 2),
                    path=str(fpath),
                )
                if ext == ".ckpt":
                    t2s_models.append(info)
                elif ext == ".pth":
                    vits_models.append(info)

        return {"t2s_models": t2s_models, "vits_models": vits_models}

    def get_model_path(self, filename: str) -> Optional[Path]:
        """根据文件名获取模型完整路径"""
        p = self.MODELS_DIR / filename
        return p if p.exists() else None

    # ========== 临时文件（参考音频 / 输出音频）==========

    async def save_temp_audio(self, file: UploadFile) -> str:
        """保存上传的参考音频到 temp/，返回文件名"""
        ext = Path(file.filename).suffix.lower() or ".wav"
        import uuid
        saved_name = f"ref_{uuid.uuid4().hex[:8]}{ext}"
        dest = self.TEMP_DIR / saved_name

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return saved_name

    def get_temp_path(self, filename: str) -> Path:
        return self.TEMP_DIR / filename

    def new_output_filename(self, ext: str = ".wav") -> str:
        import uuid, time
        ts = time.strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        return f"output_{ts}_{uid}{ext}"

    def cleanup_temp(self, max_age_minutes: int = 60):
        """清理超过 max_age_minutes 的临时文件"""
        import time
        if not self.TEMP_DIR.exists():
            return
        cutoff = time.time() - max_age_minutes * 60
        for fpath in self.TEMP_DIR.iterdir():
            if fpath.is_file() and fpath.stat().st_mtime < cutoff:
                fpath.unlink(missing_ok=True)
