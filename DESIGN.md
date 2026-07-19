# VoiceStudio 设计文档

## 设计配色
- 主色：`#7CFC00`（Lawngreen，用于按钮、高亮、进度条等交互元素）
- 背景色：`#FDFDFC`（近白，全局背景）

## 整体架构

```
Electron (Main Process) ── spawn ──→ Python FastAPI (子进程)
    │                                      │
    │ IPC                                   │
    ▼                                       ▼
Vue3 Renderer                    backend/app/
    │                              ├── api/          # FastAPI 路由
    │                              ├── services/     # 业务逻辑层
    │                              ├── schemas/      # Pydantic 请求/响应模型
    │                              └── models/       # 领域模型（不含 PyTorch）
    │
    ▼                              backend/inference/gpt-sovits/
WaveSurfer.js                      └── GPT_SoVITS/   # 现有 TTS 推理核心
FFmpeg (导出)
```

---

## 后端模块设计

### 1. ModelManager（`backend/app/services/model_manager.py`）

**职责**：管理所有 PyTorch 模型的生命周期。从现有 `TTS` 类中剥离加载逻辑。

```python
class ModelManager:
    # 持有
    - tts_pipeline: TTS              # 核心推理实例
    - current_t2s_path: str          # 当前加载的 .ckpt 路径
    - current_vits_path: str         # 当前加载的 .pth 路径
    - is_loaded: bool
    - is_loading: bool               # 加载中标志，用于排队

    # 方法
    - load_models(t2s_path, vits_path, device, is_half) -> None
    - unload() -> None
    - get_status() -> ModelStatus
    - warm_up() -> None              # 可选，提前加载 BERT 等
```

### 2. FileService（`backend/app/services/file_service.py`）

**职责**：管理用户上传文件的存取和临时文件清理。

```python
class FileService:
    # 常量
    - MODELS_DIR: "models/"           # 持久化模型存放
    - TEMP_DIR: "temp/"               # 临时文件（参考音频、输出音频）

    # 方法
    - save_model(upload_file) -> path
    - list_models() -> list[ModelInfo]  # 扫描 models/ 下的 .pth/.ckpt
    - save_temp_audio(upload_file) -> path
    - get_output_path(filename) -> path
    - cleanup_temp() -> None
```

### 3. InferenceService（`backend/app/services/inference_service.py`）

**职责**：编排 TTS 推理流程，持有 ModelManager 引用。

```python
class InferenceService:
    - model_manager: ModelManager

    # 方法
    - synthesize(request: TTSRequest) -> Generator[TTSChunk]
      步骤：
      1. 将参考音频存为临时文件
      2. 构造 TTS.run() 所需参数
      3. 驱动 generator，流式/批量 yield 音频片段
      4. 异常时回收模型
```

### 4. TaskService（`backend/app/services/task_service.py`）

**职责**：管理合成任务的状态和取消。

```python
class TaskService:
    # 状态机: pending → running → completed | failed | cancelled
    - active_task: Task | None
    - history: list[Task]            # 最多保留 5 条已完成

    # 方法
    - create_task(request) -> Task
    - start_task(task_id) -> None
    - cancel_task(task_id) -> None
    - get_status(task_id) -> TaskStatus
    - list_history() -> list[Task]
```

### 5. AudioManager（`backend/app/services/audio_manager.py`）

**职责**：音频格式转换、导出。

```python
class AudioManager:
    - export(audio_data, sr, format="wav") -> bytes
    - convert_to_mp3(wav_path) -> path    # 用 FFmpeg
```

---

## API 路由设计（`backend/app/api/routes.py`）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/models/upload` | 上传 .pth/.ckpt，存入 models/，返回路径 |
| GET  | `/api/models/list` | 列出 models/ 下所有模型文件 |
| POST | `/api/models/load` | 加载指定的模型到 GPU |
| GET  | `/api/models/status` | 当前加载状态 |
| POST | `/api/audio/upload-ref` | 上传参考音频，存到 temp/，返回路径 |
| POST | `/api/tts/synthesize` | 发起 TTS（流式 SSE 返回音频） |
| POST | `/api/tts/cancel` | 取消当前合成任务 |
| GET  | `/api/tts/status` | 当前任务状态 |
| GET  | `/api/tts/history` | 最近 5 条历史记录 |
| GET  | `/api/audio/export/{task_id}` | 导出指定格式（wav/mp3），返回文件 |

