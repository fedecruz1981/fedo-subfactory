import sys
import json
from backend.pipeline import ejecutar_pipeline

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m backend.cli <url> [modelo] [dispositivo] [motor_traduccion]")
        print("Ejemplo: python -m backend.cli https://www.youtube.com/watch?v=xxx medium cpu nllb")
        sys.exit(1)

    url = sys.argv[1]
    modelo = sys.argv[2] if len(sys.argv) > 2 else 'base'
    dispositivo = sys.argv[3] if len(sys.argv) > 3 else 'cpu'
    motor = sys.argv[4] if len(sys.argv) > 4 else 'nllb'

    config = {
        'modelo_whisper': modelo,
        'dispositivo': dispositivo,
        'motor_traduccion': motor,
        'formato_salida': 'srt',
        'carpeta_destino': ''
    }

    def on_evento(evt):
        stage = evt.get('stage', '?')
        msg = evt.get('message', '')
        prog = evt.get('progress', 0)
        print(f"[{stage}] {prog}% - {msg}")

    job_id = 'test_cli'
    print(f"URL: {url}")
    print(f"Modelo: {modelo} | Dispositivo: {dispositivo} | Traductor: {motor}")
    print("---")
    ejecutar_pipeline(job_id, url, config, callback=on_evento)
    print("---")
    print("Listo!")

if __name__ == '__main__':
    main()
