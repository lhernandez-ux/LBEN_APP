"""
core/ajuste_no_rutinario.py
============================
Ajuste No Rutinario (ANR) — Resolución UPME 16/2024

Columna esperada en el DataFrame de Histórico
---------------------------------------------
  Nombre aceptado (insensible a mayúsculas/tildes, con o sin guiones/espacios):
    "Ajuste_NR", "AjusteNR", "ajuste nr", "ANR", "Anomalia", "Anomalo",
    "Mes_Anomalo", "No_Rutinario", "no rutinario", etc.

  Valores que marcan un mes como ANÓMALO:
    Cualquier texto no vacío: "mantenimiento", "falla", "si", "1", "x", "true"

  Valores que marcan un mes como NORMAL (ignorados):
    Vacío / NaN / "0" / "no" / "normal" / "n" / "-" / "false"

Algoritmo (por año)
-------------------
  prom_normales = promedio consumos normales del año
  prom_anomalos = promedio consumos anómalos del año
  proporcion    = (prom_anomalos - prom_normales) / prom_normales
  valor_ajustado = valor_anomalo × (1 − proporcion)
  → Lleva el mes anómalo al nivel de los meses normales del mismo año.
"""

import re
import numpy as np
import pandas as pd
from typing import List, Tuple

# ── Patrón para detectar el nombre de la columna ANR ─────────────────────────
# Busca en cualquier parte del nombre (search, no match) para mayor tolerancia
_PATRON_COL_ANR = re.compile(
    r"ajuste.?nr|ajustenr|\banr\b|anomal[íi]a?|anomal[ou]|"
    r"mes.?anomal|no.?rutinario|rutinario",
    re.IGNORECASE,
)

# Valores que significan "mes normal"
_VALORES_NORMAL = {"", "0", "no", "normal", "n", "nan", "none", "-", "false", "x no"}


def _detectar_columna_anr(df: pd.DataFrame) -> str | None:
    """
    Devuelve el nombre exacto de la columna ANR si existe, o None.
    Usa búsqueda parcial para tolerar variantes del nombre.
    """
    for col in df.columns:
        nombre = _quitar_tildes(col.strip())
        if _PATRON_COL_ANR.search(nombre):
            return col
    return None


def _quitar_tildes(s: str) -> str:
    """Normaliza tildes para comparación robusta."""
    reemplazos = str.maketrans("áéíóúÁÉÍÓÚàèìòùäëïöü", "aeiouAEIOUaeiouaeiou")
    return s.translate(reemplazos)


def _es_anomalo(valor) -> bool:
    """
    True si el valor indica que el mes es anómalo.
    Cualquier texto no vacío y no perteneciente a _VALORES_NORMAL → anómalo.
    """
    if pd.isna(valor):
        return False
    s = str(valor).strip().lower()
    s_sin_tilde = _quitar_tildes(s)
    # Verificar contra set de valores "normales"
    return s_sin_tilde not in _VALORES_NORMAL and s not in _VALORES_NORMAL


def _extraer_año(fecha) -> int | None:
    """Extrae el año de una etiqueta de fecha (string, date, datetime)."""
    if hasattr(fecha, "year"):
        return int(fecha.year)
    s = str(fecha).strip()
    m = re.search(r"(\d{4})", s)
    return int(m.group(1)) if m else None


