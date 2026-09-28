const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow = null
let sidecar = null
let sidecarState = 'starting'
let sidecarStderrTail = []
let sidecarRestarts = 0
const MAX_SIDECAR_RESTARTS = 3
let lastSidecarDoctor = null

function buildDoctorReport() {
  const checks = []
  const python = lastSidecarDoctor?.find(c => c.id === 'python') || {
    id: 'python',
    label: 'Python',
    required: true,
    status: 'not-checked',
    version: null,
    message: 'Python requerido para el sidecar de transcripción.',
    hint: 'https://www.python.org/downloads/'
  }
  checks.push(python)

  if (lastSidecarDoctor) {
    for (const c of lastSidecarDoctor) {
      if (c.id !== 'python') checks.push(c)
    }
  }
  const ok = checks.every(c => c.status === 'ok')
  return { ok, sidecarState, checks }
}

async function pushDoctor() {
  if (mainWindow) {
    const report = await buildDoctorReport()
    mainWindow.webContents.send('doctor:report', report)
  }
}

function encontrarPython () {
  const { execSync } = require('child_process')
  const candidatos = [
    'python',
    'python3',
    'py',
    'C:\\Python314\\python.exe',
    'C:\\Python311\\python.exe',
    'C:\\Python310\\python.exe',
  ]
  for (const p of candidatos) {
    try {
      execSync(`"${p}" --version`, { encoding: 'utf-8', stdio: 'pipe' })
      return p
    } catch (e) { continue }
  }
  return null
}

function createWindow () {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: '#0A0A0F',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function iniciarSidecar () {
  const pythonPath = encontrarPython()
  console.log('Python path:', pythonPath)

  if (!pythonPath) {
    console.error('Python no encontrado. El sidecar no puede iniciarse.')
    if (mainWindow) {
      mainWindow.webContents.send('sidecar:status', {
        state: 'errored',
        message: 'Python no está instalado o no está en el PATH. Instálalo desde https://www.python.org/downloads/'
      })
    }
    return
  }

  const fullEnv = Object.assign({}, process.env)
  if (!fullEnv.GEMINI_API_KEY) {
    try {
      const { execSync } = require('child_process')
      fullEnv.GEMINI_API_KEY = execSync('powershell -Command "[System.Environment]::GetEnvironmentVariable(\'GEMINI_API_KEY\', \'User\')"', { encoding: 'utf-8' }).trim()
    } catch (e) {}
  }

  const isPackaged = app.isPackaged
  const cwd = isPackaged
    ? path.join(process.resourcesPath, 'app.asar.unpacked')
    : path.join(__dirname, '..')

  sidecar = spawn(pythonPath, ['-m', 'backend.sidecar'], {
    cwd,
    stdio: ['pipe', 'pipe', 'pipe'],
    env: fullEnv
  })

  let buffer = ''
  let sidecarReady = false

  sidecar.stdout.on('data', (data) => {
    buffer += data.toString()
    const lineas = buffer.split('\n')
    buffer = lineas.pop()

    for (const linea of lineas) {
      const trimmed = linea.trim()
      if (!trimmed) continue
      try {
        const evento = JSON.parse(trimmed)
        if (evento.type === 'ready') {
          sidecarState = 'ready'
          sidecarReady = true
          sidecarRestarts = 0
          pushDoctor()
        } else if (evento.type === 'doctor') {
          if (Array.isArray(evento.checks)) {
            lastSidecarDoctor = evento.checks
          }
          pushDoctor()
        }
        if (mainWindow && mainWindow.webContents) {
          mainWindow.webContents.send('sidecar:evento', evento)
        }
      } catch (e) {
        console.log('[sidecar stdout]', trimmed)
      }
    }
  })

  sidecar.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    if (!msg) return
    console.log('[sidecar]', msg)
    sidecarStderrTail.push(msg)
    if (sidecarStderrTail.length > 6) sidecarStderrTail.shift()
  })

  sidecar.on('error', (err) => {
    console.error('Error al iniciar sidecar:', err.message)
    sidecar = null
    sidecarState = 'errored'
    const reason = err.code === 'ENOENT'
      ? 'Python no está instalado o no está en el PATH.'
      : err.code === 'EACCES'
        ? 'Windows bloqueó el acceso a Python (SmartScreen o antivirus).'
        : err.message
    if (mainWindow) {
      mainWindow.webContents.send('sidecar:status', { state: 'errored', message: reason })
    }
    pushDoctor()
  })

  sidecar.on('close', (code) => {
    console.log(`Sidecar terminó con código ${code}`)
    sidecar = null
    if (sidecarReady) {
      sidecarState = 'errored'
      sidecarRestarts = 0
      const trace = sidecarStderrTail.join('\n')
      const message = trace
        ? `El sidecar terminó tras arrancar (código ${code}). ${trace.split('\n')[0]}`
        : `El sidecar terminó de forma inesperada (código ${code}).`
      if (mainWindow) {
        mainWindow.webContents.send('sidecar:status', { state: 'errored', message })
      }
      pushDoctor()
      return
    }
    sidecarRestarts++
    if (sidecarRestarts <= MAX_SIDECAR_RESTARTS) {
      console.log(`Reintentando sidecar (${sidecarRestarts}/${MAX_SIDECAR_RESTARTS})`)
      setTimeout(iniciarSidecar, 1000)
    } else {
      sidecarState = 'errored'
      const trace = sidecarStderrTail.join('\n')
      const message = trace
        ? `El sidecar no pudo iniciar. ${trace.split('\n')[0]}`
        : `El sidecar no pudo iniciar (código ${code}). Comprobá que Python, ffmpeg y whisper estén instalados.`
      if (mainWindow) {
        mainWindow.webContents.send('sidecar:status', { state: 'errored', message })
      }
      pushDoctor()
    }
  })
}

