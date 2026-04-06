"""
data/plantilla.py — Genera plantilla Excel con DOS hojas de datos:
  • "Base"  — período de referencia para ajustar el modelo
  • "Reporte"    — período nuevo para evaluar desempeño (opcional)

Soporta tres frecuencias:
  • mensual: fechas en formato "ene-2024"
  • diario:  fechas en formato "dd/mm/yyyy"
  • horario: fechas en formato "dd/mm/yyyy HH:00"
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import date, datetime, timedelta
from typing import List, Union

_FILL_T   = PatternFill("solid", fgColor="1B4F72")
_FILL_S   = PatternFill("solid", fgColor="2E86C1")
_FILL_FH  = PatternFill("solid", fgColor="1B4F72")   # encabezado fecha base
_FILL_FR  = PatternFill("solid", fgColor="B7950B")   # encabezado fecha reporte
_FILL_C   = PatternFill("solid", fgColor="1E8449")
_FILL_V   = PatternFill("solid", fgColor="154360")
_FILL_P   = PatternFill("solid", fgColor="EBF5FB")
_FILL_I   = PatternFill("solid", fgColor="FFFFFF")
_FILL_ANR = PatternFill("solid", fgColor="FEF9E7")
_FILL_FD  = PatternFill("solid", fgColor="D6EAF8")   # celda fecha base
_FILL_RD  = PatternFill("solid", fgColor="FEF9E7")   # celda fecha reporte
_FW  = Font(bold=True, color="FFFFFF", size=11)
_FH  = Font(bold=True, color="1B4F72", size=11)
_FRF = Font(bold=True, color="7D6608", size=11)
_TH  = Side(style="thin",   color="C8C8C8")
_MED = Side(style="medium", color="1B4F72")
_B   = Border(left=_TH, right=_TH, top=_TH, bottom=_TH)
_AC  = Alignment(horizontal="center", vertical="center")

# Hints de fecha según frecuencia
_HINT_FECHA = {
    "mensual": "(mes-año, ej: ene-2025)",
    "diario":  "(dd/mm/yyyy, ej: 01/04/2025)",
    "horario": "(dd/mm/yyyy HH:00, ej: 01/04/2025 08:00)",
}


# ── Formateo de fechas ─────────────────────────────────────────────────────────

def _fmt_fecha(f: Union[date, datetime], frecuencia: str) -> str:
    if frecuencia == "mensual":
        ab = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
        return f"{ab[f.month-1]}-{f.year}"
    if frecuencia == "diario":
        return f.strftime("%d/%m/%Y")
    if frecuencia == "horario":
        return f.strftime("%d/%m/%Y %H:00")
    return str(f)


def _clave_fecha(valor, frecuencia: str) -> str:
    """
    Convierte un valor de celda (str, date, datetime) a una clave
    normalizada en minúsculas para detectar duplicados.
    """
    if valor is None:
        return ""
    s = str(valor).strip().lower()
    if isinstance(valor, datetime):
        return _fmt_fecha(valor, frecuencia).lower()
    if isinstance(valor, date) and not isinstance(valor, datetime):
        return _fmt_fecha(valor, frecuencia).lower()
    return s


def _freq_text(frecuencia: str) -> str:
    if frecuencia == "mensual":  return "Mensual (mes-año)"
    if frecuencia == "diario":   return "Diario (dd/mm/yyyy)"
    if frecuencia == "horario":  return "Horario (dd/mm/yyyy HH:00)"
    return frecuencia


def _ancho_col(j: int, frecuencia: str) -> int:
    """Ancho de columna adaptado: la columna de fecha puede necesitar más espacio."""
    if j == 1:
        return {"mensual": 16, "diario": 16, "horario": 22}.get(frecuencia, 18)
    return 20


# ── API pública ────────────────────────────────────────────────────────────────

def generar_plantilla(path, modelo_id, col_consumo, vars_independientes,
                      fechas_base=None, fechas_reporte=None,
                      nombre_proyecto="", zona_climatica="", unidad="kWh",
                      frecuencia="mensual"):
    wb = openpyxl.Workbook()
    _hoja_instrucciones(wb, modelo_id, nombre_proyecto, zona_climatica, unidad,
                        col_consumo, vars_independientes,
                        fechas_base, fechas_reporte, frecuencia)
    _hoja_datos(wb, "Base", col_consumo, vars_independientes,
                fechas_base or [], unidad, _FILL_FH, _FILL_FD, _FH,
                "Período base — para ajustar el modelo (línea base)",
                incluir_anr=True, frecuencia=frecuencia)
    if fechas_reporte:
        _hoja_datos(wb, "Reporte", col_consumo, vars_independientes,
                    fechas_reporte, unidad, _FILL_FR, _FILL_RD, _FRF,
                    "Período de evaluación — para evaluar el desempeño",
                    frecuencia=frecuencia)
    wb.active = wb["Base"]
    wb.save(path)


def expandir_reporte(path_origen: str, path_destino: str,
                     nuevas_fechas: list,
                     col_consumo: str,
                     vars_independientes: list,
                     unidad: str = "kWh",
                     frecuencia: str = "mensual"):
    """
    Lee el Excel base, y en la hoja 'Reporte' agrega las nuevas_fechas al
    final sin duplicar períodos ya existentes.

    La detección de duplicados es independiente del formato de la celda:
    compara claves normalizadas en minúsculas. Funciona correctamente para
    frecuencias mensual, diaria y horaria.

    Retorna (n_existentes, n_agregadas).
    """
    import shutil, os, tempfile

    wb = openpyxl.load_workbook(path_origen)

    # ── 1. Leer filas ya existentes en hoja Reporte ───────────────────────────
    fechas_existentes_clave = set()
    filas_existentes = []

    if "Reporte" in wb.sheetnames:
        ws_rep = wb["Reporte"]
        n_cols = 1 + 1 + len(vars_independientes)
        for row in ws_rep.iter_rows(min_row=4, max_col=n_cols, values_only=True):
            fecha_val = row[0]
            if fecha_val is None or str(fecha_val).strip() == "":
                continue
            clave = _clave_fecha(fecha_val, frecuencia)
            if not clave:
                continue
            if isinstance(fecha_val, (datetime, date)):
                fecha_str = _fmt_fecha(fecha_val, frecuencia)
            else:
                fecha_str = str(fecha_val).strip()
            fechas_existentes_clave.add(clave)
            filas_existentes.append((fecha_str, list(row[1:])))

    # ── 2. Filtrar solo fechas realmente nuevas ───────────────────────────────
    fechas_a_agregar = [
        f for f in nuevas_fechas
        if _fmt_fecha(f, frecuencia).lower() not in fechas_existentes_clave
    ]
    n_existentes = len(filas_existentes)
    n_agregadas  = len(fechas_a_agregar)

    if n_agregadas == 0:
        wb.close()
        if os.path.normpath(path_destino) != os.path.normpath(path_origen):
            shutil.copy2(path_origen, path_destino)
        return n_existentes, 0

    # ── 3. Reconstruir hoja Reporte ───────────────────────────────────────────
    if "Reporte" in wb.sheetnames:
        del wb["Reporte"]

    columnas  = ["Fecha", col_consumo] + vars_independientes
    fills_hdr = [_FILL_FR, _FILL_C] + [_FILL_V] * len(vars_independientes)
    n_cols_tot = len(columnas)

    ws = wb.create_sheet("Reporte")

    # Fila 1: título
    ws.merge_cells(f"A1:{get_column_letter(n_cols_tot)}1")
    ws["A1"] = "Período de reporte — para evaluar el desempeño"
    ws["A1"].fill = _FILL_T
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=11)
    ws["A1"].alignment = _AC
    ws.row_dimensions[1].height = 24

    # Fila 2: encabezados
    for j, (col, fill) in enumerate(zip(columnas, fills_hdr), start=1):
        c = ws.cell(row=2, column=j, value=col)
        c.fill = fill; c.font = _FW; c.alignment = _AC; c.border = _B
        ws.column_dimensions[get_column_letter(j)].width = _ancho_col(j, frecuencia)

    # Fila 3: hints — adaptados a la frecuencia
    hint_fecha = _HINT_FECHA.get(frecuencia, "(fecha)")
    hints = [hint_fecha, f"Consumo en {unidad}"] + \
            [f"Variable {i+1}" for i in range(len(vars_independientes))]
    for j, h in enumerate(hints, start=1):
        c = ws.cell(row=3, column=j, value=h)
        c.font = Font(italic=True, color="999999", size=9)
        c.alignment = _AC; c.border = _B

    # Filas existentes (conserva valores)
    for i, (fecha_str, valores) in enumerate(filas_existentes):
        r   = i + 4
        bg  = _FILL_P if i % 2 == 0 else _FILL_I
        cf  = ws.cell(row=r, column=1, value=fecha_str)
        cf.fill = _FILL_RD; cf.font = _FRF; cf.alignment = _AC; cf.border = _B
        for j_off, val in enumerate(valores):
            c = ws.cell(row=r, column=j_off + 2, value=val)
            c.fill = bg; c.alignment = _AC; c.border = _B
            if val is not None:
                c.number_format = "#,##0.00"

    # Filas nuevas (vacías)
    base_i = len(filas_existentes)
    for k, fecha_obj in enumerate(fechas_a_agregar):
        i   = base_i + k
        r   = i + 4
        bg  = _FILL_P if i % 2 == 0 else _FILL_I
        cf  = ws.cell(row=r, column=1, value=_fmt_fecha(fecha_obj, frecuencia))
        cf.fill = _FILL_RD; cf.font = _FRF; cf.alignment = _AC; cf.border = _B
        for j in range(2, n_cols_tot + 1):
            c = ws.cell(row=r, column=j)
            c.fill = bg; c.alignment = _AC; c.border = _B
            c.number_format = "#,##0.00"

    ws.freeze_panes = "B4"

    # ── 4. Guardar ────────────────────────────────────────────────────────────
    fd, tmp_path = tempfile.mkstemp(
        suffix=".xlsx", dir=os.path.dirname(path_destino) or ".")
    os.close(fd)
    try:
        wb.save(tmp_path)
        wb.close()
        if os.path.exists(path_destino):
            os.remove(path_destino)
        shutil.move(tmp_path, path_destino)
    except Exception:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        raise

    return n_existentes, n_agregadas


# ── Helpers internos ──────────────────────────────────────────────────────────

def _hoja_instrucciones(wb, modelo_id, nombre_proyecto, zona_climatica, unidad,
                         col_consumo, vars_ind, fh, fr, frecuencia):
    ws = wb.active
    ws.title = "Instrucciones"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 45

    ws.merge_cells("A1:B1")
    ws["A1"] = "Herramienta de Línea Base Energética"
    ws["A1"].fill = _FILL_T
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=13)
    ws["A1"].alignment = _AC
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:B2")
    ws["A2"] = (f"Modelo: {modelo_id.title()}  |  Proyecto: {nombre_proyecto or '—'}  |  "
                f"Unidad: {unidad}  |  Frecuencia: {_freq_text(frecuencia)}")
    ws["A2"].fill = _FILL_S
    ws["A2"].font = Font(bold=True, color="FFFFFF", size=10)
    ws["A2"].alignment = _AC

    datos = [
        ("Columna consumo:", col_consumo),
        ("Variables ind.:",  ", ".join(vars_ind) if vars_ind else "Ninguna"),
        ("Zona climática:",  zona_climatica or "-"),
        ("Período base:",
         f"{_fmt_fecha(fh[0], frecuencia)} → {_fmt_fecha(fh[-1], frecuencia)}  ({len(fh)} períodos)"
         if fh else "—"),
        ("Período de evaluación:",
         f"{_fmt_fecha(fr[0], frecuencia)} → {_fmt_fecha(fr[-1], frecuencia)}  ({len(fr)} períodos)"
         if fr else "No configurado"),
    ]
    for i, (k, v) in enumerate(datos, start=4):
        ws[f"A{i}"] = k; ws[f"A{i}"].font = Font(bold=True, size=10, color="1B4F72")
        ws[f"B{i}"] = v; ws[f"B{i}"].font = Font(size=10)

    ws["A9"] = "INSTRUCCIONES"
    ws["A9"].font = Font(bold=True, size=11, color="1B4F72")

    freq_fmts = {
        "mensual": "   Las fechas están en formato 'ene-2024' (mes-año).",
        "diario":  "   Las fechas están en formato 'dd/mm/yyyy' (ej: 01/04/2025).",
        "horario": "   Las fechas están en formato 'dd/mm/yyyy HH:00' (ej: 01/04/2025 08:00).",
    }
    lineas = [
        "1. Hoja 'Base': llena los datos del período de referencia.",
        freq_fmts.get(frecuencia, "   Las fechas ya están precargadas."),
        "   Solo completa los valores numéricos.",
        "2. Columna 'Ajuste_NR' (Hoja Base): OPCIONAL.",
        "   Escribe el motivo si un período es anómalo (ej: 'mantenimiento').",
        "   Deja en blanco si el período es normal.",
        "3. Hoja 'Reporte' (si existe): llena los datos del período a evaluar.",
        "4. No elimines ni renombres las columnas.",
        "5. No dejes celdas numéricas vacías dentro del rango.",
    ]
    for i, l in enumerate(lineas, start=10):
        ws[f"A{i}"] = l; ws[f"A{i}"].font = Font(size=10)


def _hoja_datos(wb, nombre_hoja, col_consumo, vars_ind, fechas,
                unidad, fill_hdr_fecha, fill_celda_fecha, font_fecha, titulo,
                incluir_anr=False, frecuencia="mensual"):
    ws = wb.create_sheet(nombre_hoja)
    columnas  = ["Fecha", col_consumo] + vars_ind
    if incluir_anr:
        columnas += ["Ajuste_NR"]
    fills_hdr = [fill_hdr_fecha, _FILL_C] + [_FILL_V] * len(vars_ind)
    if incluir_anr:
        fills_hdr += [PatternFill("solid", fgColor="B7950B")]

    # Fila 1: título
    ws.merge_cells(f"A1:{get_column_letter(len(columnas))}1")
    ws["A1"] = titulo
    ws["A1"].fill = _FILL_T
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=11)
    ws["A1"].alignment = _AC
    ws.row_dimensions[1].height = 24

    # Fila 2: encabezados
    for j, (col, fill) in enumerate(zip(columnas, fills_hdr), start=1):
        c = ws.cell(row=2, column=j, value=col)
        c.fill = fill; c.font = _FW; c.alignment = _AC; c.border = _B
        ws.column_dimensions[get_column_letter(j)].width = _ancho_col(j, frecuencia)

    # Fila 3: hints — adaptados a la frecuencia
    hint_fecha = _HINT_FECHA.get(frecuencia, "(fecha)")
    anr_hint = (["¿Período anómalo? (motivo)"] if incluir_anr else [])
    hints = [hint_fecha, f"Consumo en {unidad}"] + \
            [f"Variable {i+1}" for i in range(len(vars_ind))] + anr_hint
    for j, h in enumerate(hints, start=1):
        c = ws.cell(row=3, column=j, value=h)
        c.font = Font(italic=True, color="999999", size=9)
        c.alignment = _AC; c.border = _B

    # Filas de datos
    n_data_cols = len(columnas)
    for i, f in enumerate(fechas):
        r  = i + 4
        bg = _FILL_P if i % 2 == 0 else _FILL_I
        for j in range(1, n_data_cols + 1):
            c = ws.cell(row=r, column=j)
            c.border = _B; c.alignment = _AC
            col_name = columnas[j - 1]
            if j == 1:
                c.value = _fmt_fecha(f, frecuencia)
                c.fill  = fill_celda_fecha
                c.font  = font_fecha
            elif col_name == "Ajuste_NR":
                c.fill  = _FILL_ANR
                c.value = ""
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.fill          = bg
                c.number_format = "#,##0.00"

    ws.freeze_panes = "B4"