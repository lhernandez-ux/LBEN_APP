"""
data/validador.py
=================
Validaciones del DataFrame antes de calcular.
Retorna una lista de mensajes de error (vacía = OK).
"""

import pandas as pd
from typing import List


def validar_dataframe(df: pd.DataFrame, col_consumo: str, vars_ind: List[str]) -> List[str]:
    errores = []

    if col_consumo not in df.columns:
        errores.append(f"Columna '{col_consumo}' no encontrada. Columnas disponibles: {list(df.columns)}")

    for v in vars_ind:
        if v not in df.columns:
            errores.append(f"Columna '{v}' no encontrada.")

    if col_consumo in df.columns:
        if df[col_consumo].dropna().shape[0] < 3:
            errores.append("Se requieren al menos 3 períodos de datos.")

        if not pd.api.types.is_numeric_dtype(df[col_consumo]):
            errores.append(f"La columna '{col_consumo}' debe ser numérica.")

        if (df[col_consumo].dropna() < 0).any():
            errores.append(f"La columna '{col_consumo}' contiene valores negativos.")

    return errores
