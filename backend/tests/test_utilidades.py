"""
Tests de backend/utilidades.py de Fábrica de Subtítulos.

No tocan disco real: se monkeypatchea CARPETA_BASE a un tmp_path.
"""

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import utilidades as u  # noqa: E402


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    """Redirige CARPETA_BASE a un directorio temporal limpio por test."""
    carpeta = tmp_path / 'subfactory'
    monkeypatch.setattr(u, 'CARPETA_BASE', str(carpeta))
    return carpeta


# ---------------------------------------------------------------------------
# sanitizar_nombre
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'entrada,esperado',
    [
        ('video normal', 'video normal'),
        ('con/barra', 'con_barra'),
        ('con\\barra', 'con_barra'),
        ('punto:dos', 'punto_dos'),
        ('a<b>c', 'a_b_c'),
        ('con*star?pregunta', 'con_star_pregunta'),
        ('barra|vertical', 'barra_vertical'),
        ('comillas"dobles', 'comillas_dobles'),
    ],
)
def test_sanitizar_nombre_cambia_caracteres_invalidos(entrada, esperado):
    assert u.sanitizar_nombre(entrada) == esperado


def test_sanitizar_nombre_colapsa_espacios():
    assert u.sanitizar_nombre('mucho    espacio   aqui') == 'mucho espacio aqui'


def test_sanitizar_nombre_quita_espacios_extremos():
    assert u.sanitizar_nombre('  borde  ') == 'borde'


def test_sanitizar_nombre_limita_a_200_caracteres():
    assert len(u.sanitizar_nombre('a' * 500)) == 200


@pytest.mark.parametrize('entrada', ['', '   ', None])
def test_sanitizar_nombre_usa_video_por_defecto(entrada):
    assert u.sanitizar_nombre(entrada) == 'video'


def test_sanitizar_nombre_preserva_acentos():
    assert u.sanitizar_nombre('canción de año') == 'canción de año'


# ---------------------------------------------------------------------------
# crear_carpeta_job / ruta_temporal
# ---------------------------------------------------------------------------


def test_crear_carpeta_job_crea_directorio(base_temporal):
    carpeta = u.crear_carpeta_job('job-1')
    assert os.path.isdir(carpeta)
    assert carpeta == os.path.join(str(base_temporal), 'job-1')


def test_crear_carpeta_job_es_idempotente(base_temporal):
    primera = u.crear_carpeta_job('job-1')
    segunda = u.crear_carpeta_job('job-1')
    assert primera == segunda
    assert os.path.isdir(segunda)


def test_crear_carpeta_job_aisla_jobs(base_temporal):
    a = u.crear_carpeta_job('job-a')
    b = u.crear_carpeta_job('job-b')
    assert a != b
    assert os.path.isdir(a) and os.path.isdir(b)


def test_ruta_temporal_devuelve_ruta_dentro_del_job(base_temporal):
    ruta = u.ruta_temporal('job-1', 'audio.wav')
    assert ruta == os.path.join(str(base_temporal), 'job-1', 'audio.wav')
    assert os.path.isdir(os.path.dirname(ruta))


# ---------------------------------------------------------------------------
# limpiar_job / listar_jobs_temporales
# ---------------------------------------------------------------------------


def test_limpiar_job_borra_la_carpeta(base_temporal):
    u.crear_carpeta_job('job-1')
    u.limpiar_job('job-1')
    assert not os.path.exists(os.path.join(str(base_temporal), 'job-1'))


def test_limpiar_job_inexistente_no_revienta(base_temporal):
    u.limpiar_job('no-existe')  # no debe levantar


def test_limpiar_job_no_toca_otros(base_temporal):
    u.crear_carpeta_job('job-1')
    u.crear_carpeta_job('job-2')
    u.limpiar_job('job-1')
    assert os.path.isdir(os.path.join(str(base_temporal), 'job-2'))


def test_listar_jobs_sin_carpeta_base_devuelve_lista_vacia(base_temporal):
    assert u.listar_jobs_temporales() == []


def test_listar_jobs_devuelve_carpetas(base_temporal):
    u.crear_carpeta_job('job-1')
    u.crear_carpeta_job('job-2')
    assert sorted(u.listar_jobs_temporales()) == ['job-1', 'job-2']


# ---------------------------------------------------------------------------
# guardar_estado / cargar_estado
# ---------------------------------------------------------------------------


def test_guardar_y_cargar_estado_ida_y_vuelta(base_temporal):
    u.crear_carpeta_job('job-1')
    estado = {'stage': 'traduccion', 'progreso': 42, 'url': 'https://x'}
    u.guardar_estado('job-1', estado)
    assert u.cargar_estado('job-1') == estado


def test_cargar_estado_inexistente_devuelve_none(base_temporal):
    assert u.cargar_estado('no-existe') is None


def test_cargar_estado_de_archivo_faltante_devuelve_none(base_temporal):
    u.crear_carpeta_job('job-1')  # carpeta existe, estado.json no
    assert u.cargar_estado('job-1') is None


def test_guardar_estado_sobrescribe(base_temporal):
    u.crear_carpeta_job('job-1')
    u.guardar_estado('job-1', {'stage': 'descarga'})
    u.guardar_estado('job-1', {'stage': 'transcripcion'})
    assert u.cargar_estado('job-1') == {'stage': 'transcripcion'}


def test_guardar_estado_preserva_acentos(base_temporal):
    u.crear_carpeta_job('job-1')
    u.guardar_estado('job-1', {'titulo': 'canción de año — ñ'})
    assert u.cargar_estado('job-1')['titulo'] == 'canción de año — ñ'


def test_guardar_estado_crea_el_json(base_temporal):
    u.guardar_estado('job-2', {'stage': 'descarga'})
    ruta = os.path.join(str(base_temporal), 'job-2', 'estado.json')
    assert os.path.isfile(ruta)


# ---------------------------------------------------------------------------
# listar_jobs_pendientes
# ---------------------------------------------------------------------------


def test_listar_pendientes_sin_base_devuelve_lista(base_temporal):
    assert u.listar_jobs_pendientes() == []


def test_listar_pendientes_excluye_terminados_y_cancelados(base_temporal):
    u.guardar_estado('job-done', {'stage': 'done'})
    u.guardar_estado('job-cancel', {'stage': 'cancelado'})
    u.guardar_estado('job-activo', {'stage': 'traduccion'})

    pendientes = u.listar_jobs_pendientes()
    assert len(pendientes) == 1
    assert pendientes[0]['stage'] == 'traduccion'


@pytest.mark.parametrize('stage', ['descarga', 'transcripcion', 'traduccion', 'render'])
def test_listar_pendientes_incluye_etapas_intermedias(base_temporal, stage):
    u.guardar_estado('job-1', {'stage': stage})
    assert len(u.listar_jobs_pendientes()) == 1


def test_listar_pendientes_ignora_carpetas_sin_estado(base_temporal):
    u.crear_carpeta_job('job-sin-estado')
    assert u.listar_jobs_pendientes() == []


def test_listar_pendientes_ignora_json_invalido(base_temporal):
    carpeta = u.crear_carpeta_job('job-roto')
    with open(os.path.join(carpeta, 'estado.json'), 'w', encoding='utf-8') as f:
        f.write('{no es json')
    u.guardar_estado('job-ok', {'stage': 'render'})

    pendientes = u.listar_jobs_pendientes()
    assert [p['stage'] for p in pendientes] == ['render']
