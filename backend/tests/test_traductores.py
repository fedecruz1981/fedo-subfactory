"""
Tests de los traductores de Fábrica de Subtítulos.

Nada sale a la red: httpx y deep_translator se monkeypatchean, y el modelo de
NLLB se reemplaza por un doble. Se verifica el parseo de la respuesta, el
mapeo por indice, los reintentos y el manejo de contexto.
"""

import sys
import types
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from traductores.base import TraductorBase  # noqa: E402


def _segmentos(*textos):
    return [{'inicio': i * 2.0, 'fin': i * 2.0 + 2.0, 'texto': t} for i, t in enumerate(textos)]


# ===========================================================================
# Base
# ===========================================================================


def test_base_es_abstracta():
    with pytest.raises(TypeError):
        TraductorBase()


def test_subclase_incompleta_no_se_puede_instantiar():
    class Incompleto(TraductorBase):
        def traducir_lote(self, segmentos, contexto_previo=''):
            return [], ''

    with pytest.raises(TypeError):
        Incompleto()


def test_subclase_completa_se_puede_instantiar():
    class Completo(TraductorBase):
        def traducir_lote(self, segmentos, contexto_previo=''):
            return list(segmentos), 'ctx'

        @property
        def nombre(self):
            return 'Completo'

    t = Completo()
    assert t.nombre == 'Completo'
    assert t.traducir_lote([]) == ([], 'ctx')


# ===========================================================================
# LLM
# ===========================================================================


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')

    def json(self):
        return self._payload


def _llm_modulo(monkeypatch, respuestas, con_httpx=True):
    """Registra un doble de httpx que devuelve `respuestas` en orden."""
    llamadas = []

    def post(url, json=None, headers=None, timeout=None):
        llamadas.append({'url': url, 'json': json, 'headers': headers})
        if not respuestas:
            raise AssertionError('se llamo httpx.post mas veces de lo esperado')
        return respuestas.pop(0)

    mod = types.ModuleType('httpx')
    mod.post = post
    mod.__dict__['calls'] = llamadas
    if con_httpx:
        monkeypatch.setitem(sys.modules, 'httpx', mod)
    return llamadas


@pytest.fixture
def sin_sleep(monkeypatch):
    """Evita que los reintentos_REALmente esperen."""
    slept = []
    import time as time_mod

    monkeypatch.setattr(time_mod, 'sleep', lambda s: slept.append(s))
    return slept


def _traductor_llm(monkeypatch, **kwargs):
    from traductores.llm import TraductorLLM

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    return TraductorLLM(**kwargs)


def test_llm_nombre_usa_el_nombre_amigable_del_modelo(monkeypatch):
    t = _traductor_llm(monkeypatch, api_key='k', model='gpt-4o-mini', proveedor='openai')
    assert t.nombre == 'LLM (GPT-4o Mini)'


def test_llm_nombre_de_modelo_desconocido_usa_el_id(monkeypatch):
    t = _traductor_llm(monkeypatch, api_key='k', model='mi-modelo', proveedor='openai')
    assert t.nombre == 'LLM (mi-modelo)'


def test_llm_base_url_segun_proveedor(monkeypatch):
    from traductores.llm import PROVEEDORES

    for proveedor, info in PROVEEDORES.items():
        t = _traductor_llm(monkeypatch, api_key='k', proveedor=proveedor)
        assert t.base_url == info['base_url']


def test_llm_proveedor_desconocido_cae_a_openai(monkeypatch):
    t = _traductor_llm(monkeypatch, api_key='k', proveedor='inventado')
    assert t.base_url == 'https://api.openai.com/v1'


def test_llm_base_url_explicita_manda(monkeypatch):
    t = _traductor_llm(monkeypatch, api_key='k', base_url='https://local.test/v1')
    assert t.base_url == 'https://local.test/v1'


def test_llm_toma_la_api_key_del_entorno(monkeypatch):
    from traductores.llm import TraductorLLM

    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'desde-entorno')
    t = TraductorLLM()
    assert t.api_key == 'desde-entorno'


def test_llm_sin_api_key_queda_vacia(monkeypatch):
    t = _traductor_llm(monkeypatch)
    assert t.api_key == ''


def test_llm_lote_vacio_no_llama_a_la_api(monkeypatch):
    llamadas = _llm_modulo(monkeypatch, [])
    t = _traductor_llm(monkeypatch, api_key='k')

    assert t.traducir_lote([]) == ([], '')
    assert llamadas == []


