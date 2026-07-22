"""模型管理服务 —— 封装 GPT-SoVITS 模型加载/卸载/状态"""

import sys
import types
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# 确保 GPT_SoVITS 可导入
_INFERENCE_DIR = Path(__file__).resolve().parent.parent.parent / "inference" / "gpt-sovits"
_SOVITS_DIR = _INFERENCE_DIR / "GPT_SoVITS"
if str(_INFERENCE_DIR) not in sys.path:
    sys.path.insert(0, str(_INFERENCE_DIR))
if str(_SOVITS_DIR) not in sys.path:
    sys.path.insert(0, str(_SOVITS_DIR))
# eres2net 子模块（SV 模型需要）
_ERES2NET_DIR = _SOVITS_DIR / "eres2net"
if str(_ERES2NET_DIR) not in sys.path:
    sys.path.insert(0, str(_ERES2NET_DIR))

# --- 占位 tools 模块（若 git submodule 未拉取）---
if "tools" not in sys.modules:
    _tm = types.ModuleType("tools")
    _tm_i18n = types.ModuleType("tools.i18n")
    _tm_i18n_i18n = types.ModuleType("tools.i18n.i18n")

    class _FakeI18n:
        def __init__(self, **kw): pass
        def __call__(self, text=None):
            return text if text else ""

    _tm_i18n_i18n.I18nAuto = _FakeI18n
    _tm_i18n_i18n.scan_language_list = lambda: []

    _tm_mu = types.ModuleType("tools.my_utils")
    import librosa as _librosa
    _tm_mu.load_audio = lambda path, sr=None: _librosa.load(path, sr=sr)[0]

    _tm_asr = types.ModuleType("tools.audio_sr")
    _tm_asr.AP_BWE = None

    sys.modules["tools"] = _tm
    sys.modules["tools.i18n"] = _tm_i18n
    sys.modules["tools.i18n.i18n"] = _tm_i18n_i18n
    sys.modules["tools.my_utils"] = _tm_mu
    sys.modules["tools.audio_sr"] = _tm_asr
    _tm.i18n = _tm_i18n
    _tm.my_utils = _tm_mu
    _tm.audio_sr = _tm_asr
    _tm_i18n.i18n = _tm_i18n_i18n


from app.schemas.requests import ModelStatus
from app.config import InferenceSettings

_settings = InferenceSettings()


class ModelManager:
    """管理 TTS 模型生命周期"""

    def __init__(self):
        self._tts = None          # TTS 实例
        self._config_obj = None   # TTS_Config 实例
        self._current_t2s: Optional[str] = None
        self._current_vits: Optional[str] = None
        self._is_loading: bool = False
        self._device: str = _settings.device
        self._is_half: bool = _settings.is_half

    @property
    def is_loaded(self) -> bool:
        return self._tts is not None

    def get_status(self) -> ModelStatus:
        return ModelStatus(
            is_loaded=self.is_loaded,
            is_loading=self._is_loading,
            current_t2s=self._current_t2s,
            current_vits=self._current_vits,
            device=self._device,
            is_half=self._is_half,
        )

    def load_models(
        self,
        t2s_path: str,
        vits_path: str,
        device: Optional[str] = None,
        is_half: Optional[bool] = None,
    ) -> None:
        """加载 TTS 模型到 GPU。若已加载其他模型则先卸载。"""
        if device is None:
            device = _settings.device
        if is_half is None:
            is_half = _settings.is_half
        if self._is_loading:
            raise RuntimeError("模型正在加载中，请等待")
        self._is_loading = True

        try:
            # 如果已加载了不同的模型，先卸载
            if self._tts is not None:
                if (self._current_t2s == t2s_path and self._current_vits == vits_path
                        and self._device == device and self._is_half == is_half):
                    logger.info("模型已加载，跳过")
                    return
                logger.info("检测到模型或设备变更，卸载旧模型...")
                self.unload()

            self._device = device
            self._is_half = is_half

            from GPT_SoVITS.TTS_infer_pack.TTS import TTS, TTS_Config

            # sv.py 内部用相对路径，需要把 cwd 切到 gpt-sovits 目录
            import os as _os
            _orig_cwd = _os.getcwd()
            _os.chdir(str(_INFERENCE_DIR))

            try:
                # 推断版本（V2 Pro）
                from GPT_SoVITS.process_ckpt import get_sovits_version_from_path_fast
                _, model_version, _ = get_sovits_version_from_path_fast(vits_path)

                # 基础模型路径
                pretrained = _INFERENCE_DIR / "GPT_SoVITS" / "pretrained_models"
                bert_path = str(pretrained / "chinese-roberta-wwm-ext-large")
                cnhubert_path = str(pretrained / "chinese-hubert-base")

                cfg_dict = {
                    "custom": {
                        "device": device,
                        "is_half": is_half,
                        "version": model_version,
                        "t2s_weights_path": t2s_path,
                        "vits_weights_path": vits_path,
                        "cnhuhbert_base_path": cnhubert_path,
                        "bert_base_path": bert_path,
                    }
                }

                logger.info(f"加载配置: {cfg_dict}")
                config = TTS_Config(cfg_dict)
                tts = TTS(config)

                self._tts = tts
                self._config_obj = config
                self._current_t2s = t2s_path
                self._current_vits = vits_path
                logger.info("模型加载完成")
            finally:
                _os.chdir(_orig_cwd)

        finally:
            self._is_loading = False

    def unload(self) -> None:
        """卸载模型，释放显存"""
        if self._tts is not None:
            logger.info("卸载模型...")
            try:
                self._tts.empty_cache()
            except Exception:
                pass
            del self._tts
            self._tts = None
            self._config_obj = None

            import gc
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            logger.info("模型已卸载")

        self._current_t2s = None
        self._current_vits = None

    @property
    def tts(self):
        """获取 TTS 实例（仅用于 InferenceService）"""
        if self._tts is None:
            raise RuntimeError("模型未加载，请先调用 load_models()")
        return self._tts
