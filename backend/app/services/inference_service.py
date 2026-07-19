"""推理编排服务 —— 持有 ModelManager，驱动 TTS.run()"""

import os
import logging
from pathlib import Path
from typing import Generator, Tuple, AsyncGenerator, Optional
import time
import numpy as np

from app.services.model_manager import ModelManager

logger = logging.getLogger(__name__)

# 推理全链路需要 cwd 在 gpt-sovits/（g2pw、text 等模块用相对路径）
_INFERENCE_DIR = Path(__file__).resolve().parent.parent.parent / "inference" / "gpt-sovits"


class InferenceService:
    """编排 TTS 推理管线"""

    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager

    def synthesize_stream(
        self,
        text: str,
        text_lang: str,
        ref_audio_path: str,
        prompt_text: str,
        prompt_lang: str,
        speed_factor: float = 1.0,
        text_split_method: str = "cut5",
        top_k: int = 5,
        top_p: float = 1.0,
        temperature: float = 1.0,
        batch_size: int = 1,
        seed: int = -1,
    ) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        TTS 流式推理 generator。
        Yields: (sample_rate, audio_chunk) 元组
        """
        tts = self.model_manager.tts

        req = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "top_k": top_k,
            "top_p": top_p,
            "temperature": temperature,
            "text_split_method": text_split_method,
            "batch_size": batch_size,
            "seed": seed,
            "speed_factor": speed_factor,
            "streaming_mode": False,
            "return_fragment": False,
            "parallel_infer": True,
            "repetition_penalty": 1.35,
        }

        t0 = time.perf_counter()

        # 切换 cwd 到 gpt-sovits/，推理全链路都用了相对路径
        _orig_cwd = os.getcwd()
        os.chdir(str(_INFERENCE_DIR))
        try:
            for sr, audio_chunk in tts.run(req):
                if len(audio_chunk) > 0:
                    yield sr, audio_chunk
        except Exception:
            logger.exception("推理失败，重置模型...")
            # 重置受污染的模型
            t2s = self.model_manager._current_t2s
            vits = self.model_manager._current_vits
            self.model_manager.unload()
            if t2s and vits:
                self.model_manager.load_models(t2s, vits)
            raise
        finally:
            os.chdir(_orig_cwd)

        elapsed = time.perf_counter() - t0
        logger.info(f"推理完成，耗时 {elapsed:.2f}s")