def test_llm_parsea_respuesta_numerada(monkeypatch):
    respuesta = _FakeResponse(payload={'choices': [{'message': {'content': '[1] Hola\n[2] Adios'}}]})
    _llm_modulo(monkeypatch, [respuesta])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, contexto = t.traducir_lote(_segmentos('Hello', 'Goodbye'))

    assert [s['texto'] for s in resultado] == ['Hola', 'Adios']
    assert resultado[0]['inicio'] == 0.0
    assert resultado[1]['fin'] == 4.0
    assert contexto == 'Adios'


def test_llm_conserva_timestamps_originales(monkeypatch):
    respuesta = _FakeResponse(payload={'choices': [{'message': {'content': '[1] A\n[2] B\n[3] C'}}]})
    _llm_modulo(monkeypatch, [respuesta])
    t = _traductor_llm(monkeypatch, api_key='k')

    segs = [
        {'inicio': 1.5, 'fin': 3.25, 'texto': 'a'},
        {'inicio': 3.25, 'fin': 9.75, 'texto': 'b'},
        {'inicio': 9.75, 'fin': 12.0, 'texto': 'c'},
    ]
    resultado, _ = t.traducir_lote(segs)

    assert [(s['inicio'], s['fin']) for s in resultado] == [(1.5, 3.25), (3.25, 9.75), (9.75, 12.0)]


def test_llm_indice_faltante_cae_al_texto_original(monkeypatch):
    """Si el modelo omite el [2], ese segmento conserva el original."""
    respuesta = _FakeResponse(payload={'choices': [{'message': {'content': '[1] Uno\n[3] Tres'}}]})
    _llm_modulo(monkeypatch, [respuesta])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, _ = t.traducir_lote(_segmentos('One', 'Two', 'Three'))
    assert [s['texto'] for s in resultado] == ['Uno', 'Two', 'Tres']


def test_llm_ignora_lineas_sin_numeracion(monkeypatch):
    respuesta = _FakeResponse(
        payload={'choices': [{'message': {'content': 'Disculpa:\n\n[1] Uno\ntexto suelto\n[2] Dos'}}]}
    )
    _llm_modulo(monkeypatch, [respuesta])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, _ = t.traducir_lote(_segmentos('One', 'Two'))
    assert [s['texto'] for s in resultado] == ['Uno', 'Dos']


def test_llm_envia_el_contexto_previo_en_el_prompt(monkeypatch):
    llamadas = _llm_modulo(
        monkeypatch,
        [_FakeResponse(payload={'choices': [{'message': {'content': '[1] Uno'}}]})],
    )
    t = _traductor_llm(monkeypatch, api_key='k')

    t.traducir_lote(_segmentos('One'), contexto_previo='frase anterior')

    prompt_usuario = llamadas[0]['json']['messages'][1]['content']
    assert 'frase anterior' in prompt_usuario


def test_llm_numerera_los_segmentos_en_el_prompt(monkeypatch):
    llamadas = _llm_modulo(
        monkeypatch,
        [_FakeResponse(payload={'choices': [{'message': {'content': '[1] a\n[2] b'}}]})],
    )
    t = _traductor_llm(monkeypatch, api_key='k')

    t.traducir_lote(_segmentos('Hola', 'Mundo'))

    prompt = llamadas[0]['json']['messages'][1]['content']
    assert '[1] Hola' in prompt
    assert '[2] Mundo' in prompt


def test_llm_envia_el_modelo_y_la_api_key(monkeypatch):
    llamadas = _llm_modulo(
        monkeypatch,
        [_FakeResponse(payload={'choices': [{'message': {'content': '[1] a'}}]})],
    )
    t = _traductor_llm(monkeypatch, api_key='secreta', model='gpt-4o')

    t.traducir_lote(_segmentos('x'))

    assert llamadas[0]['json']['model'] == 'gpt-4o'
    assert llamadas[0]['headers']['Authorization'] == 'Bearer secreta'
    assert llamadas[0]['url'].endswith('/chat/completions')


def test_llm_reintenta_ante_error_de_red(monkeypatch, sin_sleep):
    ok = _FakeResponse(payload={'choices': [{'message': {'content': '[1] Uno'}}]})
    _llm_modulo(monkeypatch, [_FakeResponse(status_code=500), ok])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, _ = t.traducir_lote(_segmentos('One'))
    assert resultado[0]['texto'] == 'Uno'
    assert sin_sleep, 'deberia haber esperado entre reintentos'