function detenerSidecar () {
  if (sidecar) {
    try {
      sidecar.stdin.end()
      sidecar.kill()
    } catch (e) {}
    sidecar = null
  }
}

app.whenReady().then(() => {
  createWindow()
  iniciarSidecar()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  detenerSidecar()
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

ipcMain.handle('sidecar:enviar', (evento, comando) => {
  if (sidecar && sidecar.stdin.writable) {
    sidecar.stdin.write(JSON.stringify(comando) + '\n')
    return true
  }
  return false
})

ipcMain.handle('doctor:get', async () => {
  const checks = []
  const python = lastSidecarDoctor?.find(c => c.id === 'python') || {
    id: 'python',
    label: 'Python',
    required: true,
    status: 'not-checked',
    version: null,
    message: 'Python requerido para el sidecar de transcripción.',
    hint: 'https://www.python.org/downloads/'
  }
  checks.push(python)
  if (lastSidecarDoctor) {
    for (const c of lastSidecarDoctor) {
      if (c.id !== 'python') checks.push(c)
    }
  }
  const ok = checks.every(c => c.status === 'ok')
  return { ok, sidecarState, checks }
})

async function pushDoctor() {
  if (mainWindow) {
    const report = await (async () => {
      const checks = []
      const python = lastSidecarDoctor?.find(c => c.id === 'python') || {
        id: 'python',
        label: 'Python',
        required: true,
        status: 'not-checked',
        version: null,
        message: 'Python requerido para el sidecar de transcripción.',
        hint: 'https://www.python.org/downloads/'
      }
      checks.push(python)
      if (lastSidecarDoctor) {
        for (const c of lastSidecarDoctor) {
          if (c.id !== 'python') checks.push(c)
        }
      }
      const ok = checks.every(c => c.status === 'ok')
      return { ok, sidecarState, checks }
    })()
    mainWindow.webContents.send('doctor:report', report)
  }
}
