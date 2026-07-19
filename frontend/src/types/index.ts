/** 前端类型定义 —— 与后端 schemas 对应 */

export interface ModelInfo {
  filename: string
  type: 't2s' | 'vits'
  size_mb: number
  path: string
}

export interface ModelStatus {
  is_loaded: boolean
  is_loading: boolean
  current_t2s: string | null
  current_vits: string | null
  device: string
  is_half: boolean
}

export interface ModelListResponse {
  t2s_models: ModelInfo[]
  vits_models: ModelInfo[]
  status: ModelStatus
}

export type SplitMethod = 'cut0' | 'cut1' | 'cut2' | 'cut3' | 'cut4' | 'cut5' | 'auto'

export interface TTSRequest {
  text: string
  text_lang: string
  ref_audio_path: string
  prompt_text: string
  prompt_lang: string
  speed_factor: number
  text_split_method: SplitMethod
  top_k: number
  top_p: number
  temperature: number
  batch_size: number
  seed: number
  streaming: boolean
}

export type TaskState = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface TaskStatus {
  task_id: string
  state: TaskState
  progress: number | null
  text: string | null
  audio_path: string | null
  duration_seconds: number | null
  sample_rate: number | null
  error_message: string | null
  created_at: string | null
}

export type ExportFormat = 'wav' | 'mp3'

export interface HistoryRecord extends TaskStatus {
  // 和 TaskStatus 同结构
}

/** 字体方案 */
export interface FontConfig {
  display: string   // 页面大标题
  body: string      // 正文
  mono: string      // 代码/数据
}