---

## 前端布局（Vue3 + TypeScript + Vite）

### 四象限布局

```
┌────────────────────┬──────────────────────────────┐
│  左上：模型管理      │  右上：参数 + 参考音频         │
│                    │                              │
│  · 上传 .pth       │  · 参考音频（拖拽/浏览/录音）  │
│  · 上传 .ckpt      │  · prompt_text（手动输入）    │
│  · 模型列表         │  · 语速 slider               │
│  · 加载状态         │  · 断句策略 dropdown          │
│                    │  · 高级设置（折叠）            │
│                    │     top_k / top_p / temp      │
│                    │     seed                      │
├────────────────────┴──────────────────────────────┤
│  中间：TTS 主操作区                                │
│                                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │  大文本框（支持粘贴长文本）                    │  │
│  │  字数统计: 128/500                             │  │
│  └──────────────────────────────────────────────┘  │
│  [合成按钮]  [取消按钮]   状态: idle/running/done    │
├────────────────────────────────────────────────────┤
│  底部：时间轴 + 播放编辑区                          │
│                                                    │
│  ┌─ WaveSurfer.js 波形 ──────────────────────────┐ │
│  │  [播放/暂停] [拖拽选区] [删除选区] [拼接]      │ │
│  └──────────────────────────────────────────────┘  │
│  [导出 WAV] [导出 MP3]    历史：(最多5条下拉)       │
└────────────────────────────────────────────────────┘
```

### 组件树

```
App.vue
├── ModelPanel.vue           # 左上：模型上传/选择/加载
├── ParamPanel.vue           # 右上：参数 + 参考音频
├── TTSMain.vue              # 中间：文本框 + 合成控制
└── TimelinePanel.vue        # 底部：WaveSurfer + 编辑 + 导出 + 历史
```

### 状态管理（Pinia Store）

```typescript
// modelStore.ts
- availableModels: ModelInfo[]
- currentModel: { t2s: string, vits: string } | null
- loadingStatus: 'idle' | 'loading' | 'loaded' | 'error'

// ttsStore.ts
- text: string
- referenceAudioPath: string
- promptText: string
- speedFactor: number        // 默认 1.0
- splitMethod: string        // 默认 'cut5'
- topK: number               // 默认 5
- topP: number               // 默认 1.0
- temperature: number        // 默认 1.0
- taskStatus: 'idle' | 'running' | 'done' | 'error'
- currentAudioUrl: string | null

// historyStore.ts
- records: HistoryRecord[]   // 最多 5 条
```

---

## 文件存储结构

```
F:\etc\VoiceStudio\
├── backend/
│   ├── app/                     # 新增
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── model_manager.py
│   │   │   ├── file_service.py
│   │   │   ├── inference_service.py
│   │   │   ├── task_service.py
│   │   │   └── audio_manager.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── requests.py
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI 启动入口
│   └── inference/gpt-sovits/    # 现有，不动
├── models/                      # 用户上传的模型文件
│   ├── *.pth
│   └── *.ckpt
├── temp/                        # 临时文件（参考音频、输出）
├── frontend/                    # Electron + Vue3（后续）
└── venv/
```

---

## 数据流总览

```
用户上传 .pth/.ckpt
    → POST /api/models/upload
    → FileService.save_model()
    → 存入 models/

用户加载模型
    → POST /api/models/load { t2s_path, vits_path }
    → ModelManager.load_models()

用户上传参考音频 + 输入文本 + 调参数
    → POST /api/audio/upload-ref
    → FileService.save_temp_audio()
    → POST /api/tts/synthesize { text, ref_audio_path, prompt_text, ... }
    → TaskService.create_task()
    → InferenceService.synthesize()
        → TTS.run(req)  [generator]
        → SSE 流式返回音频 chunk
    → TaskService 更新状态

用户导出
    → GET /api/audio/export/{task_id}?format=mp3
    → AudioManager.export()
    → 返回文件下载
```
