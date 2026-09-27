import sys
import json
import threading
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
