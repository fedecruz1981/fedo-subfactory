import time
from deep_translator import GoogleTranslator
from .base import TraductorBase

class TraductorGoogle(TraductorBase):
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='es')
        self.max_reintentos = 3

    @property
    def nombre(self):
        return 'Google Translate'

    def traducir_lote(self, segmentos, contexto_previo=''):
        if not segmentos:
            return [], ''

        textos = [s['texto'] for s in segmentos]
        texto_completo = '\n'.join(textos)

        if contexto_previo:
            texto_a_traducir = (
                f'Contexto previo (para mantener coherencia, no traducir esto):\n'
                f'"{contexto_previo}"\n\n'
                f'Texto a traducir:\n{texto_completo}'
            )
        else:
            texto_a_traducir = texto_completo

        traducido = texto_a_traducir
        for intento in range(self.max_reintentos):
            try:
                traducido = self.translator.translate(texto_a_traducir)
                break
            except Exception:
                if intento < self.max_reintentos - 1:
                    time.sleep(1 + intento)
                continue

        if contexto_previo and '\n\nTexto a traducir:\n' in traducido:
            traducido = traducido.split('\n\nTexto a traducir:\n')[-1]

        lineas_traducidas = traducido.strip().split('\n')

        resultado = []
        for i, seg in enumerate(segmentos):
            texto_seg = lineas_traducidas[i] if i < len(lineas_traducidas) else seg['texto']
            resultado.append({
                'inicio': seg['inicio'],
                'fin': seg['fin'],
                'texto': texto_seg
            })

        contexto_salida = resultado[-1]['texto'] if resultado else ''
        return resultado, contexto_salida
