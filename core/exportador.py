"""
core/exportador.py
==================
Exporta el informe completo en Excel (con múltiples hojas y formato) o PDF.
Estrategia Excel: openpyxl con formato profesional.
Estrategia PDF:   reportlab + imágenes de los gráficos Plotly (kaleido).
"""

import io
from typing import TYPE_CHECKING
import openpyxl
from openpyxl.styles import (
    PatternFill, Font, Alignment, Border, Side, numbers
)
from openpyxl.utils import get_column_letter

if TYPE_CHECKING:
    from data.sesion import Sesion


# ── Colores corporativos para el Excel ────────────────────────────────────────
_C_PRIMARY   = "1B4F72"
_C_ACCENT    = "1E8449"
_C_MEJORA    = "D5F5E3"
_C_DEGRADAR  = "FADBD8"
_C_HEADER    = "2E86C1"
_C_WHITE     = "FFFFFF"
_C_LIGHT     = "F2F3F4"

_THIN  = Side(style="thin",   color="CCCCCC")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def exportar_informe(path: str, resultado: dict, sesion: "Sesion"):
    """Decide formato por extensión del archivo."""
    if path.endswith(".pdf"):
        _exportar_pdf(path, resultado, sesion)
    else:
        _exportar_excel(path, resultado, sesion)


# ── Excel ─────────────────────────────────────────────────────────────────────

def _exportar_excel(path: str, resultado: dict, sesion: "Sesion"):
    wb = openpyxl.Workbook()

    _hoja_resumen(wb, resultado, sesion)
    _hoja_datos(wb, resultado, sesion)
    _hoja_desempeno(wb, resultado, sesion)
    _hoja_cusum(wb, resultado, sesion)

    wb.save(path)


def _hoja_resumen(wb, resultado, sesion):
    ws = wb.active
    ws.title = "Resumen"

    # Título
    ws.merge_cells("A1:F1")
    ws["A1"] = f"Informe de Línea Base Energética — {sesion.nombre_proyecto}"
    ws["A1"].fill   = PatternFill("solid", fgColor=_C_PRIMARY)
    ws["A1"].font   = Font(bold=True, color=_C_WHITE, size=14)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 36

    # Subtítulo
    ws.merge_cells("A2:F2")
    ws["A2"] = (
        f"Modelo: {sesion.modelo_id.title()}   |   "
        f"Unidad: {sesion.unidad_energia}   |   "
        f"Períodos analizados: {resultado['kpis'].get('n_periodos', '-')}"
    )
    ws["A2"].fill = PatternFill("solid", fgColor=_C_HEADER)
    ws["A2"].font = Font(color=_C_WHITE, size=11)
    ws["A2"].alignment = Alignment(horizontal="center")

    # KPIs
    kpis = resultado.get("kpis", {})
    kpi_data = [
        ("Indicador", "Valor", "Interpretación"),
        ("R²", f"{kpis.get('r2', 0):.4f}", "Ajuste del modelo (1 = perfecto)"),
        ("SEM", f"{kpis.get('sem', 0):,.2f} {sesion.unidad_energia}", "Error estándar del modelo"),
        ("CV (%)", f"{kpis.get('cv', 0):.2f}%", "Coeficiente de variación"),
        ("N períodos", str(kpis.get("n_periodos", 0)), "Períodos de referencia"),
    ]

    for i, row_data in enumerate(kpi_data, start=4):
        for j, val in enumerate(row_data, start=1):
            cell = ws.cell(row=i, column=j, value=val)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")
            if i == 4:  # encabezado
                cell.fill = PatternFill("solid", fgColor=_C_HEADER)
                cell.font = Font(bold=True, color=_C_WHITE)
            else:
                cell.fill = PatternFill("solid", fgColor=_C_LIGHT if i % 2 == 0 else _C_WHITE)

    # Coeficientes del modelo
    coefs = kpis.get("coeficientes", {})
    if coefs:
        row = 4 + len(kpi_data) + 1
        ws.cell(row=row, column=1, value="Coeficientes del modelo").font = Font(bold=True)
        for nombre, valor in coefs.items():
            row += 1
            ws.cell(row=row, column=1, value=nombre).border = _BORDER
            ws.cell(row=row, column=2, value=valor).border = _BORDER

    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 38


def _hoja_datos(wb, resultado, sesion):
    ws = wb.create_sheet("Datos de referencia")
    _write_tabla(
        ws,
        columnas=["Período", f"Consumo real ({sesion.unidad_energia})",
                  f"Línea base ({sesion.unidad_energia})"],
        filas=[
            [f, f"{r:,.2f}", f"{b:,.2f}"]
            for f, r, b in zip(
                resultado["fechas"],
                resultado["consumo_real"],
                resultado["linea_base"],
            )
        ],
        titulo="Datos de referencia",
    )


