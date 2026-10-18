# fedo-subfactory

**Fábrica de Subtítulos** — aplicación de escritorio que descarga videos, transcribe el audio, traduce las voces y genera/incrusta subtítulos.

![estado](https://img.shields.io/badge/version-0.1.2-blue)

## Descargas

**Windows x64 primero** — El instalador NSIS es para Windows x64.

Instalador para Windows (x64).

| Versión | Archivo | Tamaño |
|---------|---------|--------|
| [0.1.2](https://github.com/fedecruz1981/fedo-subfactory/releases/tag/v0.1.2) | `Fabrica.de.Subtitulos.Setup.0.1.2.exe` | 106,8 MB |
| [0.1.1](https://github.com/fedecruz1981/fedo-subfactory/releases/tag/v0.1.1) | `Fabrica.de.Subtitulos.Setup.0.1.1.exe` | 106,7 MB |

[Todas las releases](https://github.com/fedecruz1981/fedo-subfactory/releases) · [reportar un problema](https://github.com/fedecruz1981/fedo-subfactory/issues)

> **Aviso legal — YouTube**: Esta herramienta usa `yt-dlp` para descargar videos. Los Términos de Servicio de YouTube prohíben la descarga de contenido sin autorización expresa del titular de derechos. Úsala solo para contenido propio, de dominio público, o con licencia que lo permita. El autor no se responsabiliza del uso indebido.

## Qué hace

Pegás un link de video y la app hace el pipeline completo:

1. **Descarga** el video (o solo el audio)
2. **Transcribe** la pista de audio con Whisper (CPU o GPU)
3. **Traduce** los subtítulos con el motor que elijas
4. **Genera** el archivo de subtítulos (SRT) y/o **incrusta** los subtítulos en el video renderizado

Todo con una **cola de trabajos** que muestra progreso en vivo, permite cancelar, reintentar y **retomar** trabajos interrumpidos.

## Stack

- **Frontend**: Electron + React + Vite + Tailwind CSS
- **Backend**: Python sidecar (`backend/`) con Whisper, yt-dlp y ffmpeg
- **Motores de traducción**: Google Translate, LLMs (Gemini, Groq, OpenAI) y NLLB

## Motores de traducción

| Motor | Uso |
|-------|-----|
| `google` | Traducción gratuita por API de Google |
| `llm` | Traducción por LLM (Gemini, Groq o OpenAI) con clave API |
| `nllb` | Modelo local de Meta (sin red, requiere NLLB instalado) |

> Las claves API se leen desde variables de entorno del sistema (ej. `GEMINI_API_KEY`). No se guardan en el repositorio.

## Requisitos previos

**Node 24** (Vite 8 pide 20.19 o superior) y Python 3.10+.

Además de Node y Python, el pipeline necesita estos binarios y modelos **fuera de npm/pip**:

| Dependencia | Para qué | Cómo se instala |
|-------------|----------|-----------------|
| **ffmpeg / ffprobe** | Descarga, merge de audio/video, incrustado de subtítulos | Windows: [ffmpeg.org](https://ffmpeg.org/download.html) y agregarlo al PATH · macOS: `brew install ffmpeg` · Linux: `sudo apt install ffmpeg` |
| **yt-dlp** | Descarga de los videos | `pip install -U yt-dlp` (o el paquete del backend) |
| **Whisper** | Transcripción del audio | `pip install -U openai-whisper` — la primera corrida descarga el modelo (~150 MB para `base`, ~1.5 GB para `large`) al directorio de cache de Whisper |
| **CUDA (opcional)** | Acelera la transcripción en GPU NVIDIA | Drivers NVIDIA + `pip install -U torch` con build CUDA |

En Windows, `ffmpeg` tiene que estar **en el PATH del sistema** antes de abrir la app:
el sidecar Python lo invoca por nombre, no por ruta absoluta.

## Instalación

```bash
# 1. Dependencias de Node
npm install

# 2. Dependencias de Python
cd backend
pip install -r requirements.txt
cd ..
```

## Desarrollo

```bash
npm run dev
```

## Calidad

```bash
npm run lint
```

## Construcción

```bash
# instalador (Windows: NSIS)
npm run dist

# solo carpeta empaquetada
npm run pack
```

## Estructura

```
fedo-subfactory/
├── electron/            # Proceso principal (ventana + sidecar Python)
├── src/                 # Renderer (React)
│   ├── componentes/     # UI de cola de trabajos y configuración
│   └── App.jsx
├── backend/             # Backend Python
│   ├── sidecar.py       # Loop de comandos (frontera con Electron)
│   ├── descargador.py   # Descarga con yt-dlp
│   ├── transcriptor.py  # Transcripción con Whisper
│   ├── renderizador.py  # Render final con ffmpeg
│   ├── pipeline.py      # Orquestación del flujo
│   └── traductores/     # google.py, llm.py, nllb.py, base.py
└── package.json
```

## Estado

Versión **0.1.2** publicada (instalador NSIS para Windows x64). El flujo de descarga → transcripción → traducción → render funciona de punta a punta, con cola de trabajos, cancelación, reintentos y retomado. Pendiente: incrustación de subtítulos por pulir y empaquetado multiplataforma.

## Privacidad

La app corre en tu equipo y no envía nada a servidores del autor. Ahora bien, según el motor de
traducción que elijas, el **texto de los subtítulos** puede salir de tu máquina:

| Motor | Qué se envía | A dónde |
|---|---|---|
| Google Translate | El texto de los subtítulos | Servidores de Google (vía `deep-translator`) |
| LLM (OpenAI / Groq / Gemini) | El texto de los subtítulos | Al proveedor elegido, con **tu** clave API |
| NLLB (local) | Nada | Corre en tu equipo |

- La descarga (`yt-dlp`) y la transcripción (Whisper) corren localmente; la descarga, obviamente,
  se conecta a YouTube.
- Las claves API que cargues quedan guardadas en la configuración local de la app.
- Al usar esos servicios aceptás sus términos y sus políticas de privacidad.
- No proceses contenido de terceros sin autorización: los subtítulos traducidos son una obra
  derivada.

## Licencia

MIT — ver [`LICENSE`](./LICENSE).

Componentes de terceros (Electron/Chromium, React, faster-whisper, CTranslate2, yt-dlp, FFmpeg,
etc.): ver [`THIRD-PARTY.md`](./THIRD-PARTY.md). Ojo: el modelo **NLLB-200** es CC-BY-NC-4.0
(**solo uso no comercial**).

## Aviso legal

- **Sin relación con YouTube, Google ni Meta.** Proyecto independiente, sin afiliación ni aval.
- **Uso responsable.** Descargá y traducí solo contenido que puedas usar (ver el aviso de YouTube
  más arriba). Sos responsable del contenido que procesás y de su difusión.
- **Sin garantías.** El software se entrega «tal cual», sin garantía de ningún tipo (ver
  `LICENSE`).