"""
data/lector_excel.py — Lee una hoja específica del Excel.
"""

import re
import pandas as pd


# Patrón para detectar la columna de Ajuste No Rutinario (ANR).
# Se usa aquí para NO convertirla a numérico, ya que contiene texto libre.
_PATRON_COL_ANR = re.compile(
    r"ajuste.?nr|ajustenr|\banr\b|anomal[íi]a?|anomalo?|"
    r"mes.?anomal|no.?rutinario|rutinario",
    re.IGNORECASE,
)

# Patrón para detectar la columna de días de facturación.
_PATRON_COL_DIAS = re.compile(
    r"d[íi]as?.?facturaci[oó]n|dias?.?fact|dias?.?period|d[íi]as?.?ciclo",
    re.IGNORECASE,
)


def _es_columna_anr(nombre: str) -> bool:
    """True si el nombre de columna corresponde a la columna de marcado ANR."""
    return bool(_PATRON_COL_ANR.search(nombre.strip()))


def _es_columna_dias(nombre: str) -> bool:
    """True si el nombre de columna corresponde a la columna de días de facturación."""
    return bool(_PATRON_COL_DIAS.search(nombre.strip()))


def _detectar_separador(series: pd.Series) -> str:
    """
    Analiza una columna de strings y detecta si usa separador
    decimal europeo (coma) o anglosajón (punto).
    Retorna 'europeo' o 'anglosajón'.
    """
    for val in series.dropna():
        s = str(val).strip()
        # Si tiene coma Y punto, el último que aparece es el decimal
        if "," in s and "." in s:
            return "europeo" if s.rfind(",") > s.rfind(".") else "anglosajón"
        # Si solo tiene coma → decimal europeo
        if "," in s and "." not in s:
            return "europeo"
        # Si solo tiene punto → decimal anglosajón
        if "." in s and "," not in s:
            return "anglosajón"
    return "anglosajón"  # default si no hay pistas


def leer_excel(path: str, hoja: str = None) -> pd.DataFrame:
    """
    hoja: nombre exacto de la hoja ('Base', 'Reporte').
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
    # EXCEPCIÓN: columnas ANR y Días_facturación se tratan aparte
    col_fecha = df.columns[0]
    for col in df.columns:
        if col == col_fecha or _es_columna_anr(col) or _es_columna_dias(col):
            continue
        if df[col].dtype == object:
            sep = _detectar_separador(df[col])
            if sep == "europeo":
                limpio = (df[col].astype(str).str.strip()
                      .str.replace(r"\.", "", regex=True)
                      .str.replace(",", ".", regex=False))
            else:
                limpio = (df[col].astype(str).str.strip()
                        .str.replace(",", "", regex=False))  # solo quita separador de miles
            df[col] = pd.to_numeric(limpio, errors="coerce")

    # ── Normalización a 30 días (Ec. 1, Resolución UPME 16/2024) ─────────────
    # Si existe la columna Días_facturación, normaliza el consumo en el acto
    # y luego la descarta para que el resto del sistema no la vea.
    col_dias = next((c for c in df.columns if _es_columna_dias(c)), None)
    col_consumo_detectada = df.columns[1] if len(df.columns) > 1 else None

    if col_dias and col_consumo_detectada:
        dias = pd.to_numeric(df[col_dias], errors="coerce").fillna(30)
        dias = dias.replace(0, 30)   # evitar división por cero
        consumo = pd.to_numeric(df[col_consumo_detectada], errors="coerce")
        df[col_consumo_detectada] = (consumo / dias * 30).round(4)
        df = df.drop(columns=[col_dias])   # ya no es necesaria downstream

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