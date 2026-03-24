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
