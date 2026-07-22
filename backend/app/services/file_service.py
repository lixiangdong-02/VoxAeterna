"""文件管理服务 —— 负责模型存储、临时文件管理、音色配对"""

import os
import json
import uuid
import shutil
import time
from pathlib import Path
from threading import Lock
from typing import List, Optional
from fastapi import UploadFile

from app.schemas.requests import ModelInfo

# 项目根目录 → F:\etc\VoiceStudio
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class FileService:
    MODELS_DIR: Path = PROJECT_ROOT / "models"
    TEMP_DIR: Path = PROJECT_ROOT / "temp"
    PROFILE_IMAGES_DIR: Path = PROJECT_ROOT / "models" / "profile_images"

    ALLOWED_T2S_EXT = {".ckpt"}
    ALLOWED_VITS_EXT = {".pth"}
    ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

    def __init__(self):
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.PROFILE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

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


    # ========== 音色头像 ==========

    async def save_profile_image(self, file: UploadFile) -> str:
        """保存音色头像，返回文件名"""
        ext = Path(file.filename).suffix.lower()
        if ext not in self.ALLOWED_IMAGE_EXT:
            raise ValueError(f"不支持的图片格式: {ext}，仅支持 {self.ALLOWED_IMAGE_EXT}")

        saved_name = f"avatar_{uuid.uuid4().hex[:8]}{ext}"
        dest = self.PROFILE_IMAGES_DIR / saved_name

        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        return saved_name

    def get_profile_image_path(self, filename: str) -> Optional[Path]:
        p = self.PROFILE_IMAGES_DIR / filename
        return p if p.exists() else None

# ========== 音色配对（Voice Profile）==========

class VoiceProfileService:
    """管理 models/profiles.json —— pth/ckpt 文件配对为「音色」"""

    _PROFILES_PATH: Path = FileService.MODELS_DIR / "profiles.json"
    _lock = Lock()

    def _read(self) -> dict:
        if self._PROFILES_PATH.exists():
            try:
                return json.loads(self._PROFILES_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"profiles": []}

    def _write(self, data: dict):
        with self._lock:
            self._PROFILES_PATH.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def list(self) -> list[dict]:
        return self._read().get("profiles", [])

    def get(self, profile_id: str) -> Optional[dict]:
        for p in self.list():
            if p["id"] == profile_id:
                return p
        return None

    def create(self, name: str, description: str, t2s_path: str, vits_path: str,
               image: Optional[str] = None) -> dict:
        data = self._read()
        profile = {
            "id": uuid.uuid4().hex[:8],
            "name": name.strip(),
            "description": description.strip(),
            "t2s_file": t2s_path,
            "vits_file": vits_path,
            "image": image,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data["profiles"].append(profile)
        self._write(data)
        return profile

    def update(self, profile_id: str, name: Optional[str] = None,
               description: Optional[str] = None,
               image: Optional[str] = None) -> bool:
        data = self._read()
        for p in data["profiles"]:
            if p["id"] == profile_id:
                if name is not None:
                    p["name"] = name.strip()
                if description is not None:
                    p["description"] = description.strip()
                if image is not None:
                    p["image"] = image
                self._write(data)
                return True
        return False

    def delete(self, profile_id: str) -> bool:
        """删除配对（不删模型文件）"""
        data = self._read()
        for i, p in enumerate(data["profiles"]):
            if p["id"] == profile_id:
                data["profiles"].pop(i)
                self._write(data)
                return True
        return False


# 单例
profile_service = VoiceProfileService()
