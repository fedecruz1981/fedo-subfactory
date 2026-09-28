import os
import re
import json
import shutil
import tempfile

CARPETA_BASE = os.path.join(tempfile.gettempdir(), 'subfactory')

def sanitizar_nombre(nombre):
    if not nombre:
        return 'video'
    nombre = re.sub(r'[<>:"/\\|?*]', '_', nombre)
    nombre = re.sub(r'\s+', ' ', nombre).strip()
    return nombre[:200] if nombre else 'video'

def crear_carpeta_job(job_id):
    carpeta = os.path.join(CARPETA_BASE, job_id)
    os.makedirs(carpeta, exist_ok=True)
    return carpeta

def ruta_temporal(job_id, nombre):
    carpeta = crear_carpeta_job(job_id)
    return os.path.join(carpeta, nombre)

def limpiar_job(job_id):
    carpeta = os.path.join(CARPETA_BASE, job_id)
    if os.path.exists(carpeta):
        shutil.rmtree(carpeta)

def listar_jobs_temporales():
    if not os.path.exists(CARPETA_BASE):
        return []
    return os.listdir(CARPETA_BASE)

def guardar_estado(job_id, estado):
    crear_carpeta_job(job_id)
    ruta = os.path.join(CARPETA_BASE, job_id, 'estado.json')
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)

def cargar_estado(job_id):
    ruta = os.path.join(CARPETA_BASE, job_id, 'estado.json')
    if not os.path.exists(ruta):
        return None
    with open(ruta, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return None

def listar_jobs_pendientes():
    jobs = []
    if not os.path.exists(CARPETA_BASE):
        return jobs
    for job_id in os.listdir(CARPETA_BASE):
        estado = cargar_estado(job_id)
        if estado and estado.get('stage') not in ('done', 'cancelado'):
            jobs.append(estado)
    return jobs
