"""
data/plantilla.py — Genera plantilla Excel con DOS hojas de datos:
  • "Histórico"  — período de referencia para ajustar el modelo
  • "Reporte"    — período nuevo para evaluar desempeño (opcional)
  
Soporta tres frecuencias:
  • mensual: fechas en formato "ene-2024"
  • diario:  fechas en formato "dd/mm/yyyy"
  • horario: fechas en formato "dd/mm/yyyy HH:00"
"""

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from datetime import date, datetime
from typing import List, Optional, Union

_FILL_T  = PatternFill("solid", fgColor="1B4F72")
_FILL_S  = PatternFill("solid", fgColor="2E86C1")
_FILL_FH = PatternFill("solid", fgColor="1B4F72")   # encabezado fecha histórico
_FILL_FR = PatternFill("solid", fgColor="B7950B")   # encabezado fecha reporte
_FILL_C  = PatternFill("solid", fgColor="1E8449")
_FILL_V  = PatternFill("solid", fgColor="154360")
_FILL_P  = PatternFill("solid", fgColor="EBF5FB")
_FILL_I  = PatternFill("solid", fgColor="FFFFFF")
_FILL_ANR = PatternFill("solid", fgColor="FEF9E7")  # columna Ajuste_NR
_FILL_FD = PatternFill("solid", fgColor="D6EAF8")   # celda fecha histórico
_FILL_RD = PatternFill("solid", fgColor="FEF9E7")   # celda fecha reporte
_FW  = Font(bold=True, color="FFFFFF", size=11)
_FH  = Font(bold=True, color="1B4F72", size=11)
_FRF = Font(bold=True, color="7D6608", size=11)
_TH  = Side(style="thin",   color="C8C8C8")
_MED = Side(style="medium", color="1B4F72")
_B   = Border(left=_TH, right=_TH, top=_TH, bottom=_TH)
_AC  = Alignment(horizontal="center", vertical="center")


def generar_plantilla(path, modelo_id, col_consumo, vars_independientes,
                      fechas_historico=None, fechas_reporte=None,
                      nombre_proyecto="", zona_climatica="", unidad="kWh",
                      frecuencia="mensual"):
    """
    Genera la plantilla Excel.
    
    Args:
        frecuencia: "mensual", "diario" o "horario"
    """
    wb = openpyxl.Workbook()
    _hoja_instrucciones(wb, modelo_id, nombre_proyecto, zona_climatica, unidad,
                        col_consumo, vars_independientes,
                        fechas_historico, fechas_reporte, frecuencia)
    _hoja_datos(wb, "Histórico", col_consumo, vars_independientes,
                fechas_historico or [], unidad, _FILL_FH, _FILL_FD, _FH,
                "Período histórico — para ajustar el modelo (línea base)",
                incluir_anr=True, frecuencia=frecuencia)
    if fechas_reporte:
        _hoja_datos(wb, "Reporte", col_consumo, vars_independientes,
                    fechas_reporte, unidad, _FILL_FR, _FILL_RD, _FRF,
                    "Período de reporte — para evaluar el desempeño",
                    frecuencia=frecuencia)
    wb.active = wb["Histórico"]
    wb.save(path)


def _hoja_instrucciones(wb, modelo_id, nombre_proyecto, zona_climatica, unidad,
                         col_consumo, vars_ind, fh, fr, frecuencia):
    ws = wb.active
    ws.title = "Instrucciones"
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 45

    ws.merge_cells("A1:B1")
    ws["A1"] = "Herramienta de Línea Base Energética"
    ws["A1"].fill = _FILL_T; ws["A1"].font = Font(bold=True, color="FFFFFF", size=13)
    ws["A1"].alignment = _AC; ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:B2")
    ws["A2"] = f"Modelo: {modelo_id.title()}  |  Proyecto: {nombre_proyecto or '—'}  |  Unidad: {unidad}  |  Frecuencia: {_freq_text(frecuencia)}"
    ws["A2"].fill = _FILL_S; ws["A2"].font = Font(bold=True, color="FFFFFF", size=10)
    ws["A2"].alignment = _AC

    datos = [
        ("Columna consumo:", col_consumo),
        ("Variables ind.:", ", ".join(vars_ind) if vars_ind else "Ninguna"),
        ("Zona climática:", zona_climatica or "-"),
        ("Período histórico:", f"{_fmt_fecha(fh[0], frecuencia)} → {_fmt_fecha(fh[-1], frecuencia)}  ({len(fh)} períodos)" if fh else "—"),
        ("Período de reporte:", f"{_fmt_fecha(fr[0], frecuencia)} → {_fmt_fecha(fr[-1], frecuencia)}  ({len(fr)} períodos)" if fr else "No configurado"),
    ]
    for i, (k, v) in enumerate(datos, start=4):
        ws[f"A{i}"] = k; ws[f"A{i}"].font = Font(bold=True, size=10, color="1B4F72")
        ws[f"B{i}"] = v; ws[f"B{i}"].font = Font(size=10)

    ws["A9"] = "INSTRUCCIONES"
    ws["A9"].font = Font(bold=True, size=11, color="1B4F72")

    freq_instructions = {
        "mensual": "   Las fechas están en formato 'ene-2024' (mes-año).",
        "diario":  "   Las fechas están en formato 'dd/mm/yyyy' (día/mes/año).",
        "horario": "   Las fechas están en formato 'dd/mm/yyyy HH:00' (día/mes/año hora).",
    }
    
    lineas = [
        "1. Hoja 'Histórico': llena los datos del período de referencia.",
        freq_instructions.get(frecuencia, "   Las fechas ya están precargadas."),
        "   Solo completa los valores numéricos.",
        "2. Columna 'Ajuste_NR' (Hoja Histórico): OPCIONAL.",
        "   Escribe el motivo si un mes es anómalo (ej: 'mantenimiento', 'falla').",
        "   Deja en blanco si el período es normal.",
        "   Los períodos marcados se corregirán automáticamente antes de calcular.",
        "3. Hoja 'Reporte' (si existe): llena los datos del período a evaluar.",
        "   La herramienta comparará estos datos con la línea base calculada.",
        "4. No elimines ni renombres las columnas.",
        "5. No dejes celdas numéricas vacías dentro del rango.",
    ]
    for i, l in enumerate(lineas, start=10):
        ws[f"A{i}"] = l; ws[f"A{i}"].font = Font(size=10)


