const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('fedoSubfactory', {
  enviarComando: (comando) => ipcRenderer.invoke('sidecar:enviar', comando),
  onEvento: (callback) => {
    ipcRenderer.on('sidecar:evento', (evento, data) => callback(data))
  }
})
