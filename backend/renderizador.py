import subprocess
import os

def segundos_a_timestamp(segundos):
    horas = int(segundos // 3600)
    minutos = int((segundos % 3600) // 60)
    segs = segundos % 60
    return f'{horas:02d}:{minutos:02d}:{segs:06.3f}'.replace('.', ',')

def escribir_srt(segmentos, ruta_salida):
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segmentos, 1):
            inicio = segundos_a_timestamp(seg['inicio'])
            fin = segundos_a_timestamp(seg['fin'])
            f.write(f'{i}\n')
            f.write(f'{inicio} --> {fin}\n')
            f.write(f'{seg["texto"]}\n\n')

def incrustar_subtitulos(ruta_video, ruta_srt, ruta_salida, callback_progreso=None):
    if callback_progreso:
        callback_progreso(0, 'Incrustando subtítulos...')

    comando = [
        'ffmpeg', '-y',
        '-i', ruta_video,
        '-vf', f'subtitles={ruta_srt}:force_style="FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2"',
        '-c:a', 'copy',
        ruta_salida
    ]

    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=600)
        if resultado.returncode != 0:
            raise RuntimeError(f'Error ffmpeg: {resultado.stderr}')

        if callback_progreso:
            callback_progreso(100, 'Subtítulos incrustados')
        return True
    except subprocess.TimeoutExpired:
        raise RuntimeError('ffmpeg tardó demasiado (>10 minutos)')
    except FileNotFoundError:
        raise RuntimeError('ffmpeg no encontrado. Instálalo y asegúrate de que esté en el PATH')