def test_llm_reintenta_429_con_espera_progresiva(monkeypatch, sin_sleep):
    """Un 429 es transitorio: reintenta hasta max_reintentos con espera creciente."""
    _llm_modulo(monkeypatch, [_FakeResponse(status_code=429) for _ in range(5)])
    t = _traductor_llm(monkeypatch, api_key='k')

    with pytest.raises(Exception, match='429'):
        t.traducir_lote(_segmentos('One'))
    # 5 intentos, esperando 30/60/90/120 entre ellos
    assert len(sin_sleep) == 4
    assert sin_sleep == [30, 60, 90, 120]


def test_llm_429_se_recupera_si_el_reintento_funciona(monkeypatch, sin_sleep):
    ok = _FakeResponse(payload={'choices': [{'message': {'content': '[1] Uno'}}]})
    _llm_modulo(monkeypatch, [_FakeResponse(status_code=429), ok])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, _ = t.traducir_lote(_segmentos('One'))
    assert resultado[0]['texto'] == 'Uno'
    assert sin_sleep == [30]


def test_llm_agota_reintentos_y_propaga(monkeypatch, sin_sleep):
    _llm_modulo(monkeypatch, [_FakeResponse(status_code=500) for _ in range(5)])
    t = _traductor_llm(monkeypatch, api_key='k')

    with pytest.raises(Exception, match='500'):
        t.traducir_lote(_segmentos('One'))
    assert len(sin_sleep) == 4


def test_llm_respuesta_vacia_devuelve_textos_originales(monkeypatch):
    _llm_modulo(monkeypatch, [_FakeResponse(payload={'choices': [{'message': {'content': ''}}]})])
    t = _traductor_llm(monkeypatch, api_key='k')

    resultado, contexto = t.traducir_lote(_segmentos('One', 'Two'))
    assert [s['texto'] for s in resultado] == ['One', 'Two']
    assert contexto == 'Two'


# ===========================================================================
# Google
# ===========================================================================


class _FakeGoogleTranslator:
    """Doble de deep_translator.GoogleTranslator."""

    respuesta = ''
    error = None
    llamadas = []

    def __init__(self, source='auto', target='es'):
        self.source = source
        self.target = target

    def translate(self, texto):
        type(self).llamadas.append(texto)
        if type(self).error is not None:
            err = type(self).error
            type(self).error = None  # solo falla el primer intento
            raise err
        return type(self).respuesta


@pytest.fixture
def google(monkeypatch):
    import deep_translator

    _FakeGoogleTranslator.llamadas = []
    _FakeGoogleTranslator.respuesta = ''
    _FakeGoogleTranslator.error = None
    monkeypatch.setattr(deep_translator, 'GoogleTranslator', _FakeGoogleTranslator)
    return _FakeGoogleTranslator


def test_google_nombre(google):
    from traductores.google import TraductorGoogle

    assert TraductorGoogle().nombre == 'Google Translate'


def test_google_lote_vacio_no_traduce(google):
    from traductores.google import TraductorGoogle

    assert TraductorGoogle().traducir_lote([]) == ([], '')
    assert google.llamadas == []


