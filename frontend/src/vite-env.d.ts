/// <reference types="vite/client" />

interface WindowControls {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
  onMaximizeChange: (callback: (maximized: boolean) => void) => void
}

interface EnvSetupAPI {
  check: () => Promise<{ python: boolean; pythonPath: string; gpu: boolean; deps: { ok: boolean; missing: string[] } }>
  checkModels: () => Promise<boolean>
  downloadModels: () => Promise<{ success: boolean; error?: string }>
  cancel: () => Promise<{ message: string }>
  restart: () => Promise<void>
  onProgress: (callback: (data: any) => void) => void
  removeProgressListener: () => void
}

interface Window {
  ipcRenderer: {
    on(channel: string, listener: (...args: any[]) => void): void
    off(channel: string, listener: (...args: any[]) => void): void
    send(channel: string, ...args: any[]): void
    invoke(channel: string, ...args: any[]): Promise<any>
  }
  deviceFingerprint: { get: () => Promise<string> }
  windowControls: WindowControls
  envSetup?: EnvSetupAPI
  appVersion?: { get: () => Promise<string>; openUrl: (url: string) => Promise<void> }
}