def _hoja_desempeno(wb, resultado, sesion):
    ws = wb.create_sheet("Desempeño")
    columnas = resultado.get("columnas_desempeno", [])
    filas    = resultado.get("tabla_desempeno", [])

    _write_tabla(ws, columnas, filas, titulo="Tabla de desempeño por período")

    # Colorear filas por desviación
    try:
        col_desv = columnas.index("Desviación (%)") + 1
    except ValueError:
        return

    for row_idx, fila in enumerate(filas, start=3):
        try:
            val = float(str(fila[col_desv - 1]).replace("%", "").replace("+", "").replace(",", "."))
            fill_color = _C_MEJORA if val <= 0 else _C_DEGRADAR
            for col_idx in range(1, len(columnas) + 1):
                ws.cell(row=row_idx, column=col_idx).fill = PatternFill("solid", fgColor=fill_color)
        except ValueError:
            pass


def _hoja_cusum(wb, resultado, sesion):
    ws = wb.create_sheet("CUSUM")
    _write_tabla(
        ws,
        columnas=["Período", f"Desviación abs. ({sesion.unidad_energia})", "CUSUM acumulado"],
        filas=[
            [f, f"{d:+,.2f}", f"{c:+,.2f}"]
            for f, d, c in zip(
                resultado["fechas"],
                resultado["desviacion_abs"],
                resultado["cusum"],
            )
        ],
        titulo="Análisis CUSUM — Acumulado de desviaciones energéticas",
    )


def _write_tabla(ws, columnas, filas, titulo=""):
    # Título
    ws.merge_cells(f"A1:{get_column_letter(len(columnas))}1")
    ws["A1"] = titulo
    ws["A1"].fill = PatternFill("solid", fgColor=_C_PRIMARY)
    ws["A1"].font = Font(bold=True, color=_C_WHITE, size=12)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Encabezados
    for j, col in enumerate(columnas, start=1):
        c = ws.cell(row=2, column=j, value=col)
        c.fill   = PatternFill("solid", fgColor=_C_HEADER)
        c.font   = Font(bold=True, color=_C_WHITE)
        c.border = _BORDER
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(j)].width = 20

    # Filas
    for i, fila in enumerate(filas, start=3):
        bg = _C_LIGHT if i % 2 == 0 else _C_WHITE
        for j, val in enumerate(fila, start=1):
            c = ws.cell(row=i, column=j, value=val)
            c.fill   = PatternFill("solid", fgColor=bg)
            c.border = _BORDER
            c.alignment = Alignment(horizontal="right" if j > 1 else "left")

    ws.freeze_panes = "A3"


# ── PDF (básico con reportlab) ────────────────────────────────────────────────

def _exportar_pdf(path: str, resultado: dict, sesion: "Sesion"):
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Table, TableStyle, Paragraph,
            Spacer, Image as RLImage,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
    except ImportError:
        raise ImportError("Instala reportlab: pip install reportlab")

    doc = SimpleDocTemplate(path, pagesize=landscape(A4),
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    azul   = colors.HexColor("#1B4F72")
    verde  = colors.HexColor("#1E8449")

    titulo_style = ParagraphStyle("titulo", parent=styles["Title"],
                                   textColor=azul, fontSize=18, spaceAfter=6)
    subtitulo_style = ParagraphStyle("sub", parent=styles["Normal"],
                                      textColor=colors.HexColor("#566573"), fontSize=10)

    story = [
        Paragraph(f"Línea Base Energética — {sesion.nombre_proyecto}", titulo_style),
        Paragraph(
            f"Modelo: {sesion.modelo_id.title()} | Unidad: {sesion.unidad_energia} | "
            f"Períodos: {resultado['kpis'].get('n_periodos', '-')}",
            subtitulo_style,
        ),
        Spacer(1, 0.5*cm),
    ]

    # KPIs
    kpis = resultado.get("kpis", {})
    kpi_rows = [
        ["Indicador", "Valor"],
        ["R²",        f"{kpis.get('r2', 0):.4f}"],
        ["SEM",       f"{kpis.get('sem', 0):,.2f} {sesion.unidad_energia}"],
        ["CV (%)",    f"{kpis.get('cv', 0):.2f}%"],
        ["N períodos",str(kpis.get("n_periodos", 0))],
    ]
    t = Table(kpi_rows, colWidths=[6*cm, 5*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), azul),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F2F3F4"), colors.white]),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Tabla de desempeño
    cols_desp = resultado.get("columnas_desempeno", [])
    filas_desp = resultado.get("tabla_desempeno", [])
    if cols_desp and filas_desp:
        story.append(Paragraph("Tabla de desempeño por período", styles["Heading2"]))
        tabla_data = [cols_desp] + filas_desp
        col_w = [4*cm] * len(cols_desp)
        t2 = Table(tabla_data, colWidths=col_w, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), colors.HexColor(_C_HEADER)),
            ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
            ("FONTNAME",       (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor(_C_LIGHT), colors.white]),
            ("GRID",           (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("FONTSIZE",       (0, 0), (-1, -1), 9),
            ("ALIGN",          (1, 1), (-1, -1), "RIGHT"),
        ]))
        story.append(t2)

    doc.build(story)