def test_google_mapea_lineas_por_orden(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'Hola\nAdios\nHasta luego'
    resultado, contexto = TraductorGoogle().traducir_lote(_segmentos('Hello', 'Goodbye', 'See you'))

    assert [s['texto'] for s in resultado] == ['Hola', 'Adios', 'Hasta luego']
    assert contexto == 'Hasta luego'


def test_google_conserva_timestamps(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'Uno\nDos'
    resultado, _ = TraductorGoogle().traducir_lote(
        [{'inicio': 2.0, 'fin': 4.0, 'texto': 'a'}, {'inicio': 4.0, 'fin': 5.5, 'texto': 'b'}]
    )
    assert [s['inicio'] for s in resultado] == [2.0, 4.0]
    assert [s['fin'] for s in resultado] == [4.0, 5.5]


def test_google_respuesta_mas_corta_usa_original_faltante(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'Solo uno'
    resultado, _ = TraductorGoogle().traducir_lote(_segmentos('One', 'Two', 'Three'))
    assert [s['texto'] for s in resultado] == ['Solo uno', 'Two', 'Three']


def test_google_reintenta_ante_error(google, monkeypatch):
    import time as time_mod

    monkeypatch.setattr(time_mod, 'sleep', lambda s: None)
    from traductores.google import TraductorGoogle

    google.error = RuntimeError('fiableTemporal')
    google.respuesta = 'Hola'
    resultado, _ = TraductorGoogle().traducir_lote(_segmentos('Hello'))
    assert resultado[0]['texto'] == 'Hola'
    assert len(google.llamadas) == 2


def test_google_envia_el_contexto_como_bloque(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'Hola'
    TraductorGoogle().traducir_lote(_segmentos('Hello'), contexto_previo='previo')

    enviado = google.llamadas[0]
    assert 'Contexto previo' in enviado
    assert 'previo' in enviado


def test_google_recorta_el_bloque_de_contexto_de_la_respuesta(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'contexto traducido\n\nTexto a traducir:\nHola'
    resultado, _ = TraductorGoogle().traducir_lote(_segmentos('Hello'), contexto_previo='previo')
    assert resultado[0]['texto'] == 'Hola'


def test_google_sin_contexto_no_recorta(google):
    from traductores.google import TraductorGoogle

    google.respuesta = 'Hola\nAdios'
    resultado, _ = TraductorGoogle().traducir_lote(_segmentos('Hello', 'Goodbye'))
    assert [s['texto'] for s in resultado] == ['Hola', 'Adios']


# ===========================================================================
# NLLB
# ===========================================================================


class _FakeModel:
    """Doble de ctranslate2.TranslationModel."""

    def __init__(self, salida=None):
        self.salida = salida or []
        self.llamadas = []

    def translate_batch(self, textos, src_lang=None, tgt_lang=None, beam_size=None):
        self.llamadas.append({'textos': list(textos), 'src': src_lang, 'tgt': tgt_lang})
        if self.salida:
            return self.salida
        return [[f'trad_{t}'] for t in textos]


@pytest.fixture
def nllb(monkeypatch):
    """Pre-inyecta el modelo para que no se cargue ctranslate2 real."""
    from traductores.nllb import TraductorNLLB

    t = TraductorNLLB()
    modelo = _FakeModel()
    t._modelo = modelo
    t.MODELO = modelo
    return t


def test_nllb_nombre(nllb):
    assert nllb.nombre == 'NLLB-200'


def test_nllb_lote_vacio_no_traduce(nllb):
    assert nllb.traducir_lote([]) == ([], '')
    assert nllb.MODELO.llamadas == []


def test_nllb_traduce_con_idiomas_fijos(nllb):
    nllb.MODELO.salida = [['Hola'], ['Adios']]
    resultado, contexto = nllb.traducir_lote(_segmentos('Hello', 'Goodbye'))

    assert [s['texto'] for s in resultado] == ['Hola', 'Adios']
    assert contexto == 'Adios'
    llamada = nllb.MODELO.llamadas[0]
    assert llamada['src'] == 'eng_Latn'
    assert llamada['tgt'] == 'spa_Latn'


def test_nllb_conserva_timestamps(nllb):
    nllb.MODELO.salida = [['A'], ['B']]
    resultado, _ = nllb.traducir_lote(
        [{'inicio': 0.0, 'fin': 1.0, 'texto': 'a'}, {'inicio': 1.0, 'fin': 7.5, 'texto': 'b'}]
    )
    assert [s['fin'] for s in resultado] == [1.0, 7.5]


def test_nllb_antepone_el_contexto_con_separador(nllb):
    nllb.traducir_lote(_segmentos('One'), contexto_previo='previo')
    enviado = nllb.MODELO.llamadas[0]['textos']
    assert enviado == ['previo ||| One']


def test_nllb_sin_contexto_no_antepone_nada(nllb):
    nllb.traducir_lote(_segmentos('One'))
    assert nllb.MODELO.llamadas[0]['textos'] == ['One']


def test_nllb_respuesta_mas_corta_usa_original(nllb):
    nllb.MODELO.salida = [['Solo una']]
    resultado, _ = nllb.traducir_lote(_segmentos('One', 'Two'))
    assert [s['texto'] for s in resultado] == ['Solo una', 'Two']


def test_nllb_carga_el_modelo_int8_de_facebook(monkeypatch):
    """Verifica el modelo y compute_type usados al cargar por primera vez.

    No se importa ctranslate2 real: se inyecta un doble en sys.modules para que
    el test corra en CI sin la dependencia nativa instalada.
    """
    from traductores.nllb import TraductorNLLB

    capturados = {}

    class FakeCT:
        @staticmethod
        def TranslationModel(ruta, compute_type=None):
            capturados['ruta'] = ruta
            capturados['compute_type'] = compute_type
            return _FakeModel()

    monkeypatch.setitem(sys.modules, 'ctranslate2', FakeCT)

    TraductorNLLB().traducir_lote(_segmentos('One'))

    assert capturados['ruta'] == 'facebook/nllb-200-distilled-600M'
    assert capturados['compute_type'] == 'int8'


def test_nllb_reutiliza_el_modelo_ya_cargado(nllb):
    nllb.traducir_lote(_segmentos('a'))
    nllb.traducir_lote(_segmentos('b'))
    assert len(nllb.MODELO.llamadas) == 2
