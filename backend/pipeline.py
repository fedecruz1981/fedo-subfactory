import os
import time
from . import utilidades
from .utilidades import sanitizar_nombre
from .descargador import descargar_video
from .transcriptor import transcribir_audio
from .renderizador import escribir_srt, incrustar_subtitulos
from .traductores.nllb import TraductorNLLB
from .traductores.google import TraductorGoogle
from .traductores.llm import TraductorLLM

TRADUCTORES = {
    'nllb': TraductorNLLB,
    'google': TraductorGoogle,
    'llm': TraductorLLM,
}

TAMANIO_LOTE = 10

PASOS = ['pending', 'downloaded', 'transcribed', 'translated', 'srt_done', 'done']

def indice_paso(paso):
    try:
        return PASOS.index(paso)
    except ValueError:
        return -1

def traducir_con_contexto(segmentos, config, emitir, progreso_base=60, progreso_fin=80, segmentos_previos=None, job_id=None):
    motor = config.get('motor_traduccion', 'nllb')
    ClaseTraductor = TRADUCTORES.get(motor, TraductorNLLB)

    if motor == 'llm':
        traductor = ClaseTraductor(
            api_key=config.get('llm_api_key', ''),
            model=config.get('llm_modelo', 'gpt-4o-mini'),
            proveedor=config.get('llm_proveedor', 'openai')
        )
    else:
        traductor = ClaseTraductor()

    total = len(segmentos)

    traducidos_previos = segmentos_previos[:len(segmentos_previos)] if segmentos_previos else []
    ya_traducidos = len(traducidos_previos)
    todos_traducidos = list(traducidos_previos)
    contexto_previo = ''

    if traducidos_previos and len(traducidos_previos) > 0:
        contexto_previo = ''.join(s.get('texto', '') for s in traducidos_previos[-TAMANIO_LOTE:])
        emitir('translating', progreso_base + (ya_traducidos / total) * (progreso_fin - progreso_base) * 0.5,
               f'Retando desde segmento {ya_traducidos}/{total}')

    start_idx = ya_traducidos

    for i in range(start_idx, total, TAMANIO_LOTE):
        lote = segmentos[i:i + TAMANIO_LOTE]
        num_lote = (i // TAMANIO_LOTE) + 1
        total_lotes = (total + TAMANIO_LOTE - 1) // TAMANIO_LOTE

        emitir('translating', progreso_base + (i / total) * (progreso_fin - progreso_base) * 0.5,
               f'Lote {num_lote}/{total_lotes} ({len(lote)} segmentos, contexto de {len(contexto_previo)} chars)')

        traducidos_lote, contexto_previo = traductor.traducir_lote(lote, contexto_previo)
        todos_traducidos.extend(traducidos_lote)

        progreso = progreso_base + (len(todos_traducidos) / total) * (progreso_fin - progreso_base)
        emitir('translating', progreso,
               f'Traducido: {len(todos_traducidos)}/{total} segmentos')

        if job_id:
            estado = utilidades.cargar_estado(job_id) or {}
            estado['segmentos_traducidos'] = todos_traducidos
            utilidades.guardar_estado(job_id, estado)

    return todos_traducidos


def ejecutar_pipeline(job_id, url, config, callback=None):
    def emitir(stage, progress=0, message='', **kwargs):
        if callback:
            callback({
                'job_id': job_id,
                'stage': stage,
                'progress': progress,
                'message': message,
                **kwargs
            })

    try:
        carpeta = utilidades.crear_carpeta_job(job_id)
        estado = utilidades.cargar_estado(job_id) or {
            'job_id': job_id,
            'url': url,
            'config': config,
            'stage': 'pending',
        }

        def guardar(overrides):
            nonlocal estado
            estado.update(overrides)
            utilidades.guardar_estado(job_id, estado)
            return estado
        desde_paso = estado.get('stage', 'pending') if estado else 'pending'

        if estado and estado.get('stage') == 'error':
            desde_paso = 'pending'
            estado['error'] = None

        paso_actual_idx = indice_paso(desde_paso)

        if paso_actual_idx > 0:
            emitir('resuming', 0, f'Retando desde: {desde_paso}')

        titulo = estado.get('titulo') if estado else None
        ruta_video = estado.get('ruta_video') if estado else None
        segmentos = estado.get('segmentos') if estado else None
        idioma = estado.get('idioma') if estado else None
        segmentos_traducidos = estado.get('segmentos_traducidos') if estado else None

        if ruta_video and os.path.exists(ruta_video):
            emitir('downloading', 30, f'Descargado previamente: {titulo or "video"}')
        elif paso_actual_idx <= indice_paso('pending'):
            emitir('downloading', 0, 'Iniciando descarga...')
            for intento in range(3):
                try:
                    def progreso_descarga(p, msg):
                        emitir('downloading', p * 0.3, msg)
                    ruta_video, titulo = descargar_video(url, carpeta, progreso_descarga)
                    break
                except Exception as e:
                    if intento < 2:
                        emitir('downloading', 0, f'Error (intento {intento+1}/3): {e}')
                        time.sleep(2 * (intento + 1))
                    else:
                        raise RuntimeError(f'Descarga falló tras 3 intentos: {e}')

            guardar({
                'stage': 'downloaded',
                'ruta_video': ruta_video,
                'titulo': titulo,
            })
            emitir('downloading', 30, f'Descargado: {titulo}')

        if paso_actual_idx < indice_paso('transcribed'):
            emitir('transcribing', 30, 'Iniciando transcripción...')

            def progreso_transcripcion(p, msg):
                emitir('transcribing', 30 + p * 0.3, msg)

            segmentos, idioma = transcribir_audio(
                ruta_video,
                modelo=config.get('modelo_whisper', 'medium'),
                dispositivo=config.get('dispositivo', 'cpu'),
                callback_progreso=progreso_transcripcion
            )
            guardar({
                'stage': 'transcribed',
                'segmentos': segmentos,
                'idioma': idioma,
            })
            emitir('transcribing', 60, f'Transcrito en {idioma}: {len(segmentos)} segmentos')

        if not segmentos:
            guardar({'stage': 'done', 'output_path': ruta_video})
            emitir('done', 100, 'Video procesado pero no se detectó habla. No se generaron subtítulos.', output_path=ruta_video)
            return

        if idioma != 'es':
            if paso_actual_idx < indice_paso('translated'):
                emitir('translating', 60, 'Traduciendo al español con contexto...')

                segmentos_traducidos = traducir_con_contexto(
                    segmentos, config, emitir,
                    progreso_base=60, progreso_fin=80,
                    segmentos_previos=segmentos_traducidos,
                    job_id=job_id
                )
                guardar({
                    'stage': 'translated',
                    'segmentos': segmentos,
                    'segmentos_traducidos': segmentos_traducidos,
                })
                emitir('translating', 80, f'Traducción completa: {len(segmentos_traducidos)} segmentos')
            else:
                emitir('translating', 80, f'Traducción previa cargada: {len(segmentos_traducidos)} segmentos')
                segmentos = segmentos_traducidos
        else:
            emitir('translating', 80, 'Video en español, saltando traducción')
            segmentos_traducidos = segmentos

        segmentos_finales = segmentos_traducidos or segmentos

        titulo_safe = sanitizar_nombre(titulo) if titulo else 'video'

        if paso_actual_idx < indice_paso('srt_done'):
            ruta_srt = os.path.join(carpeta, f'{titulo_safe}.srt')
            escribir_srt(segmentos_finales, ruta_srt)
            guardar({
                'stage': 'srt_done',
                'ruta_srt': ruta_srt,
            })
            emitir('renderizando', 85, 'Subtítulos .srt generados')

        ruta_srt = estado.get('ruta_srt') if estado else os.path.join(carpeta, f'{titulo_safe}.srt')

        formato = config.get('formato_salida', 'srt')
        if formato == 'video':
            ruta_salida = os.path.join(carpeta, f'{titulo_safe}_subtitulado.mp4')
            if paso_actual_idx < indice_paso('done') or not os.path.exists(ruta_salida):
                emitir('renderizando', 90, 'Incrustando subtítulos en video...')
                try:
                    incrustar_subtitulos(ruta_video, ruta_srt, ruta_salida)
                    guardar({'stage': 'done', 'output_path': ruta_salida})
                    emitir('done', 100, 'Completado', output_path=ruta_salida)
                except Exception as e:
                    guardar({'stage': 'done', 'output_path': ruta_srt})
                    emitir('done', 100, f'ffmpeg falló, pero el .srt está listo: {e}', output_path=ruta_srt)
            else:
                emitir('done', 100, 'Completado', output_path=ruta_salida)
        else:
            if paso_actual_idx < indice_paso('done'):
                guardar({'stage': 'done', 'output_path': ruta_srt})
            emitir('done', 100, 'Completado', output_path=ruta_srt)

    except Exception as e:
        guardar({'stage': 'error', 'error': str(e)})
        emitir('error', 0, str(e))