def _hoja_datos(wb, nombre_hoja, col_consumo, vars_ind, fechas,
                unidad, fill_hdr_fecha, fill_celda_fecha, font_fecha, titulo,
                incluir_anr=False, frecuencia="mensual"):
    ws = wb.create_sheet(nombre_hoja)
    columnas = ["Fecha", col_consumo] + vars_ind
    if incluir_anr:
        columnas += ["Ajuste_NR"]
    fills_hdr = [fill_hdr_fecha, _FILL_C] + [_FILL_V] * len(vars_ind)
    if incluir_anr:
        fills_hdr += [PatternFill("solid", fgColor="B7950B")]

    # Fila 1: título de la hoja
    ws.merge_cells(f"A1:{get_column_letter(len(columnas))}1")
    ws["A1"] = titulo
    ws["A1"].fill = _FILL_T
    ws["A1"].font = Font(bold=True, color="FFFFFF", size=11)
    ws["A1"].alignment = _AC
    ws.row_dimensions[1].height = 24

    # Fila 2: encabezados de columna
    for j, (col, fill) in enumerate(zip(columnas, fills_hdr), start=1):
        c = ws.cell(row=2, column=j, value=col)
        c.fill = fill; c.font = _FW; c.alignment = _AC; c.border = _B
        ws.column_dimensions[get_column_letter(j)].width = 20

    # Fila 3: hints
    anr_cols = (["¿Período anómalo? (motivo)"] if incluir_anr else [])
    hints = ["(automático)", f"Consumo en {unidad}"] + [f"Variable {i+1}" for i in range(len(vars_ind))] + anr_cols
    for j, h in enumerate(hints, start=1):
        c = ws.cell(row=3, column=j, value=h)
        c.font = Font(italic=True, color="999999", size=9)
        c.alignment = _AC; c.border = _B

    # Filas de datos
    n_data_cols = len(columnas)
    for i, f in enumerate(fechas):
        r = i + 4
        bg = _FILL_P if i % 2 == 0 else _FILL_I
        for j in range(1, n_data_cols + 1):
            c = ws.cell(row=r, column=j)
            c.border = _B; c.alignment = _AC
            col_name = columnas[j - 1]
            if j == 1:
                c.value = _fmt_fecha(f, frecuencia)
                c.fill = fill_celda_fecha
                c.font = font_fecha
            elif col_name == "Ajuste_NR":
                c.fill = _FILL_ANR
                c.value = ""
                c.alignment = Alignment(horizontal="left", vertical="center")
            else:
                c.fill = bg
                c.number_format = "#,##0.00"

    ws.freeze_panes = "B4"


def _fmt_fecha(f: Union[date, datetime], frecuencia: str) -> str:
    """Formatea una fecha según la frecuencia."""
    if frecuencia == "mensual":
        ab = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
        return f"{ab[f.month-1]}-{f.year}"
    elif frecuencia == "diario":
        return f.strftime("%d/%m/%Y")
    elif frecuencia == "horario":
        return f.strftime("%d/%m/%Y %H:00")
    return str(f)


def _freq_text(frecuencia: str) -> str:
    """Devuelve el texto descriptivo de la frecuencia."""
    if frecuencia == "mensual":
        return "Mensual (mes-año)"
    elif frecuencia == "diario":
        return "Diario (día/mes/año)"
    elif frecuencia == "horario":
        return "Horario (día/mes/año hora)"
    return frecuencia


