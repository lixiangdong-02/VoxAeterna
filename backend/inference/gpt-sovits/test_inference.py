"""
测试脚本：验证 V2 Pro 模型加载 + TTS 推理全链路
用法：在 venv 激活状态下执行
    python test_inference.py
"""
import os
import sys

# 确保导入路径正确——把 GPT_SoVITS 和它的父目录都加到 path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "GPT_SoVITS"))

# tools 目录是 git submodule，可能未拉取。创建占位模块。
import types

def _fake_i18n(text=None):
    return text if text else ""

class _FakeI18n:
    def __call__(self, text=None):
        return text if text else "Unknown"
    def __init__(self, **kw): pass
    def __getattr__(self, name):
        return _fake_i18n

tools_mod = types.ModuleType("tools")
tools_i18n_mod = types.ModuleType("tools.i18n")
tools_i18n_inner = types.ModuleType("tools.i18n.i18n")
tools_i18n_inner.I18nAuto = _FakeI18n
tools_i18n_inner.scan_language_list = lambda: []
sys.modules["tools"] = tools_mod
sys.modules["tools.i18n"] = tools_i18n_mod
sys.modules["tools.i18n.i18n"] = tools_i18n_inner
tools_mod.i18n = tools_i18n_mod
tools_i18n_mod.i18n = tools_i18n_inner

# 同样处理 tools.my_utils 和 tools.audio_sr
import torch
import librosa as _librosa
def _load_audio(path, sr=None):
    audio, file_sr = _librosa.load(path, sr=sr)
    return audio

tools_mu_mod = types.ModuleType("tools.my_utils")
tools_mu_mod.load_audio = _load_audio
sys.modules["tools.my_utils"] = tools_mu_mod
tools_mod.my_utils = tools_mu_mod

# 占位 tools.audio_sr（超分模型，不装也没事）
tools_asr_mod = types.ModuleType("tools.audio_sr")
tools_asr_mod.AP_BWE = None
sys.modules["tools.audio_sr"] = tools_asr_mod
tools_mod.audio_sr = tools_asr_mod


# ============ Step 1: 检查模型文件是否存在 ============
print("=" * 60)
print("Step 1: 检查模型文件")
print("=" * 60)

T2S_PATH = "GPT_SoVITS/pretrained_models/my-e15.ckpt"
VITS_PATH = "GPT_SoVITS/pretrained_models/my_e8_s304.pth"

for path, label in [(T2S_PATH, "GPT/T2S"), (VITS_PATH, "SoVITS/VITS")]:
    full = os.path.join(PROJECT_ROOT, path)
    if os.path.exists(full):
        size_mb = os.path.getsize(full) / (1024 * 1024)
        print(f"  [OK] {label}: {path} ({size_mb:.0f} MB)")
    else:
        print(f"  [MISS] {label}: {path}")
        sys.exit(1)

# ============ Step 2: 检查 .pth 文件版本 ============
print("\n" + "=" * 60)
print("Step 2: 识别模型版本")
print("=" * 60)

from GPT_SoVITS.process_ckpt import get_sovits_version_from_path_fast

version, model_version, if_lora = get_sovits_version_from_path_fast(
    os.path.join(PROJECT_ROOT, VITS_PATH)
)
print(f"  Version: {version}")
print(f"  Model Version: {model_version}")
print(f"  Is LoRA: {if_lora}")

# ============ Step 2.5: 下载基础模型（BERT + CNHuBERT）============
print("\n" + "=" * 60)
print("Step 2.5: 下载基础模型（BERT + CNHuBERT）")
print("=" * 60)

BERT_LOCAL = os.path.join(PROJECT_ROOT, "GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large")
CNHUBERT_LOCAL = os.path.join(PROJECT_ROOT, "GPT_SoVITS/pretrained_models/chinese-hubert-base")

for local_path, hf_id, label in [
    (BERT_LOCAL, "hfl/chinese-roberta-wwm-ext-large", "BERT"),
    (CNHUBERT_LOCAL, "TencentGameMate/chinese-hubert-base", "CNHuBERT"),
]:
    if os.path.exists(local_path) and os.listdir(local_path):
        print(f"  [OK] {label} 已存在: {local_path}")
    else:
        print(f"  下载 {label} 从 {hf_id} ...")
        os.makedirs(local_path, exist_ok=True)
        if label == "BERT":
            from transformers import AutoTokenizer, AutoModelForMaskedLM
            tok = AutoTokenizer.from_pretrained(hf_id)
            tok.save_pretrained(local_path)
            model = AutoModelForMaskedLM.from_pretrained(hf_id)
            model.save_pretrained(local_path)
        else:
            from transformers import HubertModel, Wav2Vec2FeatureExtractor
            model = HubertModel.from_pretrained(hf_id)
            model.save_pretrained(local_path)
            fe = Wav2Vec2FeatureExtractor.from_pretrained(hf_id)
            fe.save_pretrained(local_path)
        print(f"  [OK] {label} 下载完成 -> {local_path}")

