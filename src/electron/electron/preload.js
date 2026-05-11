const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  openPdf: (filename, displayName) => ipcRenderer.invoke('open-method-pdf', filename, displayName),

  // This is the modern, secure way to get a file path in Electron
  getFilePath: (file) => {
    // Check if modern webUtils exists (Electron 29+)
    if (webUtils && webUtils.getPathForFile) {
      return webUtils.getPathForFile(file);
    }
    // Fallback for older Electron versions
    return file.path;
  }
});