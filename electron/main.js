const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow = null
let sidecar = null

function encontrarPython () {
  const { execSync } = require('child_process')
  const posibles = [
    'C:\\Python314\\python.exe',
    'C:\\Python311\\python.exe',
    'C:\\Python310\\python.exe',
    'python'
  ]
  for (const p of posibles) {
    try {
      execSync(`"${p}" --version`, { encoding: 'utf-8', stdio: 'pipe' })
      return p
    } catch (e) { continue }
  }
  return 'python'
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
      nodeIntegration: false
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

  const fullEnv = Object.assign({}, process.env)
  const denoPath = 'C:\\Users\\fedo\\AppData\\Local\\Microsoft\\WinGet\\Packages\\DenoLand.Deno_Microsoft.Winget.Source_8wekyb3d8bbwe'
  const ffmpegPath = 'C:\\Users\\fedo\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-9.0-full_build\\bin'
  const nvidiaBase = 'C:\\Users\\fedo\\AppData\\Roaming\\Python\\Python314\\site-packages\\nvidia'
  const nvidiaDlls = nvidiaBase + '\\cublas\\bin;' + nvidiaBase + '\\cuda_nvrtc\\bin;' + nvidiaBase + '\\cuda_runtime\\bin;' + nvidiaBase + '\\cudnn\\bin'
  fullEnv.PATH = denoPath + ';' + ffmpegPath + ';C:\\Python314;' + nvidiaDlls + ';' + (fullEnv.PATH || '')
  if (!fullEnv.GEMINI_API_KEY) {
    try {
      const { execSync } = require('child_process')
      fullEnv.GEMINI_API_KEY = execSync('powershell -Command "[System.Environment]::GetEnvironmentVariable(\'GEMINI_API_KEY\', \'User\')"', { encoding: 'utf-8' }).trim()
    } catch (e) {}
  }

  sidecar = spawn(pythonPath, ['-m', 'backend.sidecar'], {
    cwd: path.join(__dirname, '..'),
    stdio: ['pipe', 'pipe', 'pipe'],
    env: fullEnv
  })

  let buffer = ''

  sidecar.stdout.on('data', (data) => {
    buffer += data.toString()
    const lineas = buffer.split('\n')
    buffer = lineas.pop()

    for (const linea of lineas) {
      const trimmed = linea.trim()
      if (!trimmed) continue
      try {
        const evento = JSON.parse(trimmed)
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
    if (msg) console.log('[sidecar]', msg)
  })

  sidecar.on('error', (err) => {
    console.error('Error al iniciar sidecar:', err.message)
    sidecar = null
  })

  sidecar.on('close', (code) => {
    console.log(`Sidecar terminó con código ${code}`)
    sidecar = null
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
