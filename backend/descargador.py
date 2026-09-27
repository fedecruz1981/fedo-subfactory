import yt_dlp
import os
import re

class LoggerSilencioso:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass
    def info(self, msg): pass

def sanitizar_nombre(nombre):
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre[:200] if nombre else 'video'

def descargar_video(url, carpeta_destino, callback_progreso=None):
    def hook_progreso(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            descargado = d.get('downloaded_bytes', 0)
            if total > 0:
                porcentaje = int(descargado / total * 100)
                if callback_progreso:
                    callback_progreso(porcentaje, f'Descargando... {porcentaje}%')
        elif d['status'] == 'finished':
            if callback_progreso:
                callback_progreso(100, 'Descarga completa')

    opciones = {
        'outtmpl': os.path.join(carpeta_destino, '%(title).200s.%(ext)s'),
        'restrictfilenames': True,
        'format': 'bv*+ba/b',
        'merge_output_format': 'mp4',
        'progress_hooks': [hook_progreso],
        'logger': LoggerSilencioso(),
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'retries': 5,
        'fragment_retries': 5,
        'extractor_retries': 5,
        'extractor_args': {'youtube': {'player_client': ['web_embedded']}},
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }

    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(url, download=True)
        titulo = sanitizar_nombre(info.get('title', 'video'))
        archivo = ydl.prepare_filename(info)

        if not archivo.endswith('.mp4'):
            base = os.path.splitext(archivo)[0]
            archivo = base + '.mp4'

        return archivo, titulo
