"""FastAPI 路由 —— 模型管理 / 参考音频上传 / TTS / 导出"""

import io
import logging
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from pydantic import ValidationError

from app.schemas.requests import (
    ModelLoadRequest,
    ModelListResponse,
    MessageResponse,
    TTSRequest,
    TaskStatus,
    ExportFormat,
    VoiceProfileOut,
    CreateProfileRequest,
    UpdateProfileRequest,
)
from app.services.file_service import FileService, profile_service
from app.services.model_manager import ModelManager
from app.services.inference_service import InferenceService
from app.services.task_service import TaskService, Task
from app.services.audio_manager import AudioManager
from app.services.history_store import list_by_user as history_list_by_user
from app.services.history_store import delete_task as history_delete_task
from app.services.history_store import get_task as history_get_task

logger = logging.getLogger(__name__)

# ========== 单例服务 ==========
file_service = FileService()
model_manager = ModelManager()
inference_service = InferenceService(model_manager)
task_service = TaskService()

router = APIRouter(prefix="/api")


# ======================= 音色配对 =======================

@router.get("/profiles")
async def list_profiles():
    """列出所有音色配对"""
    return JSONResponse(content=profile_service.list())


@router.post("/profiles/image")
async def upload_profile_image(file: UploadFile = File(...)):
    """上传音色头像，返回文件名"""
    try:
        saved_name = await file_service.save_profile_image(file)
        return JSONResponse(content={"filename": saved_name})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profiles/image/{filename}")
async def get_profile_image(filename: str):
    """获取音色头像"""
    img_path = file_service.get_profile_image_path(filename)
    if not img_path:
        raise HTTPException(status_code=404, detail="头像不存在")
    import mimetypes
    mime, _ = mimetypes.guess_type(str(img_path))
    return FileResponse(path=str(img_path), media_type=mime or "image/png")


@router.post("/profiles")
async def create_profile(req: CreateProfileRequest):
    """创建音色配对（.ckpt + .pth 文件必须已上传到 models/）"""
    t2s_full = file_service.get_model_path(req.t2s_path)
    vits_full = file_service.get_model_path(req.vits_path)
    if not t2s_full:
        raise HTTPException(status_code=404, detail=f"模型文件不存在: {req.t2s_path}")
    if not vits_full:
        raise HTTPException(status_code=404, detail=f"模型文件不存在: {req.vits_path}")
    profile = profile_service.create(req.name, req.description, req.t2s_path, req.vits_path, req.image)
    return JSONResponse(content=profile, status_code=201)


@router.put("/profiles/{profile_id}")
async def update_profile(profile_id: str, req: UpdateProfileRequest):
    """修改音色名称/简介/头像"""
    ok = profile_service.update(profile_id, req.name, req.description, req.image)
    if not ok:
        raise HTTPException(status_code=404, detail="音色不存在")
    return MessageResponse(message="已更新")


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """删除音色配对（不删文件）"""
    ok = profile_service.delete(profile_id)
    if not ok:
        raise HTTPException(status_code=404, detail="音色不存在")
    return MessageResponse(message="已删除")


# ======================= 模型管理 =======================

@router.get("/models/list", response_model=ModelListResponse)
async def list_models():
    """列出所有模型 + 当前加载状态"""
    models = file_service.list_models()
    status = model_manager.get_status()
    return ModelListResponse(**models, status=status)