def aplicar_ajuste_no_rutinario(
    df: pd.DataFrame,
    col_consumo: str,
) -> Tuple[pd.DataFrame, List[dict], bool]:
    """
    Parámetros
    ----------
    df           : DataFrame leído del Excel (Histórico)
    col_consumo  : nombre de la columna de consumo energético

    Retorna
    -------
    df_ajustado  : DataFrame con la columna de consumo ya corregida
    log_ajuste   : lista de dicts con el detalle de cada corrección
    hay_anr      : True si se aplicó algún ajuste
    """
    df_out = df.copy()
    # Asegurar que la columna consumo sea float para poder escribir valores ajustados
    if col_consumo in df_out.columns:
        df_out[col_consumo] = df_out[col_consumo].astype(float)
    log_ajuste: List[dict] = []

    # 1. Detectar columna ANR
    col_anr = _detectar_columna_anr(df)
    if col_anr is None:
        return df_out, [], False

    # 2. Columna de fecha (primera columna que no sea consumo ni ANR)
    col_fecha = next(
        (c for c in df.columns if c != col_consumo and c != col_anr),
        None
    )
    if col_fecha is None:
        return df_out, [], False

    # 3. Identificar índices de meses anómalos
    indices_anomalos = [
        i for i in range(len(df))
        if _es_anomalo(df[col_anr].iloc[i])
    ]
    if not indices_anomalos:
        return df_out, [], False

    # 4. Agrupar por año
    años: dict = {}
    for i in range(len(df)):
        fecha   = df[col_fecha].iloc[i]
        año     = _extraer_año(fecha)
        consumo = df[col_consumo].iloc[i]
        if año is None or pd.isna(consumo):
            continue
        consumo = float(consumo)
        if año not in años:
            años[año] = {"normales": [], "anomalos": []}
        if _es_anomalo(df[col_anr].iloc[i]):
            años[año]["anomalos"].append((i, consumo))
        else:
            años[año]["normales"].append((i, consumo))

    hay_anr = False

    for año, grupos in años.items():
        anomalos = grupos["anomalos"]
        normales = grupos["normales"]

        if not anomalos:
            continue

        if not normales:
            for idx, val_orig in anomalos:
                fecha_str = str(df[col_fecha].iloc[idx])
                motivo    = str(df[col_anr].iloc[idx]).strip()
                log_ajuste.append({
                    "año":            año,
                    "fecha":          fecha_str,
                    "motivo":         motivo,
                    "valor_original": round(val_orig, 4),
                    "valor_ajustado": round(val_orig, 4),
                    "proporcion":     0.0,
                    "ajustado":       False,
                    "advertencia":    "Sin meses normales de referencia en el mismo año",
                })
            continue

        prom_normales = float(np.mean([v for _, v in normales]))
        prom_anomalos = float(np.mean([v for _, v in anomalos]))

        if prom_normales == 0:
            continue

        diferencia = prom_anomalos - prom_normales
        proporcion = diferencia / prom_normales

        for idx, val_orig in anomalos:
            fecha_str    = str(df[col_fecha].iloc[idx])
            motivo       = str(df[col_anr].iloc[idx]).strip()
            val_ajustado = val_orig * (1.0 - proporcion)

            df_out.at[df_out.index[idx], col_consumo] = val_ajustado
            hay_anr = True

            log_ajuste.append({
                "año":            año,
                "fecha":          fecha_str,
                "motivo":         motivo,
                "prom_normales":  round(prom_normales, 4),
                "prom_anomalos":  round(prom_anomalos, 4),
                "diferencia":     round(diferencia, 4),
                "proporcion":     round(proporcion, 6),
                "valor_original": round(val_orig, 4),
                "valor_ajustado": round(val_ajustado, 4),
                "delta_pct":      round((val_ajustado - val_orig) / val_orig * 100, 2)
                                  if val_orig != 0 else 0.0,
                "ajustado":       True,
                "advertencia":    "",
            })

    return df_out, log_ajuste, hay_anr


def resumen_anr(log_ajuste: List[dict]) -> dict:
    """Resumen compacto del proceso ANR para mostrar en la UI."""
    ajustados = [r for r in log_ajuste if r.get("ajustado")]
    no_ajust  = [r for r in log_ajuste if not r.get("ajustado")]
    años_únicos = sorted({r["año"] for r in log_ajuste})
    return {
        "n_meses_marcados": len(log_ajuste),
        "n_ajustados":      len(ajustados),
        "n_no_ajustados":   len(no_ajust),
        "años_afectados":   años_únicos,
        "detalle":          log_ajuste,
    }