import os
import sys

nvidia_base = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'site-packages', 'nvidia')
for sub in ['cublas', 'cuda_nvrtc', 'cuda_runtime', 'cudnn', 'nccl']:
    dll_dir = os.path.join(nvidia_base, sub, 'bin')
    if os.path.isdir(dll_dir):
        os.add_dll_directory(dll_dir)

from faster_whisper import WhisperModel

def transcribir_audio(ruta_audio, modelo='medium', dispositivo='cpu', callback_progreso=None):
    if callback_progreso:
        callback_progreso(0, f'Cargando modelo {modelo}...')

    compute_type = 'float16' if dispositivo == 'cuda' else 'int8'
    model = WhisperModel(modelo, device=dispositivo, compute_type=compute_type)

    if callback_progreso:
        callback_progreso(10, 'Transcribiendo audio...')

    segments_iter, info = model.transcribe(ruta_audio, beam_size=5)

    segmentos = []
    total_duration = info.duration

    for segment in segments_iter:
        segmentos.append({
            'inicio': segment.start,
            'fin': segment.end,
            'texto': segment.text.strip()
        })

        if callback_progreso and total_duration > 0:
            progreso = min(90, int(segment.end / total_duration * 90))
            callback_progreso(progreso, f'Transcribiendo... {segment.end:.1f}s / {total_duration:.1f}s')

    if callback_progreso:
        callback_progreso(100, f'Transcripción completa: {len(segmentos)} segmentos')

    return segmentos, info.language
