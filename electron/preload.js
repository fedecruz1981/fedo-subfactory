const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('fedoSubfactory', {
  enviarComando: (comando) => ipcRenderer.invoke('sidecar:enviar', comando),
  onEvento: (callback) => {
    ipcRenderer.on('sidecar:evento', (evento, data) => callback(data))
  },
  getDoctor: () => ipcRenderer.invoke('doctor:get'),
  onDoctorReport: (callback) => {
    ipcRenderer.on('doctor:report', (evento, data) => callback(data))
  },
  onSidecarStatus: (callback) => {
    ipcRenderer.on('sidecar:status', (evento, data) => callback(data))
  }
})