# ============ Step 3: 加载 TTS_Config ============
print("\n" + "=" * 60)
print("Step 3: 加载 TTS_Config")
print("=" * 60)

from GPT_SoVITS.TTS_infer_pack.TTS import TTS_Config

# 构造针对 V2 Pro 的配置
config_dict = {
    "custom": {
        "device": "cuda",
        "is_half": True,
        "version": "v2Pro",
        "t2s_weights_path": os.path.join(PROJECT_ROOT, T2S_PATH),
        "vits_weights_path": os.path.join(PROJECT_ROOT, VITS_PATH),
        "cnhuhbert_base_path": CNHUBERT_LOCAL,
        "bert_base_path": BERT_LOCAL,
    }
}

tts_config = TTS_Config(config_dict)
print(tts_config)

# ============ Step 4: 检查 BERT / CNHuBERT 基础模型 ============
print("=" * 60)
print("Step 4: 检查基础模型")
print("=" * 60)

for path, label in [
    (tts_config.bert_base_path, "BERT"),
    (tts_config.cnhuhbert_base_path, "CNHuBERT"),
]:
    if os.path.exists(path):
        print(f"  [OK] {label}: {path}")
    else:
        print(f"  [MISS] {label}: {path}")
        print(f"    需要从 HuggingFace 下载...")

# ============ Step 5: 初始化 TTS（加载全部模型）============
print("\n" + "=" * 60)
print("Step 5: 初始化 TTS（加载模型，这一步最慢）")
print("=" * 60)

try:
    from GPT_SoVITS.TTS_infer_pack.TTS import TTS
    print("  开始加载所有模型...")
    tts_pipeline = TTS(tts_config)
    print("  [OK] TTS 模型加载成功！")
except Exception as e:
    print(f"  [FAIL] 模型加载失败:")
    print(f"  {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============ Step 6: 检查是否有测试参考音频 ============
print("\n" + "=" * 60)
print("Step 6: 准备测试推理")
print("=" * 60)

# 找个参考音频
ref_candidates = [
    os.path.join(PROJECT_ROOT, "test_ref.wav"),
]
ref_audio = None
for candidate in ref_candidates:
    if os.path.exists(candidate):
        ref_audio = candidate
        break

if ref_audio is None:
    print(f"  [SKIP] 没有找到参考音频文件")
    print(f"    请准备一个 3~10 秒的 .wav 参考音频，放到项目根目录下")
    print(f"    命名为 test_ref.wav，然后重新运行此脚本")
    print(f"    示例：一段清晰的单人说话音频，语种和你要合成的一致")
    print("\n  [OK] 模型加载测试通过！推理需要参考音频，暂时跳过。")
else:
    print(f"  [OK] 参考音频: {ref_audio}")

    # ============ Step 7: 执行一次 TTS 推理 ============
    print("\n" + "=" * 60)
    print("Step 7: 执行 TTS 推理")
    print("=" * 60)

    import librosa
    wav, sr = librosa.load(ref_audio, sr=16000)
    duration = len(wav) / sr
    print(f"  参考音频时长: {duration:.1f}s (需要 3~10s)")

    if duration < 3 or duration > 10:
        print(f"  [WARN] 参考音频时长{duration:.1f}s不在推荐范围(3~10s)，可能影响效果")
    else:
        print("  参考音频时长符合要求")

    # 用户需要自己提供 prompt_text
    # 这里用默认值，后续你可以改成真实的
    req = {
        "text": "我现在正在测试，你在干什么？吃啦吗？你是否也感觉到了呢，ok你可以出去了，现在！",
        "text_lang": "zh",
        "ref_audio_path": ref_audio,
        "prompt_text": "英国政府给自己加税，实际上，是在扣伊朗的钱。",
        "prompt_lang": "zh",
        "top_k": 5,
        "top_p": 1,
        "temperature": 1,
        "text_split_method": "cut5",
        "batch_size": 1,
        "seed": 42,
        "streaming_mode": False,
    }

    print("  开始推理...")
    try:
        gen = tts_pipeline.run(req)
        output_sr, audio = next(gen)
        print(f"  [OK] 推理成功!")
        print(f"    采样率: {output_sr} Hz")
        print(f"    音频长度: {len(audio) / output_sr:.2f}s")

        # 保存结果
        output_path = os.path.join(PROJECT_ROOT, "test_output.wav")
        import soundfile as sf
        sf.write(output_path, audio, output_sr)
        print(f"  [OK] 音频已保存到: {output_path}")
    except Exception as e:
        print(f"  [FAIL] 推理失败:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