def expandir_reporte(path_origen, path_destino, nuevas_fechas,
                     col_consumo, vars_independientes, unidad="kWh", frecuencia="mensual"):
    """
    Lee el Excel base (path_origen), y en la hoja 'Reporte' agrega las
    nuevas_fechas al final (sin duplicar los períodos ya existentes).
    Guarda el resultado en path_destino (puede ser el mismo archivo).
    Devuelve (n_existentes, n_agregadas).
    """
    import shutil, os, tempfile

    # ── 1. Leer workbook original ─────────────────────────────────────────────
    wb = openpyxl.load_workbook(path_origen)

    # ── 2. Leer filas ya existentes en hoja Reporte ───────────────────────────
    fechas_existentes_str = []
    filas_existentes = []

    if "Reporte" in wb.sheetnames:
        ws_rep = wb["Reporte"]
        n_cols = 1 + 1 + len(vars_independientes)
        for row in ws_rep.iter_rows(min_row=4, max_col=n_cols, values_only=True):
            fecha_val = row[0]
            if fecha_val is None or not str(fecha_val).strip():
                continue
            fecha_str = str(fecha_val).strip()
            valores   = list(row[1:])
            fechas_existentes_str.append(fecha_str.lower())
            filas_existentes.append((fecha_str, valores))

    # ── 3. Filtrar solo fechas realmente nuevas ───────────────────────────────
    def _fmt_fecha_local(f):
        if frecuencia == "mensual":
            ab = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
            return f"{ab[f.month-1]}-{f.year}"
        elif frecuencia == "diario":
            return f.strftime("%d/%m/%Y")
        elif frecuencia == "horario":
            return f.strftime("%d/%m/%Y %H:00")
        return str(f)

    fechas_a_agregar = [
        f for f in nuevas_fechas
        if _fmt_fecha_local(f).lower() not in fechas_existentes_str
    ]
    n_existentes = len(filas_existentes)
    n_agregadas  = len(fechas_a_agregar)

    if n_agregadas == 0:
        wb.close()
        if os.path.normpath(path_destino) != os.path.normpath(path_origen):
            shutil.copy2(path_origen, path_destino)
        return n_existentes, 0

    # ── 4. Reconstruir hoja Reporte con datos existentes + filas nuevas ───────
    if "Reporte" in wb.sheetnames:
        del wb["Reporte"]

    columnas   = ["Fecha", col_consumo] + vars_independientes
    fills_hdr  = [_FILL_FR, _FILL_C] + [_FILL_V] * len(vars_independientes)
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
        ws.column_dimensions[get_column_letter(j)].width = 20

    # Fila 3: hints
    hints = ["(automático)", f"Consumo en {unidad}"] + \
            [f"Variable {i+1}" for i in range(len(vars_independientes))]
    for j, h in enumerate(hints, start=1):
        c = ws.cell(row=3, column=j, value=h)
        c.font = Font(italic=True, color="999999", size=9)
        c.alignment = _AC; c.border = _B

    # Filas existentes (conserva sus valores)
    for i, (fecha_str, valores) in enumerate(filas_existentes):
        r = i + 4
        bg = _FILL_P if i % 2 == 0 else _FILL_I
        cf = ws.cell(row=r, column=1, value=fecha_str)
        cf.fill = _FILL_RD; cf.font = _FRF; cf.alignment = _AC; cf.border = _B
        for j_off, val in enumerate(valores):
            c = ws.cell(row=r, column=j_off + 2, value=val)
            c.fill = bg; c.alignment = _AC; c.border = _B
            if val is not None:
                c.number_format = "#,##0.00"

    # Filas nuevas (vacías para llenar)
    base_i = len(filas_existentes)
    for k, fecha_obj in enumerate(fechas_a_agregar):
        i = base_i + k
        r = i + 4
        bg = _FILL_P if i % 2 == 0 else _FILL_I
        cf = ws.cell(row=r, column=1, value=_fmt_fecha_local(fecha_obj))
        cf.fill = _FILL_RD; cf.font = _FRF; cf.alignment = _AC; cf.border = _B
        for j in range(2, n_cols_tot + 1):
            c = ws.cell(row=r, column=j)
            c.fill = bg; c.alignment = _AC; c.border = _B
            c.number_format = "#,##0.00"

    ws.freeze_panes = "B4"

    # ── 5. Guardar en archivo temporal, luego mover al destino ────────────────
    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx", dir=os.path.dirname(path_destino) or ".")
    os.close(fd)
    try:
        wb.save(tmp_path)
        wb.close()
        # Reemplazar destino
        if os.path.exists(path_destino):
            os.remove(path_destino)
        shutil.move(tmp_path, path_destino)
    except Exception:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except Exception: pass
        raise

    return n_existentes, n_agregadas