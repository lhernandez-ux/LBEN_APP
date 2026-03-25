"""
ui/components/chart_widget.py
==============================
Gráficos Plotly embebidos en CustomTkinter via kaleido (PNG estático)
con botón para abrir versión interactiva en el navegador.
"""

import io
import numpy as np
import customtkinter as ctk
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ui.theme import COLORS, FONTS, get_chart_layout


class ChartWidget(ctk.CTkFrame):
    def __init__(self, parent, height: int = 400, **kwargs):
        super().__init__(parent, fg_color=COLORS.bg_card,
                         corner_radius=12, border_width=1,
                         border_color=COLORS.border, **kwargs)
        self._height = height
        self._fig    = None

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=30)
        btn_row.pack(fill="x", padx=10, pady=(6, 2))
        btn_row.pack_propagate(False)
        ctk.CTkButton(btn_row,
                      text="🌐 Ver interactivo en navegador",
                      font=(FONTS.family, FONTS.size_xs),
                      fg_color="transparent",
                      hover_color=COLORS.primary_light,
                      text_color=COLORS.primary,
                      height=26,
                      command=self._abrir_web).pack(side="right")

        self._img_label = ctk.CTkLabel(self, text="")
        self._img_label.pack(expand=True, fill="both", padx=6, pady=(0, 8))

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self, fig: go.Figure, width: int = 960):
        self._fig = fig
        try:
            raw = fig.to_image(format="png", width=width,
                               height=self._height, scale=1.5)
            img    = Image.open(io.BytesIO(raw))
            display_w = int(img.width  / 1.5)
            display_h = int(img.height / 1.5)
            ctk_img = ctk.CTkImage(light_image=img, size=(display_w, display_h))
            self._img_label.configure(image=ctk_img, text="")
            self._img_label._image = ctk_img
        except Exception:
            self._img_label.configure(
                text="Instala kaleido para ver gráficos:\n  pip install kaleido\n\n"
                     "Usa el botón para abrir en el navegador.",
                text_color=COLORS.text_secondary,
                font=(FONTS.family, FONTS.size_sm),
            )

    def _abrir_web(self):
        if self._fig:
            import webbrowser, tempfile
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
                self._fig.write_html(f.name)
                webbrowser.open(f"file://{f.name}")

    # ── Gráfico 1: Línea base — agrupado por mes (un punto por año) ─────────────

    def plot_linea_base(self, resultado: dict, titulo_proyecto: str = ""):
        """
        Eje X = 12 meses del año.
        Una serie por cada año del histórico (puntos conectados).
        Línea roja = LBEn (promedio mensual).
        Outliers marcados con X roja.
        """
        unidad = resultado.get("unidad", "")
        params = resultado.get("modelo_params", {})
        datos_por_mes  = params.get("datos_por_mes",  {})   # {1: [v_año1, v_año2,...], ...}
        datos_depurados = params.get("datos_depurados", {})
        outliers_mes   = params.get("outliers", {})
        lben_mensual   = params.get("lben_mensual", {})
        ic_mensual     = params.get("ic_mensual", {})

        # Si no hay datos_por_mes, intentar con coc_depurados (modelo cociente)
        if not datos_por_mes or not any(datos_por_mes.values()):
            coc_dep = params.get("coc_depurados", {})
            if coc_dep and any(coc_dep.values()):
                # Cociente: misma visualización por mes pero con cocientes (kWh/variable)
                self._plot_linea_base_cociente(resultado, titulo_proyecto)
            else:
                self._plot_linea_base_cronologico(resultado, titulo_proyecto)
            return

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]
        meses_x = NOMBRES  # eje X fijo

        # Detectar cuántos años hay (máximo de datos en cualquier mes)
        n_years = max((len(v) for v in datos_por_mes.values() if v), default=0)

        # Paleta de colores por año
        PALETA = ["#2E86C1","#E67E22","#27AE60","#8E44AD",
                  "#E74C3C","#1ABC9C","#F39C12","#2C3E50"]

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Línea Base Energética — {titulo_proyecto}" if titulo_proyecto
                    else "Línea Base Energética",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]    = {"text": "Mes"}
        layout["xaxis"]["tickangle"] = 0   # horizontal para meses cortos
        layout["yaxis"]["title"]    = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]            = {"l": 70, "r": 20, "t": 70, "b": 80}
        layout["plot_bgcolor"]      = "#FAFAFA"
        layout["legend"]            = {
            "orientation": "h",
            "yanchor": "top", "y": -0.18,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # ── Banda IC ──────────────────────────────────────────────────────────
        ic_sup_vals = [ic_mensual.get(m, (None,None))[1] for m in range(1,13)]
        ic_inf_vals = [ic_mensual.get(m, (None,None))[0] for m in range(1,13)]
        if any(v is not None for v in ic_sup_vals):
            ic_sup_clean = [v if v is not None else 0 for v in ic_sup_vals]
            ic_inf_clean = [v if v is not None else 0 for v in ic_inf_vals]
            fig.add_trace(go.Scatter(
                x=meses_x + meses_x[::-1],
                y=ic_sup_clean + ic_inf_clean[::-1],
                fill="toself",
                fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Intervalo de confianza",
                hoverinfo="skip",
                showlegend=True,
            ))

        # ── Una serie por año ──────────────────────────────────────────────────
        outlier_set = set()
        for lst in outliers_mes.values():
            for v in lst:
                outlier_set.add(round(float(v), 4))

        # Determinar etiquetas de año reales
        años_por_mes = params.get("años_por_mes", {})
        # Recopilar años únicos en orden
        años_vistos = []
        for mes in range(1, 13):
            for a in años_por_mes.get(mes, []):
                if a is not None and a not in años_vistos:
                    años_vistos.append(a)
        años_vistos.sort()
        # Si no hay info de año, usar "Año 1", "Año 2"...
        def _label_año(yr_idx):
            if yr_idx < len(años_vistos):
                return str(años_vistos[yr_idx])
            return f"Año {yr_idx + 1}"

        for yr_idx in range(n_years):
            y_vals  = []
            hover   = []
            label   = _label_año(yr_idx)
            for mes in range(1, 13):
                vals = datos_por_mes.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.0f} {unidad}")
                else:
                    y_vals.append(None)
                    hover.append("")

            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=meses_x,
                y=y_vals,
                mode="markers",
                name=label,
                marker=dict(color=color, size=9,
                            line=dict(width=1.5, color="white")),
                text=hover,
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── Outliers marcados con X ───────────────────────────────────────────
        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1])
                y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.0f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out,
                mode="markers",
                name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out,
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── LBEn (promedio mensual) — línea roja ──────────────────────────────
        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            fig.add_trace(go.Scatter(
                x=meses_x,
                y=lben_vals,
                mode="lines+markers",
                name="LBEn (promedio mes)",
                line=dict(color="#E74C3C", width=2.5),
                marker=dict(color="#E74C3C", size=7),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

        fig.update_layout(**layout)
        self._render(fig)

    def _plot_linea_base_cociente(self, resultado: dict, titulo_proyecto: str = ""):
        """
        Gráfico de línea base para modelo cociente.
        Eje X = 12 meses. Puntos por año con el valor del cociente (kWh/variable).
        Línea roja = LBEn mensual (cociente promedio depurado).
        """
        unidad  = resultado.get("unidad", "")
        params  = resultado.get("modelo_params", {})
        coc_dep      = params.get("coc_depurados", {})
        outliers_mes = params.get("outliers", {})
        lben_mensual = params.get("lben_mensual", {})
        ic_mensual   = params.get("ic_mensual", {})
        años_por_mes = params.get("años_por_mes", {})
        variable     = params.get("variable", "variable")

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]
        meses_x = NOMBRES

        n_years = max((len(v) for v in coc_dep.values() if v), default=0)
        PALETA  = ["#2E86C1","#E67E22","#27AE60","#8E44AD",
                   "#E74C3C","#1ABC9C","#F39C12","#2C3E50"]

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Línea Base Energética (Cociente) — {titulo_proyecto}" if titulo_proyecto
                    else "Línea Base Energética (Cociente)",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": "Mes"}
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["title"]     = {"text": f"Cociente (kWh/{variable})"}
        layout["margin"]             = {"l": 70, "r": 20, "t": 70, "b": 80}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["legend"]             = {
            "orientation": "h",
            "yanchor": "top", "y": -0.18,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # Banda IC
        ic_sup_vals = [ic_mensual.get(m, (None,None))[1] for m in range(1,13)]
        ic_inf_vals = [ic_mensual.get(m, (None,None))[0] for m in range(1,13)]
        if any(v is not None for v in ic_sup_vals):
            ic_sup_c = [v if v is not None else 0 for v in ic_sup_vals]
            ic_inf_c = [v if v is not None else 0 for v in ic_inf_vals]
            fig.add_trace(go.Scatter(
                x=meses_x + meses_x[::-1],
                y=ic_sup_c + ic_inf_c[::-1],
                fill="toself", fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Intervalo de confianza",
                hoverinfo="skip", showlegend=True,
            ))

        # Años únicos en orden
        años_vistos = []
        for mes in range(1, 13):
            for a in años_por_mes.get(mes, []):
                if a is not None and a not in años_vistos:
                    años_vistos.append(a)
        años_vistos.sort()

        def _label_año(idx):
            return str(años_vistos[idx]) if idx < len(años_vistos) else f"Año {idx+1}"

        for yr_idx in range(n_years):
            y_vals = []
            hover  = []
            label  = _label_año(yr_idx)
            for mes in range(1, 13):
                vals = coc_dep.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.4f} kWh/{variable}")
                else:
                    y_vals.append(None)
                    hover.append("")
            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=meses_x, y=y_vals,
                mode="markers",
                name=label,
                marker=dict(color=color, size=9,
                            line=dict(width=1.5, color="white")),
                text=hover,
                hovertemplate="%{text}<extra></extra>",
            ))

        # Outliers con X
        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1])
                y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.4f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out, mode="markers",
                name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out,
                hovertemplate="%{text}<extra></extra>",
            ))

        # LBEn mensual (línea roja)
        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            fig.add_trace(go.Scatter(
                x=meses_x, y=lben_vals,
                mode="lines+markers",
                name=f"LBEn (kWh/{variable})",
                line=dict(color="#E74C3C", width=2.5),
                marker=dict(color="#E74C3C", size=7),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.4f}<extra></extra>",
            ))

        fig.update_layout(**layout)
        self._render(fig)

    def _plot_linea_base_cronologico(self, resultado: dict, titulo_proyecto: str = ""):
        """Fallback cronológico para modelos que no son promedio."""
        fechas_h  = resultado.get("fechas_hist", [])
        consumo_h = resultado.get("consumo_hist", [])
        lb_h      = resultado.get("lb_hist", [])
        ic_sup_h  = resultado.get("ic_sup_hist", [])
        ic_inf_h  = resultado.get("ic_inf_hist", [])
        unidad    = resultado.get("unidad", "")

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Período histórico — {titulo_proyecto}" if titulo_proyecto else "Período histórico",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"] = {"text": "Período"}
        layout["yaxis"]["title"] = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]         = {"l": 70, "r": 20, "t": 70, "b": 100}
        layout["plot_bgcolor"]   = "#FAFAFA"
        layout["legend"]         = {
            "orientation": "h", "yanchor": "top", "y": -0.22,
            "xanchor": "center", "x": 0.5,
        }

        if ic_sup_h and ic_inf_h:
            fig.add_trace(go.Scatter(
                x=list(fechas_h) + list(fechas_h)[::-1],
                y=list(ic_sup_h) + list(ic_inf_h)[::-1],
                fill="toself", fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Intervalo de confianza", hoverinfo="skip",
            ))
        if lb_h:
            fig.add_trace(go.Scatter(
                x=fechas_h, y=lb_h, mode="lines+markers",
                name="Línea base (LBEn)",
                line=dict(color="#E74C3C", width=2.5),
                marker=dict(color="#E74C3C", size=7),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))
        if consumo_h:
            fig.add_trace(go.Scatter(
                x=fechas_h, y=consumo_h, mode="lines+markers",
                name="Consumo histórico",
                line=dict(color="#2E86C1", width=1.8),
                marker=dict(color="#2E86C1", size=7),
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 1b: Seguimiento — reporte vs LBEn ────────────────────────────

    def plot_seguimiento(self, resultado: dict, titulo_proyecto: str = ""):
        """
        Gráfico de seguimiento: muestra el período de reporte (consumo real)
        vs la línea base histórica, con la banda de confianza.
        Es el gráfico que antes estaba en 'Línea base' mostrando el reporte.
        """
        fechas   = resultado.get("fechas", [])
        consumo  = resultado.get("consumo_real", [])
        lb       = resultado.get("linea_base", [])
        ic_sup   = resultado.get("ic_superior", [])
        ic_inf   = resultado.get("ic_inferior", [])
        unidad   = resultado.get("unidad", "")

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Seguimiento energético — {titulo_proyecto}" if titulo_proyecto
                    else "Seguimiento energético",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"] = {"text": "Período de reporte"}
        layout["yaxis"]["title"] = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]         = {"l": 70, "r": 20, "t": 70, "b": 100}
        layout["plot_bgcolor"]   = "#FAFAFA"
        layout["legend"]         = {
            "orientation": "h",
            "yanchor": "top", "y": -0.22,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0",
            "borderwidth": 1,
        }

        # Banda IC
        if ic_sup and ic_inf:
            fig.add_trace(go.Scatter(
                x=list(fechas) + list(fechas)[::-1],
                y=list(ic_sup) + list(ic_inf)[::-1],
                fill="toself",
                fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name="Intervalo de confianza",
                hoverinfo="skip",
            ))

        # LBEn
        if lb:
            fig.add_trace(go.Scatter(
                x=fechas, y=lb,
                mode="lines",
                name="Línea base (LBEn)",
                line=dict(color="#2E86C1", width=2.5, dash="dash"),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

        # Consumo real — color por punto según si está por encima o debajo
        if consumo and lb:
            colores_pts = ["#27AE60" if c <= b else "#E74C3C"
                           for c, b in zip(consumo, lb)]
            fig.add_trace(go.Scatter(
                x=fechas, y=consumo,
                mode="lines+markers",
                name="Consumo real",
                line=dict(color="#E74C3C", width=2),
                marker=dict(color=colores_pts, size=9,
                            line=dict(width=1.5, color="white")),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Consumo: %{{y:,.0f}} {unidad}<extra></extra>"
                ),
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 2: Desviación (barras con colores) ────────────────────────────

    def plot_desviacion(self, resultado: dict):
        fechas   = resultado.get("fechas", [])
        desv_pct = resultado.get("desviacion_pct", [])
        desv_abs = resultado.get("desviacion_abs", [])
        consumo  = resultado.get("consumo_real", [])
        lb       = resultado.get("linea_base", [])
        unidad   = resultado.get("unidad", "")

        VERDE = "#27AE60"
        ROJO  = "#E74C3C"
        colores = [VERDE if v <= 0 else ROJO for v in desv_pct]

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": "Desviación respecto a la línea base",
            "x": 0.5, "xanchor": "center",
            "font": {"size": 15},
        }
        layout["yaxis"]["ticksuffix"] = "%"
        layout["yaxis"]["title"]      = {"text": "Desviación (%)"}
        layout["xaxis"]["title"]      = {"text": "Período"}
        layout["margin"]  = {"l": 70, "r": 30, "t": 60, "b": 60}
        layout["bargap"]  = 0.3
        layout["plot_bgcolor"] = "#FAFAFA"

        # Barra de referencia en 0%
        fig.add_hline(y=0, line_dash="dot",
                      line_color="#95A5A6", line_width=1.5)

        # Barras principales
        c_real = [f"{c:,.0f}" for c in consumo]
        c_lb   = [f"{b:,.0f}" for b in lb]
        c_abs  = [f"{a:+,.0f}" for a in desv_abs]

        fig.add_trace(go.Bar(
            x=fechas, y=desv_pct,
            marker_color=colores,
            marker_line_width=0,
            name="Desviación (%)",
            customdata=list(zip(c_abs, c_real, c_lb)),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Desviación: <b>%{y:+.1f}%</b><br>"
                f"Diferencia: %{{customdata[0]}} {unidad}<br>"
                f"Real: %{{customdata[1]}} {unidad}<br>"
                f"LBEn: %{{customdata[2]}} {unidad}"
                "<extra></extra>"
            ),
            text=[f"{v:+.1f}%" for v in desv_pct],
            textposition="outside",
            textfont=dict(size=11, color=colores),
        ))

        # Leyenda
        fig.add_trace(go.Bar(x=[None], y=[None], name="Ahorro / Mejora",
                             marker_color=VERDE, marker_line_width=0))
        fig.add_trace(go.Bar(x=[None], y=[None], name="Incremento",
                             marker_color=ROJO,  marker_line_width=0))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 3: CUSUM ──────────────────────────────────────────────────────

    def plot_cusum(self, resultado: dict):
        """
        CUSUM con líneas rectas (shape="hv" NO, rectas directas entre puntos),
        segmentos coloreados verde/rojo según si el CUSUM baja o sube,
        puntos grandes en cada período.
        """
        fechas = resultado.get("fechas", [])
        cusum  = resultado.get("cusum",  [])
        unidad = resultado.get("unidad", "")

        if not fechas or not cusum:
            return

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": "Gráfico CUSUM — Acumulado de desviaciones energéticas",
            "x": 0.5, "xanchor": "center",
        }
        layout["yaxis"]["title"] = {"text": f"CUSUM ({unidad})" if unidad else "CUSUM acumulado"}
        layout["xaxis"]["title"] = {"text": "Período"}
        layout["margin"]         = {"l": 80, "r": 30, "t": 70, "b": 60}
        layout["plot_bgcolor"]   = "#FAFAFA"

        # ── Segmentos: una línea recta por tramo, coloreada según dirección ──
        # Verde = CUSUM baja (ahorro acumulado)
        # Rojo  = CUSUM sube (incremento acumulado)
        COLOR_BAJA  = "#27AE60"   # verde fuerte
        COLOR_SUBE  = "#E74C3C"   # rojo fuerte
        COLOR_BAJA_FILL = "rgba(39,174,96,0.10)"
        COLOR_SUBE_FILL = "rgba(231,76,60,0.10)"

        for i in range(1, len(cusum)):
            baja  = cusum[i] <= cusum[i - 1]
            color = COLOR_BAJA if baja else COLOR_SUBE
            fig.add_trace(go.Scatter(
                x=[fechas[i - 1], fechas[i]],
                y=[cusum[i - 1],  cusum[i]],
                mode="lines",
                line=dict(color=color, width=3.5),
                showlegend=False,
                hoverinfo="skip",
            ))

        # ── Área de fondo según signo del CUSUM ──────────────────────────────
        # Rellena entre 0 y el CUSUM para dar sensación de acumulación
        cero = [0] * len(fechas)
        # Área verde donde CUSUM < 0 (ahorro)
        y_verde = [min(c, 0) for c in cusum]
        fig.add_trace(go.Scatter(
            x=list(fechas) + list(fechas)[::-1],
            y=y_verde + cero[::-1],
            fill="toself",
            fillcolor=COLOR_BAJA_FILL,
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ))
        # Área roja donde CUSUM > 0 (exceso)
        y_rojo = [max(c, 0) for c in cusum]
        fig.add_trace(go.Scatter(
            x=list(fechas) + list(fechas)[::-1],
            y=y_rojo + cero[::-1],
            fill="toself",
            fillcolor=COLOR_SUBE_FILL,
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
        ))

        # ── Puntos grandes en cada período ───────────────────────────────────
        marker_colors = []
        for i in range(len(cusum)):
            if i == 0:
                marker_colors.append(COLOR_BAJA if cusum[i] <= 0 else COLOR_SUBE)
            else:
                marker_colors.append(COLOR_BAJA if cusum[i] <= cusum[i-1] else COLOR_SUBE)

        fig.add_trace(go.Scatter(
            x=fechas, y=cusum,
            mode="markers",
            marker=dict(
                color=marker_colors,
                size=12,
                line=dict(width=2, color="white"),
                symbol="circle",
            ),
            name="CUSUM",
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"CUSUM acumulado: %{{y:,.1f}} {unidad}<extra></extra>"
            ),
        ))

        # ── Línea de cero (referencia) ────────────────────────────────────────
        fig.add_hline(y=0,
                      line_dash="dot",
                      line_color="#95A5A6",
                      line_width=1.5,
                      annotation_text="Referencia (0)",
                      annotation_position="bottom right",
                      annotation_font_size=11,
                      annotation_font_color="#95A5A6")

        # ── Leyenda manual ────────────────────────────────────────────────────
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines+markers",
                                  line=dict(color=COLOR_BAJA, width=3),
                                  marker=dict(color=COLOR_BAJA, size=10),
                                  name="Mejora / Ahorro (CUSUM baja)"))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines+markers",
                                  line=dict(color=COLOR_SUBE, width=3),
                                  marker=dict(color=COLOR_SUBE, size=10),
                                  name="Incremento (CUSUM sube)"))

        fig.update_layout(**layout)
        self._render(fig)


    # ── Gráfico ANR: Comparación original vs ajustado ────────────────────────

    def plot_ajuste_no_rutinario(self, resultado: dict):
        """
        Gráfico de auditoría del Ajuste No Rutinario.
        Línea gris = consumo original; línea azul = consumo ajustado.
        Puntos naranjas = meses anómalos corregidos.
        """
        resumen     = resultado.get("resumen_anr", {})
        detalle     = resumen.get("detalle", [])
        fechas_hist = resultado.get("fechas_hist_original", [])
        consumo_orig = resultado.get("consumo_hist_original", [])
        consumo_ajust = resultado.get("consumo_hist", [])
        unidad = resultado.get("unidad", "")

        if not fechas_hist or not consumo_orig:
            return

        # Construir set de fechas anómalas para colorear
        fechas_anom = {r["fecha"] for r in detalle if r.get("ajustado")}

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": "Ajuste No Rutinario — Original vs Ajustado",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": "Período"}
        layout["xaxis"]["tickangle"] = -45
        layout["yaxis"]["title"]     = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]             = {"l": 75, "r": 20, "t": 70, "b": 100}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["legend"]             = {
            "orientation": "h", "yanchor": "top", "y": -0.25,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        fechas_str = [str(f) for f in fechas_hist]

        # Línea original (gris)
        fig.add_trace(go.Scatter(
            x=fechas_str, y=consumo_orig,
            mode="lines+markers",
            name="Consumo original",
            line=dict(color="#95A5A6", width=2, dash="dash"),
            marker=dict(color="#95A5A6", size=6),
            hovertemplate="<b>%{x}</b><br>Original: %{y:,.2f}<extra></extra>",
        ))

        # Línea ajustada (azul)
        fig.add_trace(go.Scatter(
            x=fechas_str, y=consumo_ajust,
            mode="lines+markers",
            name="Consumo ajustado (ANR)",
            line=dict(color="#2E86C1", width=2.5),
            marker=dict(color="#2E86C1", size=6,
                        line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{x}</b><br>Ajustado: %{y:,.2f}<extra></extra>",
        ))

        # Puntos naranjas sobre los meses anómalos (valor ajustado)
        x_anom, y_anom_orig, y_anom_ajust, hover_anom = [], [], [], []
        anom_dict = {r["fecha"]: r for r in detalle if r.get("ajustado")}
        for f_str, c_orig, c_ajust in zip(fechas_str, consumo_orig, consumo_ajust):
            if f_str in anom_dict:
                r = anom_dict[f_str]
                x_anom.append(f_str)
                y_anom_orig.append(c_orig)
                y_anom_ajust.append(c_ajust)
                hover_anom.append(
                    f"<b>{f_str}</b> — {r['motivo']}<br>"
                    f"Original: {r['valor_original']:,.2f}<br>"
                    f"Ajustado: {r['valor_ajustado']:,.2f}<br>"
                    f"Δ = {r['delta_pct']:+.1f}%"
                )

        if x_anom:
            # Flechas: segmentos verticales de orig → ajust
            for i, (x_a, y_o, y_a) in enumerate(zip(x_anom, y_anom_orig, y_anom_ajust)):
                fig.add_shape(
                    type="line",
                    x0=x_a, x1=x_a, y0=y_o, y1=y_a,
                    line=dict(color="#E67E22", width=1.5, dash="dot"),
                )

            # Punto en valor ajustado
            fig.add_trace(go.Scatter(
                x=x_anom, y=y_anom_ajust,
                mode="markers",
                name="Mes anómalo (corregido)",
                marker=dict(color="#E67E22", size=12, symbol="diamond",
                            line=dict(width=2, color="white")),
                text=hover_anom,
                hovertemplate="%{text}<extra></extra>",
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 1-nuevo: Scatter consumos por año + LBEn promedio + límites ±10% ──
    # Aplica a Modelos 1 (promedio) y 2 (cociente)

    def plot_scatter_lben_limites(self, resultado: dict, titulo_proyecto: str = ""):
        """
        Scatter de consumos históricos agrupados por mes (eje X = 12 meses).
        Superpone:
          - LBEn mensual (línea azul sólida)
          - Límite +10% sobre LBEn (línea naranja punteada)
          - Límite -10% sobre LBEn (línea verde punteada)
        Un punto por cada año-mes disponible en el histórico.
        """
        unidad  = resultado.get("unidad", "")
        params  = resultado.get("modelo_params", {})
        modelo_id = params.get("modelo_id", resultado.get("modelo_id", "promedio"))

        # Intentar datos_por_mes (Modelo 1) o coc_depurados (Modelo 2)
        datos_por_mes = params.get("datos_por_mes", {})
        coc_dep       = params.get("coc_depurados", {})
        lben_mensual  = params.get("lben_mensual", {})
        años_por_mes  = params.get("años_por_mes", {})
        outliers_mes  = params.get("outliers", {})
        es_cociente   = not datos_por_mes or not any(datos_por_mes.values())

        fuente = coc_dep if es_cociente else datos_por_mes
        if not fuente or not any(fuente.values()):
            return

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]
        PALETA  = ["#2E86C1","#E67E22","#27AE60","#8E44AD",
                   "#E74C3C","#1ABC9C","#F39C12","#2C3E50"]

        # Años únicos
        años_vistos = sorted({
            a for mes in range(1,13)
            for a in años_por_mes.get(mes, [])
            if a is not None
        })
        def _label(idx):
            return str(años_vistos[idx]) if idx < len(años_vistos) else f"Año {idx+1}"

        n_years = max((len(v) for v in fuente.values() if v), default=0)

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": (f"Scatter LBEn ±10% — {titulo_proyecto}"
                     if titulo_proyecto else "Scatter consumos por mes — LBEn ±10%"),
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": "Mes"}
        layout["xaxis"]["tickangle"] = 0
        y_label = (f"Cociente (kWh/{params.get('variable','variable')})"
                   if es_cociente else
                   (f"Consumo ({unidad})" if unidad else "Consumo"))
        layout["yaxis"]["title"]  = {"text": y_label}
        layout["margin"]          = {"l": 75, "r": 20, "t": 70, "b": 90}
        layout["plot_bgcolor"]    = "#FAFAFA"
        layout["legend"]          = {
            "orientation": "h", "yanchor": "top", "y": -0.22,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # ── Outliers con X ────────────────────────────────────────────────────
        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1])
                y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.2f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out, mode="markers",
                name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out,
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── Puntos por año ────────────────────────────────────────────────────
        for yr_idx in range(n_years):
            y_vals, hover = [], []
            label = _label(yr_idx)
            for mes in range(1, 13):
                vals = fuente.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.2f}")
                else:
                    y_vals.append(None)
                    hover.append("")
            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=y_vals, mode="markers",
                name=label,
                marker=dict(color=color, size=9, line=dict(width=1.5, color="white")),
                text=hover,
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── LBEn mensual ──────────────────────────────────────────────────────
        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            lben_clean = [v if v is not None else None for v in lben_vals]

            # Límite +10%
            sup10 = [v * 1.10 if v is not None else None for v in lben_clean]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=sup10, mode="lines",
                name="LBEn +10%",
                line=dict(color="#E67E22", width=1.8, dash="dot"),
                hovertemplate="<b>%{x}</b><br>+10%%: %{y:,.2f}<extra></extra>",
            ))

            # Límite -10%
            inf10 = [v * 0.90 if v is not None else None for v in lben_clean]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=inf10, mode="lines",
                name="LBEn −10%",
                line=dict(color="#27AE60", width=1.8, dash="dot"),
                fill="tonexty",
                fillcolor="rgba(39,174,96,0.06)",
                hovertemplate="<b>%{x}</b><br>-10%%: %{y:,.2f}<extra></extra>",
            ))

            # LBEn principal
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=lben_clean, mode="lines+markers",
                name="LBEn (promedio mes)",
                line=dict(color="#1B4F72", width=2.8),
                marker=dict(color="#1B4F72", size=8,
                            line=dict(width=1.5, color="white")),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 2-nuevo: Correlación consumo vs variable relevante ────────────
    # Aplica a Modelos 2 (cociente) y 3 (regresión)

    def plot_correlacion_variable(self, resultado: dict):
        """
        Scatter X = variable independiente principal, Y = consumo real.
        Muestra la línea del modelo ajustado (regresión o cociente) encima.
        Incluye anotación con ecuación y R².
        """
        params   = resultado.get("modelo_params", {})
        unidad   = resultado.get("unidad", "")
        x_disp   = resultado.get("x_dispersion", [])
        x_label  = resultado.get("x_label", "Variable")

        # Usar datos históricos para mostrar el ajuste del modelo
        consumo_h = resultado.get("consumo_hist", [])
        fechas_h  = resultado.get("fechas_hist", [])

        if not x_disp or not consumo_h:
            return

        # Reconstruir x_disp para el histórico (puede ser del reporte si hay reporte)
        # Intentamos recuperar x desde modelo_params
        x_hist = params.get("x_hist", x_disp)
        if len(x_hist) != len(consumo_h):
            x_hist = x_disp[:len(consumo_h)]

        # Línea del modelo: generar puntos suavizados
        import numpy as np
        x_arr = [float(v) for v in x_hist if v is not None]
        y_arr = consumo_h[:len(x_arr)]

        if len(x_arr) < 2:
            return

        x_min, x_max = min(x_arr), max(x_arr)
        x_line = list(np.linspace(x_min, x_max, 60))

        # Calcular línea según tipo de modelo
        coefs = params.get("coeficientes", {})
        indice = params.get("indice", None)

        if coefs and len(coefs) >= 2:
            # Regresión lineal simple o múltiple (solo 1ª variable en scatter)
            vals = list(coefs.values())
            intercepto = vals[0]
            pendiente  = vals[1]
            y_line = [pendiente * xi + intercepto for xi in x_line]
            r2 = params.get("r2", 0)
            ecuacion = _construir_ecuacion(params, x_label, r2)
        elif indice is not None:
            # Cociente: y = indice * x
            y_line = [indice * xi for xi in x_line]
            r2 = params.get("r2", 0)
            ecuacion = f"y = {indice:.4f} × x<br>R² = {r2:.3f}"
        else:
            return

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Correlación: Consumo vs {x_label}",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": x_label}
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["title"]     = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]             = {"l": 75, "r": 20, "t": 70, "b": 80}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["hovermode"]          = "closest"
        layout["legend"]             = {
            "orientation": "h", "yanchor": "top", "y": -0.18,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # Puntos reales
        hover_pts = [
            f"{str(f)}<br>{x_label}: {xi:,.2f}<br>Consumo: {yi:,.0f} {unidad}"
            for f, xi, yi in zip(fechas_h, x_arr, y_arr)
        ]
        fig.add_trace(go.Scatter(
            x=x_arr, y=y_arr, mode="markers",
            name="Datos históricos",
            marker=dict(color="#2E86C1", size=9,
                        line=dict(width=1.5, color="white")),
            text=hover_pts,
            hovertemplate="%{text}<extra></extra>",
        ))

        # Línea del modelo
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            name="Modelo ajustado",
            line=dict(color="#E74C3C", width=2.5),
            hovertemplate=f"{x_label}: %{{x:,.2f}}<br>Modelo: %{{y:,.0f}} {unidad}<extra></extra>",
        ))

        # Anotación ecuación + R²
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.02, y=0.97, xanchor="left", yanchor="top",
            text=ecuacion,
            showarrow=False,
            bgcolor="rgba(255,255,255,0.88)",
            bordercolor="#D5D8DC", borderwidth=1,
            borderpad=6,
            font=dict(size=12, color=COLORS.text_primary, family=FONTS.family),
        )

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 3-nuevo: LBEn vs línea meta de mejores desempeños ────────────

    def plot_lben_vs_meta(self, resultado: dict, titulo_proyecto: str = ""):
        """
        Gráfico de barras horizontales por mes mostrando:
          - LBEn mensual (azul)
          - Meta de mejor desempeño (verde): el percentil 10 de los datos históricos
            depurados por mes (o la mejor observación disponible).
        Eje X = valor de consumo/índice. Eje Y = meses.
        """
        params   = resultado.get("modelo_params", {})
        unidad   = resultado.get("unidad", "")
        lben     = params.get("lben_mensual", {})

        # Datos depurados para calcular la meta (mejor desempeño)
        datos_dep  = params.get("datos_depurados", {})   # Modelo 1
        coc_dep    = params.get("coc_depurados",   {})   # Modelo 2
        fuente_dep = datos_dep if any(datos_dep.values()) else coc_dep

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]

        lben_vals = []
        meta_vals = []
        meses_lbl = []

        import numpy as np
        for mes in range(1, 13):
            lb = lben.get(mes)
            if lb is None:
                continue
            vals_dep = fuente_dep.get(mes, [])
            if vals_dep:
                # Mejor desempeño = percentil 10 (consumo más bajo depurado)
                meta = float(np.percentile(vals_dep, 10))
            else:
                meta = lb * 0.90   # fallback: 10% mejor que LBEn

            lben_vals.append(lb)
            meta_vals.append(meta)
            meses_lbl.append(NOMBRES[mes-1])

        if not lben_vals:
            return

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": (f"LBEn vs Meta de mejores desempeños — {titulo_proyecto}"
                     if titulo_proyecto else "LBEn vs Meta de mejores desempeños"),
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": f"Consumo ({unidad})" if unidad else "Valor"}
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["title"]     = {"text": "Mes"}
        layout["yaxis"]["autorange"] = "reversed"   # Ene arriba
        layout["margin"]             = {"l": 60, "r": 20, "t": 70, "b": 70}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["barmode"]            = "group"
        layout["hovermode"]          = "y unified"
        layout["legend"]             = {
            "orientation": "h", "yanchor": "top", "y": -0.15,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # LBEn
        fig.add_trace(go.Bar(
            y=meses_lbl, x=lben_vals,
            name="LBEn mensual",
            orientation="h",
            marker=dict(color="#1B4F72",
                        line=dict(color="#154360", width=0.8)),
            hovertemplate="<b>%{y}</b><br>LBEn: %{x:,.2f}<extra></extra>",
            text=[f"{v:,.1f}" for v in lben_vals],
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="white", size=10),
        ))

        # Meta (mejor desempeño)
        fig.add_trace(go.Bar(
            y=meses_lbl, x=meta_vals,
            name="Meta (mejor desempeño — percentil 10)",
            orientation="h",
            marker=dict(color="#1E8449",
                        line=dict(color="#186A3B", width=0.8)),
            hovertemplate="<b>%{y}</b><br>Meta: %{x:,.2f}<extra></extra>",
            text=[f"{v:,.1f}" for v in meta_vals],
            textposition="inside",
            insidetextanchor="end",
            textfont=dict(color="white", size=10),
        ))

        # Diferencia % como anotaciones en el margen derecho
        x_max = max(max(lben_vals), max(meta_vals)) * 1.02
        for i, (lb, mt, mes) in enumerate(zip(lben_vals, meta_vals, meses_lbl)):
            diff_pct = (mt - lb) / lb * 100 if lb != 0 else 0
            color_txt = "#27AE60" if diff_pct <= 0 else "#E74C3C"
            fig.add_annotation(
                x=x_max, y=mes,
                text=f"{diff_pct:+.1f}%",
                showarrow=False,
                font=dict(size=10, color=color_txt, family=FONTS.family),
                xanchor="left",
            )

        layout["xaxis"]["range"] = [0, x_max * 1.12]
        fig.update_layout(**layout)
        self._render(fig)

    # plot_dispersion eliminado — ya no se usa


