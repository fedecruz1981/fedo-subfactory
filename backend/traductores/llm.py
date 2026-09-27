import os
import time
from .base import TraductorBase

PROVEEDORES = {
    'openai': {
        'base_url': 'https://api.openai.com/v1',
        'modelos': {
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-4o': 'GPT-4o',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo',
        }
    },
    'groq': {
        'base_url': 'https://api.groq.com/openai/v1',
        'modelos': {
            'llama-3.3-70b-versatile': 'Llama 3.3 70B',
            'llama-3.1-8b-instant': 'Llama 3.1 8B (rápido)',
            'mixtral-8x7b-32768': 'Mixtral 8x7B',
            'gemma2-9b-it': 'Gemma 2 9B',
        }
    },
    'gemini': {
        'base_url': 'https://generativelanguage.googleapis.com/v1beta/openai',
        'modelos': {
            'gemini-3.6-flash': 'Gemini 3.6 Flash',
            'gemini-3.5-flash': 'Gemini 3.5 Flash',
            'gemini-3.7-flash': 'Gemini 3.7 Flash',
        }
    },
}

class TraductorLLM(TraductorBase):
    def __init__(self, api_key=None, model='gpt-4o-mini', proveedor='openai', base_url=None):
        self.api_key = api_key or ''
        self.proveedor = proveedor or 'openai'
        self.model = model

        if not self.api_key:
            self.api_key = os.environ.get('GEMINI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')

        if base_url:
            self.base_url = base_url
        elif self.proveedor in PROVEEDORES:
            self.base_url = PROVEEDORES[self.proveedor]['base_url']
        else:
            self.base_url = 'https://api.openai.com/v1'

        self.max_reintentos = 5

    @property
    def nombre(self):
        proveedor_info = PROVEEDORES.get(self.proveedor, {})
        modelos = proveedor_info.get('modelos', {})
        nombre_modelo = modelos.get(self.model, self.model)
        return f'LLM ({nombre_modelo})'

    def _llamar_api(self, messages):
        import httpx

        url = f'{self.base_url}/chat/completions'
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        payload = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.3
        }

        for intento in range(self.max_reintentos):
            try:
                resp = httpx.post(url, json=payload, headers=headers, timeout=60)
                if resp.status_code == 429:
                    if intento < self.max_reintentos - 1:
                        wait = 30 * (intento + 1)
                        time.sleep(wait)
                        continue
                    else:
                        raise Exception('Rate limit (429) tras varios reintentos. Esperá unos minutos y volvé a intentar.')
                resp.raise_for_status()
                data = resp.json()
                return data['choices'][0]['message']['content']
            except Exception as e:
                if '429' in str(e):
                    raise e
                if intento < self.max_reintentos - 1:
                    time.sleep(5 * (intento + 1))
                else:
                    raise e

    def traducir_lote(self, segmentos, contexto_previo=''):
        if not segmentos:
            return [], ''

        textos = []
        for i, seg in enumerate(segmentos, 1):
            textos.append(f'[{i}] {seg["texto"]}')

        bloques_texto = '\n'.join(textos)

        system_prompt = (
            'Eres un traductor profesional de subtítulos de video al español. '
            'Traduce los siguientes segmentos de subtítulos manteniendo naturalidad, '
            'coherencia entre segmentos y el tono del original. '
            'IMPORTANTE: responde SOLO con las traducciones, una por línea, '
            'numeradas como [1], [2], etc. Sin explicaciones adicionales.'
        )

        user_parts = []
        if contexto_previo:
            user_parts.append(
                f'Contexto del fragmento anterior (para mantener coherencia):\n'
                f'"{contexto_previo}"'
            )

        user_parts.append(f'Textos a traducir:\n{bloques_texto}')
        user_message = '\n\n'.join(user_parts)

        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]

        respuesta = self._llamar_api(messages)

        lineas = respuesta.strip().split('\n')
        traducciones_map = {}
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            if linea.startswith('['):
                try:
                    idx_end = linea.index(']')
                    idx = int(linea[1:idx_end])
                    texto = linea[idx_end + 1:].strip()
                    traducciones_map[idx] = texto
                except (ValueError, IndexError):
                    continue

        resultado = []
        for i, seg in enumerate(segmentos, 1):
            texto_traducido = traducciones_map.get(i, seg['texto'])
            resultado.append({
                'inicio': seg['inicio'],
                'fin': seg['fin'],
                'texto': texto_traducido
            })

        contexto_salida = resultado[-1]['texto'] if resultado else ''
        return resultado, contexto_salida
