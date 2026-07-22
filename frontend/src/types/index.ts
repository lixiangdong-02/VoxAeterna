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
  user_id?: number
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

export interface HistoryRecord {
  task_id: string
  state: TaskState
  progress: number | null
  text: string | null
  audio_path: string | null
  duration_seconds: number | null
  sample_rate: number | null
  error_message: string | null
  prompt_text: string | null
  speed_factor: number | null
  ref_audio_path: string | null
  created_at: string | null
}

/** 字体方案 */
export interface FontConfig {
  display: string   // 页面大标题
  body: string      // 正文
  mono: string      // 代码/数据
}

/** 音色配对 */
export interface VoiceProfile {
  id: string
  name: string
  description: string
  t2s_file: string
  vits_file: string
  image: string | null
  created_at: string
}

/** 保存的音频片段 */
export interface SavedClip {
  id: string              // uuid
  name: string            // 显示名，如 "合成-20260719_2300"
  blob: Blob              // 音频原始数据
  url: string             // ObjectURL
  duration: number        // 秒
  createdAt: string       // ISO 时间
}

/** 编辑区轨道 —— 一个轨道是一个 SavedClip 的引用 + 编辑状态 */
export interface EditorTrack {
  id: string
  clipId: string
  name: string
  url: string
  duration: number
  startOffset: number     // 轨内裁剪起点（秒）
  endOffset: number       // 轨内裁剪终点（秒）
}

// ==================== 用户 & 订阅 ====================

export interface UserInfo {
  id: number
  email: string
  username: string
  role: string
  status?: string
  created_at: string | null
}

export interface SubscriptionStatus {
  plan: string
  status: string
  starts_at: string | null
  expires_at: string | null
  auto_renew: boolean
  subscription_id: number | null
  trial_remaining?: number
}

export interface UsageStats {
  total_syntheses: number
  total_duration: number
  month_syntheses: number
  month_duration: number
  account_age_days: number
}

export interface PaymentRecord {
  id: number
  plan: string
  amount: number
  status: string
  payjs_order_id: string
  paid_at: string | null
  created_at: string | null
}

export interface ActiveSession {
  id: number
  device_fingerprint: string
  created_at: string | null
  is_current: boolean
}


// ==================== Window API ====================

declare global {
  interface Window {
    appVersion?: {
      get: () => Promise<string>
      openUrl: (url: string) => Promise<void>
    }
  }
}

