"""音频管理服务 —— 格式转换、导出"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import numpy as np
import soundfile as sf
import logging

logger = logging.getLogger(__name__)


class AudioManager:
    """音频导出和格式转换"""

    @staticmethod
    def save_wav(audio_data: np.ndarray, sample_rate: int, output_path: str) -> str:
        """保存为 WAV 文件"""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        sf.write(output_path, audio_data, sample_rate)
        return output_path

    @staticmethod
    def convert_to_mp3(wav_path: str, output_path: Optional[str] = None) -> str:
        """用 FFmpeg 将 wav 转 mp3"""
        if output_path is None:
            output_path = wav_path.replace(".wav", ".mp3")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", wav_path,
            "-codec:a", "libmp3lame",
            "-b:a", "192k",
            output_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        except FileNotFoundError:
            logger.error("FFmpeg not found, falling back to wav")
            # FFmpeg 不可用时降级为 wav 拷贝
            return wav_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg 转换失败: {e.stderr.decode()}")

        return output_path

    @staticmethod
    def export(
        audio_data: np.ndarray,
        sample_rate: int,
        output_format: str = "wav",
        output_dir: str = "",
    ) -> str:
        """导出音频到指定格式，返回文件路径"""
        if output_format not in ("wav", "mp3"):
            raise ValueError(f"不支持的格式: {output_format}")

        import uuid, time
        ts = time.strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        wav_path = os.path.join(output_dir, f"output_{ts}_{uid}.wav")

        AudioManager.save_wav(audio_data, sample_rate, wav_path)

        if output_format == "mp3":
            mp3_path = wav_path.replace(".wav", ".mp3")
            return AudioManager.convert_to_mp3(wav_path, mp3_path)

        return wav_path
