# Licencias de terceros

**fedo~subfactory** es software propio, distribuido bajo licencia MIT (ver [`LICENSE`](./LICENSE)).
Este documento detalla los componentes de terceros que usa y con qué licencia se distribuye cada
uno.

> Documento informativo; no es asesoramiento legal.

## 1. Incluidos en el instalador

### Runtime de Electron

| Componente | Versión | Licencia |
|---|---|---|
| [Electron](https://github.com/electron/electron) | 44.x | MIT |
| Chromium (incluido en Electron) | — | BSD-3-Clause y otras licencias libres |
| Node.js (incluido en Electron) | — | MIT |

El runtime de Electron trae sus propios avisos (`LICENSE` y `LICENSES.chromium.html`), que
Chromium exige conservar al redistribuir.

### Dependencias incluidas en la aplicación

| Componente | Versión | Licencia | Uso |
|---|---|---|---|
| [React](https://react.dev) / [React DOM](https://react.dev) | 18.3 | MIT | Interfaz |

El instalador incluye además el **código propio** del frontend y del backend Python
(`backend/**`), pero **no** incluye Python, pip ni las bibliotecas de Python.

### Herramientas de desarrollo (no entran en el instalador)

| Componente | Versión | Licencia |
|---|---|---|
| Vite | 8.x | MIT |
| TypeScript | 7.x | Apache-2.0 |
| Tailwind CSS | 3.4 | MIT |
| PostCSS / Autoprefixer | 8.x / 10.x | MIT |
| ESLint (`@eslint/js`, `globals`) | — | MIT |
| electron-builder | 26.x | MIT |
| Playwright (`@playwright/test`) | 1.63 | Apache-2.0 |
| `@vitejs/plugin-react`, `concurrently`, `cross-env`, `wait-on` | — | MIT |

## 2. Requeridos en el sistema (no se redistribuyen)

| Componente | Licencia | Notas |
|---|---|---|
| [Python](https://www.python.org) 3.x | PSF-2.0 | Requerido por el backend |
| [FFmpeg](https://ffmpeg.org) (`ffmpeg`, `ffprobe`) | LGPL-2.1+ o GPL-2.0+ según cómo esté compilado | **No se empaqueta**: lo instala el usuario |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT | Transcripción |
| [CTranslate2](https://github.com/OpenNMT/CTranslate2) | MIT | Motor de inferencia |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense (dominio público) | Descarga |
| [deep-translator](https://github.com/nidhaloff/deep-translator) | MIT | Envoltorio de Google Translate |
| [srt](https://github.com/cdown/srt) | MIT | (declarado; el proyecto escribe los `.srt` por su cuenta) |

Estos paquetes se instalan con `pip` **en la máquina del usuario**: no forman parte del instalador.

### Modelos descargados por el usuario

| Modelo | Licencia | Notas |
|---|---|---|
| Whisper (OpenAI), vía faster-whisper | MIT | Modelos de transcripción |
| NLLB-200 (Meta), motor local | CC-BY-NC-4.0 | **Solo uso no comercial**, según la licencia del modelo |

El motor **NLLB** corre localmente, pero su modelo está bajo licencia **CC-BY-NC-4.0**: no se puede
usar en un contexto comercial. Si el proyecto se va a usar comercialmente, hay que elegir otro
motor (Google, o un LLM del proveedor elegido) o migrar a un modelo con licencia permisiva.

## 3. Dependencias de copyleft

**Importante:** `pysrt` (GPLv3) estaba declarado en `backend/requirements.txt`. No se usa en
ninguna parte del código (se quitó), pero vale la regla general: las dependencias **GPL** obligan a
distribuir el código fuente bajo GPL si el programa se distribuye. Por eso este proyecto:

- no empaqueta bibliotecas de Python dentro del instalador (las instala el usuario con `pip`);
- mantiene el backend Python como **proceso aparte** (sidecar), no enlazado al binario de Electron.

Antes de agregar una dependencia nueva (sobre todo Python), revisá su licencia:

```powershell
pip install -r backend/requirements.txt
pip-licenses --format=markdown
```

## 4. Servicios de terceros (no son software incluido)

| Servicio | Costo | Datos que salen de tu equipo |
|---|---|---|
| Google Translate (vía deep-translator) | Gratis, sin clave | El texto de los subtítulos |
| OpenAI / Groq / Google Gemini (LLM, con clave propia) | Según el proveedor | El texto de los subtítulos |
| NLLB (local) | Gratis, sin conexión | Ninguno |

Al usar esos servicios se aplican **sus** términos de uso y políticas de privacidad.

## 5. Cómo regenerar esta lista

```powershell
npm ls --depth=0
npx license-checker --direct

pip install -r backend/requirements.txt
pip-licenses --format=markdown
```

Última verificación: 2026-10-17.
