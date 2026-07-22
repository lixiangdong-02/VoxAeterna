/// <reference types="vite/client" />

interface WindowControls {
  minimize: () => Promise<void>
  maximize: () => Promise<void>
  close: () => Promise<void>
  isMaximized: () => Promise<boolean>
  onMaximizeChange: (callback: (maximized: boolean) => void) => void
}

interface Window {
  ipcRenderer: {
    on(channel: string, listener: (...args: any[]) => void): void
    off(channel: string, listener: (...args: any[]) => void): void
    send(channel: string, ...args: any[]): void
    invoke(channel: string, ...args: any[]): Promise<any>
  }
  deviceFingerprint: {
    get: () => Promise<string>
  }
  windowControls: WindowControls
}
