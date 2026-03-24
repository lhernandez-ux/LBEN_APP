"""
data/lector_excel.py — Lee una hoja específica del Excel.
"""

import re
import pandas as pd


def leer_excel(path: str, hoja: str = None) -> pd.DataFrame:
    """
    hoja: nombre exacto de la hoja ('Histórico', 'Reporte').
          Si es None busca automáticamente la primera hoja de datos.
    """
    hoja_elegida = hoja if hoja else _elegir_hoja(path)
    df = pd.read_excel(path, sheet_name=hoja_elegida, header=1)  # row 1 = encabezados reales
    df.columns = [str(c).strip() for c in df.columns]

    # Salta fila de hints si existe
    if len(df) > 0 and _es_fila_hint(df.iloc[0]):
        df = df.iloc[1:].reset_index(drop=True)

    df = df.dropna(how="all").reset_index(drop=True)

    # Normaliza números (europeo 45.200,00 → 45200.0)
    col_fecha = df.columns[0]
    for col in df.columns:
        if col == col_fecha:
            continue
        if df[col].dtype == object:
            limpio = (df[col].astype(str).str.strip()
                      .str.replace(r"\.", "", regex=True)
                      .str.replace(",", ".", regex=False))
            df[col] = pd.to_numeric(limpio, errors="coerce")

    return df


def _elegir_hoja(path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    hojas = wb.sheetnames
    wb.close()
    if "Datos" in hojas:
        return "Datos"
    for h in hojas:
        if h.strip().lower() not in ("instrucciones", "instructions"):
            return h
    return hojas[0]


def _es_fila_hint(fila: pd.Series) -> bool:
    vals = [v for v in fila if not pd.isna(v)]
    if not vals:
        return False
    return all(isinstance(v, str) and not _parece_fecha(v) and not _parece_num(v) for v in vals)


def _parece_fecha(s: str) -> bool:
    return bool(re.match(r"^[a-záéíóúñ]{3}-\d{4}$", s.strip().lower()))


def _parece_num(s: str) -> bool:
    try:
        float(s.replace(".", "").replace(",", ".").strip())
        return True
    except (ValueError, AttributeError):
        return False
