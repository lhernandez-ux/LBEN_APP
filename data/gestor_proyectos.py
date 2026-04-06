"""
data/gestor_proyectos.py
========================
Guarda y carga proyectos en una carpeta local (.lben_proyectos/).
Cada proyecto es un JSON con la configuración + ruta del Excel base.
Los datos (DataFrames) NO se guardan en el JSON — se releen del Excel.
"""

import json
import os
from datetime import datetime
from dataclasses import asdict
from typing import List, Optional

# Carpeta de proyectos junto al ejecutable
PROYECTOS_DIR = os.path.join(os.path.expanduser("~"), ".lben_proyectos")


def _asegurar_dir():
    os.makedirs(PROYECTOS_DIR, exist_ok=True)


def _ruta(nombre: str) -> str:
    return os.path.join(PROYECTOS_DIR, f"{nombre}.json")


def guardar_proyecto(sesion, ruta_excel: str):
    """Guarda la configuración de la sesión actual como proyecto JSON."""
    _asegurar_dir()
    datos = {
        "nombre_proyecto":      sesion.nombre_proyecto,
        "unidad_energia":       sesion.unidad_energia,
        "zona_climatica":       sesion.zona_climatica,
        "modelo_id":            sesion.modelo_id,
        "col_consumo":          sesion.col_consumo,
        "vars_independientes":  sesion.vars_independientes,
        "nivel_confianza":      sesion.nivel_confianza,
        "periodo_base":    sesion.periodo_base,
        "periodo_reporte":      sesion.periodo_reporte,
        "tiene_reporte":        sesion.tiene_reporte,
        "frecuencia":           getattr(sesion, "frecuencia", "mensual"),
        "ruta_excel":           ruta_excel,
        "guardado_en":          datetime.now().isoformat(timespec="seconds"),
    }
    nombre_archivo = _nombre_seguro(sesion.nombre_proyecto)
    with open(_ruta(nombre_archivo), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return nombre_archivo


def listar_proyectos() -> List[dict]:
    """Devuelve lista de proyectos guardados, ordenados por fecha desc."""
    _asegurar_dir()
    proyectos = []
    for fname in os.listdir(PROYECTOS_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(PROYECTOS_DIR, fname), encoding="utf-8") as f:
                d = json.load(f)
            d["_archivo"] = fname
            proyectos.append(d)
        except Exception:
            pass
    proyectos.sort(key=lambda x: x.get("guardado_en", ""), reverse=True)
    return proyectos


def cargar_proyecto(nombre_archivo: str) -> Optional[dict]:
    """Carga un proyecto por nombre de archivo .json."""
    path = os.path.join(PROYECTOS_DIR, nombre_archivo)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def actualizar_ruta_excel(nombre_archivo: str, nueva_ruta: str):
    """Actualiza la ruta del Excel en el proyecto guardado."""
    d = cargar_proyecto(nombre_archivo)
    if d:
        d["ruta_excel"] = nueva_ruta
        path = os.path.join(PROYECTOS_DIR, nombre_archivo)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)


def _nombre_seguro(nombre: str) -> str:
    """Convierte un nombre de proyecto a nombre de archivo válido."""
    import re
    s = nombre.strip().lower()
    s = re.sub(r"[^a-z0-9áéíóúñü\s_-]", "", s)
    s = re.sub(r"\s+", "_", s)
    s = s[:60]
    return s or "proyecto"


def actualizar_ruta_seguimiento(nombre_archivo: str, ruta_seguimiento: str):
    """Guarda la ruta del Excel de seguimiento (monitoreo acumulado) en el proyecto."""
    d = cargar_proyecto(nombre_archivo)
    if d:
        d["ruta_seguimiento"] = ruta_seguimiento
        path = os.path.join(PROYECTOS_DIR, nombre_archivo)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)


def eliminar_proyecto(nombre_archivo: str) -> bool:
    """Elimina el JSON del proyecto. Devuelve True si se eliminó correctamente."""
    path = os.path.join(PROYECTOS_DIR, nombre_archivo)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False