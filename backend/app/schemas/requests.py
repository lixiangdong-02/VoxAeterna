"""Pydantic 请求/响应模型"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# ============ 模型管理 ============

class ModelLoadRequest(BaseModel):
    t2s_path: str = Field(..., description=".ckpt 文件路径（相对于 models/）")
    vits_path: str = Field(..., description=".pth 文件路径（相对于 models/）")

class ModelInfo(BaseModel):
    filename: str
    type: str  # "t2s" | "vits"
    size_mb: float
    path: str

class ModelStatus(BaseModel):
    is_loaded: bool
    is_loading: bool
    current_t2s: Optional[str] = None
    current_vits: Optional[str] = None
    device: str = "cpu"
    is_half: bool = False

class ModelListResponse(BaseModel):
    t2s_models: list[ModelInfo]
    vits_models: list[ModelInfo]
    status: ModelStatus


# ============ TTS 合成 ============

class SplitMethod(str, Enum):
    CUT0 = "cut0"   # 最保守，句号/问号/感叹号
    CUT1 = "cut1"
    CUT2 = "cut2"
    CUT3 = "cut3"
    CUT4 = "cut4"
    CUT5 = "cut5"   # 最激进
    AUTO = "auto"

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="要合成的文字")
    text_lang: str = Field(default="zh", description="文字语言")
    ref_audio_path: str = Field(..., description="参考音频路径（temp/ 下的文件名）")
    prompt_text: str = Field(..., description="参考音频对应的文字")
    prompt_lang: str = Field(default="zh", description="参考音频语言")
    speed_factor: float = Field(default=1.0, ge=0.5, le=2.0, description="语速")
    text_split_method: SplitMethod = Field(default=SplitMethod.CUT5, description="断句策略")
    top_k: int = Field(default=5, ge=1, le=20)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    temperature: float = Field(default=1.0, ge=0.1, le=2.0)
    batch_size: int = Field(default=1, ge=1, le=10)
    seed: int = Field(default=-1)
    streaming: bool = Field(default=True, description="是否流式返回")


# ============ 任务状态 ============

class TaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskStatus(BaseModel):
    task_id: str
    state: TaskState
    progress: Optional[float] = None     # 0.0 ~ 1.0
    text: Optional[str] = None
    audio_path: Optional[str] = None     # 完成后可访问的音频路径
    duration_seconds: Optional[float] = None
    sample_rate: Optional[int] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


# ============ 导出 ============

class ExportFormat(str, Enum):
    WAV = "wav"
    MP3 = "mp3"

class ExportRequest(BaseModel):
    task_id: str
    format: ExportFormat = ExportFormat.WAV


# ============ 通用 ============

class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
