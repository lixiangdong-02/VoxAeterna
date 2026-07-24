import { ipcRenderer, contextBridge } from 'electron'

// --------- Expose some API to the Renderer process ---------
contextBridge.exposeInMainWorld('ipcRenderer', {
  on(...args: Parameters<typeof ipcRenderer.on>) {
    const [channel, listener] = args
    return ipcRenderer.on(channel, (event, ...args) => listener(event, ...args))
  },
  off(...args: Parameters<typeof ipcRenderer.off>) {
    const [channel, ...omit] = args
    return ipcRenderer.off(channel, ...omit)
  },
  send(...args: Parameters<typeof ipcRenderer.send>) {
    const [channel, ...omit] = args
    return ipcRenderer.send(channel, ...omit)
  },
  invoke(...args: Parameters<typeof ipcRenderer.invoke>) {
    const [channel, ...omit] = args
    return ipcRenderer.invoke(channel, ...omit)
  },

  // You can expose other APTs you need here.
  // ...
})

// 设备指纹 API
contextBridge.exposeInMainWorld('deviceFingerprint', {
  get: () => ipcRenderer.invoke('get-device-fingerprint'),
})

// 窗口控制 API
contextBridge.exposeInMainWorld('windowControls', {
  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),
  isMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  onMaximizeChange: (callback: (maximized: boolean) => void) => {
    ipcRenderer.on('window-maximized', (_event, maximized: boolean) => callback(maximized))
  },
})

// 版本更新 API
contextBridge.exposeInMainWorld('appVersion', {
  get: () => ipcRenderer.invoke('get-app-version'),
  openUrl: (url: string) => ipcRenderer.invoke('open-external-url', url),
})

// 环境初始化 API
contextBridge.exposeInMainWorld('envSetup', {
  check: () => ipcRenderer.invoke('env-setup:check'),
  downloadPython: () => ipcRenderer.invoke('env-setup:download-python'),
  install: () => ipcRenderer.invoke('env-setup:install'),
  cancel: () => ipcRenderer.invoke('env-setup:cancel'),
  restart: () => ipcRenderer.invoke('env-setup:restart'),
  checkModels: () => ipcRenderer.invoke('env-setup:check-models'),
  checkTorch: () => ipcRenderer.invoke('env-setup:check-torch'),
  torchGuide: () => ipcRenderer.invoke('env-setup:torch-guide'),
  downloadModels: () => ipcRenderer.invoke('env-setup:download-models'),
  onProgress: (callback: (data: any) => void) => {
    ipcRenderer.on('env-setup:progress', (_event, data: any) => callback(data))
  },
  removeProgressListener: () => {
    ipcRenderer.removeAllListeners('env-setup:progress')
  },
})