@router.post("/models/upload")
async def upload_model(file: UploadFile = File(...)):
    """上传模型文件（.pth / .ckpt）"""
    try:
        info = await file_service.save_model(file)
        return JSONResponse(content=info.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/models/load")
async def load_model(req: ModelLoadRequest):
    """加载指定模型"""
    t2s_full = file_service.get_model_path(req.t2s_path)
    vits_full = file_service.get_model_path(req.vits_path)

    if not t2s_full or not vits_full:
        missing = []
        if not t2s_full:
            missing.append(req.t2s_path)
        if not vits_full:
            missing.append(req.vits_path)
        raise HTTPException(status_code=404, detail=f"模型不存在: {missing}")

    try:
        model_manager.load_models(str(t2s_full), str(vits_full))
        return JSONResponse(content={"message": "模型加载成功"})
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("模型加载失败")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models/status")
async def model_status():
    """当前模型加载状态"""
    return JSONResponse(content=model_manager.get_status().model_dump())


# ======================= 参考音频 =======================

@router.post("/audio/upload-ref")
async def upload_reference_audio(file: UploadFile = File(...)):
    """上传参考音频，返回临时文件名"""
    try:
        saved_name = await file_service.save_temp_audio(file)
        return JSONResponse(content={"filename": saved_name})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ======================= TTS =======================

@router.post("/tts/synthesize")
async def synthesize(req: TTSRequest):
    """发起 TTS 合成任务"""
    if not model_manager.is_loaded:
        raise HTTPException(status_code=400, detail="模型未加载，请先加载模型")

    # 验证参考音频存在
    ref_path = file_service.get_temp_path(req.ref_audio_path)
    if not ref_path.exists():
        raise HTTPException(status_code=404, detail=f"参考音频不存在: {req.ref_audio_path}")

    # 创建任务
    task = task_service.create_task(
        req.text,
        user_id=req.user_id,
        prompt_text=req.prompt_text,
        speed_factor=req.speed_factor,
        ref_audio_path=req.ref_audio_path,
    )

    if not req.streaming:
        # 非流式：同步执行，一次性返回
        try:
            task_service.start_task(task)
            chunks = list(inference_service.synthesize_stream(
                text=req.text,
                text_lang=req.text_lang,
                ref_audio_path=str(ref_path),
                prompt_text=req.prompt_text,
                prompt_lang=req.prompt_lang,
                speed_factor=req.speed_factor,
                text_split_method=req.text_split_method.value,
                top_k=req.top_k,
                top_p=req.top_p,
                temperature=req.temperature,
                batch_size=req.batch_size,
                seed=req.seed,
                cancel_event=task._cancel_event,
            ))

            if not chunks:
                raise HTTPException(status_code=500, detail="推理返回空结果")

            # TTS.run() 在 return_fragment=False 时 yield 一次完整合成音频
            final_sr, full_audio = chunks[0]

            # 保存
            output_name = file_service.new_output_filename(".wav")
            output_path = file_service.get_temp_path(output_name)
            AudioManager.save_wav(full_audio, final_sr, str(output_path))

            duration = len(full_audio) / final_sr
            task_service.complete_task(task, output_name, duration, final_sr, req.user_id)

            # 返回音频文件，附上时长头
            return FileResponse(
                path=str(output_path),
                media_type="audio/wav",
                filename=output_name,
                headers={
                    "X-Task-Id": task.task_id,
                    "X-Audio-Duration": f"{duration:.2f}",
                    "X-Audio-Sample-Rate": str(final_sr),
                },
            )

        except Exception as e:
            task_service.fail_task(task, str(e), req.user_id)
            raise HTTPException(status_code=500, detail=str(e))

    else:
        # 流式：SSE 返回
        task_service.start_task(task)

        async def sse_generator():
            try:
                import wave
                from io import BytesIO
                first_chunk = True
                total_samples = 0
                final_sr = 0

                for sr, chunk in inference_service.synthesize_stream(
                    text=req.text,
                    text_lang=req.text_lang,
                    ref_audio_path=str(ref_path),
                    prompt_text=req.prompt_text,
                    prompt_lang=req.prompt_lang,
                    speed_factor=req.speed_factor,
                    text_split_method=req.text_split_method.value,
                    top_k=req.top_k,
                    top_p=req.top_p,
                    temperature=req.temperature,
                    batch_size=req.batch_size,
                    seed=req.seed,
                    cancel_event=task._cancel_event,
                ):
                    final_sr = sr
                    total_samples += len(chunk)

                    if first_chunk:
                        first_chunk = False

                    yield chunk.tobytes()

                # 保存完整音频
                # 这里简化处理：流式模式下只返回音频流，不保存
                task_service.complete_task(task, "", total_samples / final_sr, final_sr)

            except Exception as e:
                task_service.fail_task(task, str(e), req.user_id)
                yield b""

        return StreamingResponse(
            sse_generator(),
            media_type="audio/wav",
            headers={"X-Task-Id": task.task_id},
        )


@router.post("/tts/cancel")
async def cancel_tts(task_id: str = Query(...), user_id: int = Query(default=0)):
    """取消当前合成任务"""
    status = task_service.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    task_service.cancel_task_by_id(task_id, user_id)
    return MessageResponse(message="已取消")


@router.get("/tts/status")
async def tts_status(task_id: str = Query(...)):
    """查询任务状态"""
    status = task_service.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return JSONResponse(content=status.model_dump())


@router.get("/tts/history")
async def tts_history(user_id: int = Query(default=0)):
    """查询用户合成历史（从 SQLite）"""
    if user_id > 0:
        records = history_list_by_user(user_id, limit=50)
        return JSONResponse(content=records)
    # 兼容：无 user_id 时返回内存中的历史
    return JSONResponse(content=[h.model_dump() for h in task_service.list_history()])


# ======================= 健康检查 =======================

@router.get("/health")
async def health():
    """后端健康检查"""
    return {"status": "ok", "service": "VoiceStudio Inference", "model_loaded": model_manager.is_loaded}

@router.delete("/tts/history/{task_id}")
async def delete_tts_history(task_id: str, user_id: int = Query(default=0)):
    """删除一条合成历史"""
    if user_id <= 0:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    ok = history_delete_task(task_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权删除")
    return MessageResponse(message="已删除")


@router.get("/audio/export/{task_id}")
async def export_audio(task_id: str, format: ExportFormat = Query(default=ExportFormat.WAV)):
    """导出指定格式音频文件"""
    status = task_service.get_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if status.state != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，无法导出")

    audio_path = status.audio_path
    if audio_path and file_service.get_temp_path(audio_path).exists():
        file_path = file_service.get_temp_path(audio_path)
    else:
        raise HTTPException(status_code=404, detail="音频文件不存在，可能已被清理")

    if format.value == "mp3":
        try:
            mp3_path = AudioManager.convert_to_mp3(str(file_path))
            return FileResponse(path=mp3_path, media_type="audio/mpeg", filename=f"{task_id}.mp3")
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(path=str(file_path), media_type="audio/wav", filename=f"{task_id}.wav")