# ── Helper: construye la cadena de la ecuación ────────────────────────────────

def _construir_ecuacion(params: dict, x_label: str, r2: float) -> str:
    """
    Devuelve un string con la ecuación del modelo y el R² para mostrarlo
    como anotación en el gráfico (igual al cuadro de la imagen de referencia).
    """
    coefs = params.get("coeficientes", {})
    if not coefs:
        # Modelo cociente: índice
        indice = params.get("indice")
        if indice:
            return f"y = {indice:.4f} × x<br>R² = {r2:.3f}"
        return f"R² = {r2:.3f}"

    # Regresión lineal
    nombres = list(coefs.keys())
    valores = list(coefs.values())

    if len(nombres) == 1:
        # Solo intercepto — promedio
        return f"ȳ = {valores[0]:,.1f}<br>R² = {r2:.3f}"

    if len(nombres) == 2:
        # Simple: intercepto + 1 variable
        intercepto = valores[0]
        pendiente  = valores[1]
        signo      = "+" if intercepto >= 0 else "−"
        return (
            f"y = {pendiente:.4f}x {signo} {abs(intercepto):,.1f}<br>"
            f"R² = {r2:.3f}"
        )

    # Múltiple: lista de términos
    terminos = []
    for nombre, val in list(coefs.items())[1:]:
        terminos.append(f"{val:.4f}·{nombre}")
    intercepto = valores[0]
    signo = "+" if intercepto >= 0 else "−"
    ec = "y = " + " + ".join(terminos) + f" {signo} {abs(intercepto):,.1f}"
    return f"{ec}<br>R² = {r2:.3f}"