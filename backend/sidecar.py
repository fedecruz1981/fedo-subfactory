import sys
import json
import threading
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from .pipeline import ejecutar_pipeline
from . import utilidades

enviar_lock = threading.Lock()
jobs_activos = {}
executor = None

def enviar_evento(evento):
    with enviar_lock:
        line = json.dumps(evento, ensure_ascii=False)
        sys.stdout.write(line + '\n')
        sys.stdout.flush()


def doctor_report():
    """Reporta el estado de las herramientas del sidecar al proceso principal."""
    checks = []

    checks.append({
        'id': 'python',
        'label': 'Python',
        'required': True,
        'status': 'ok',
        'version': sys.version.split()[0],
        'message': 'Python disponible.',
        'hint': None,
    })

    # Verificar whisper (faster_whisper)
    whisper_ok = False
    whisper_version = None
    try:
        from faster_whisper import __version__ as fw_version
        whisper_ok = True
        whisper_version = fw_version
    except ImportError:
        pass
    checks.append({
        'id': 'faster_whisper',
        'label': 'faster-whisper',
        'required': True,
        'status': 'ok' if whisper_ok else 'missing',
        'version': whisper_version,
        'message': ('faster-whisper disponible.' if whisper_ok
                    else 'faster-whisper no está instalado. La transcripción fallará.'),
        'hint': None if whisper_ok else 'pip install -U faster-whisper',
    })

    # Verificar ffmpeg
    for tool in ('ffmpeg', 'ffprobe'):
        exe = shutil.which(tool)
        version = None
        missing = exe is None
        if exe:
            try:
                res = subprocess.run([exe, '-version'], capture_output=True, text=True, timeout=10)
                out = (res.stdout or res.stderr) or ''
                version = out.strip().splitlines()[0] if out.strip() else None
                missing = res.returncode != 0
            except Exception:
                missing = True
        label = 'FFmpeg' if tool == 'ffmpeg' else 'FFprobe'
        checks.append({
            'id': tool,
            'label': label,
            'required': True,
            'status': 'missing' if missing else 'ok',
            'version': version,
            'message': (label + ' disponible.' if not missing
                        else label + ' no está en el PATH. La transcripción y el renderizado fallarán.'),
            'hint': None if not missing else 'https://ffmpeg.org/download.html',
        })

    # Verificar ctranslate2 (dependencia de faster_whisper)
    ct2_ok = False
    try:
        import ctranslate2
        ct2_ok = True
    except ImportError:
        pass
    checks.append({
        'id': 'ctranslate2',
        'label': 'ctranslate2',
        'required': True,
        'status': 'ok' if ct2_ok else 'missing',
        'version': getattr(ctranslate2, '__version__', None) if ct2_ok else None,
        'message': ('ctranslate2 disponible.' if ct2_ok
                    else 'ctranslate2 no está instalado. faster-whisper no funcionará.'),
        'hint': None if ct2_ok else 'pip install -U ctranslate2',
    })

    enviar_evento({'type': 'doctor', 'checks': checks})

def procesar_job(job_id, url, config, executor_ref):
    enviar_evento({
        'job_id': job_id,
        'stage': 'en_cola',
        'progress': 0,
        'message': 'Procesando...'
    })
    ejecutar_pipeline(job_id, url, config, callback=enviar_evento)
    with enviar_lock:
        jobs_activos.pop(job_id, None)

def procesar_comando(comando):
    global executor

    cmd = comando.get('cmd')

    if cmd == 'process_job':
        job_id = comando['job_id']
        url = comando['url']
        config = comando.get('config', {})
        max_paralelo = config.get('max_paralelo', 1)

        if executor is None or executor._max_workers != max_paralelo:
            if executor:
                executor.shutdown(wait=False)
            executor = ThreadPoolExecutor(max_workers=max_paralelo)

        if job_id not in jobs_activos:
            jobs_activos[job_id] = True
            executor.submit(procesar_job, job_id, url, config, executor)

    elif cmd == 'resume_job':
        job_id = comando['job_id']
        config = comando.get('config', {})
        max_paralelo = config.get('max_paralelo', 1)

        estado = utilidades.cargar_estado(job_id)
        if not estado:
            enviar_evento({
                'job_id': job_id,
                'stage': 'error',
                'message': 'No se encontró estado previo para este job'
            })
            return

        url = estado.get('url', '')
        if executor is None or executor._max_workers != max_paralelo:
            if executor:
                executor.shutdown(wait=False)
            executor = ThreadPoolExecutor(max_workers=max_paralelo)

        if job_id not in jobs_activos:
            jobs_activos[job_id] = True
            executor.submit(procesar_job, job_id, url, config, executor)

    elif cmd == 'load_pending':
        jobs_pendientes = utilidades.listar_jobs_pendientes()
        for estado in jobs_pendientes:
            enviar_evento({
                'job_id': estado['job_id'],
                'stage': 'pending_resume',
                'progress': 0,
                'message': f"Interrumpido en: {estado.get('stage', 'desconocido')}",
                'url': estado.get('url', ''),
                'titulo': estado.get('titulo', ''),
            })

    elif cmd == 'cancel_job':
        job_id = comando.get('job_id')
        enviar_evento({
            'job_id': job_id,
            'stage': 'cancelado',
            'progress': 0,
            'message': 'Cancelado por el usuario'
        })
        jobs_activos.pop(job_id, None)

def main():
    sys.stderr.write('Sidecar Python iniciado\n')
    sys.stderr.flush()
    doctor_report()

    for linea in sys.stdin:
        linea = linea.strip()
        if not linea:
            continue

        try:
            comando = json.loads(linea)
            procesar_comando(comando)
        except json.JSONDecodeError:
            enviar_evento({
                'stage': 'error',
                'message': f'JSON invalido: {linea}'
            })
        except Exception as e:
            enviar_evento({
                'stage': 'error',
                'message': f'Error inesperado: {str(e)}'
            })

    if executor:
        executor.shutdown(wait=True)

if __name__ == '__main__':
    main()
