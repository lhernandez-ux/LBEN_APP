"""
ui/components/chart_widget.py  — fragmento relevante
=====================================================
Sólo se muestra el método plot_correlacion_variable actualizado y el
helper _construir_ecuacion. Los demás métodos de ChartWidget no cambian.

CAMBIOS respecto a la versión anterior:
  • plot_correlacion_variable ahora muestra:
      - Puntos azules  → consumo > LBEn  (sobre la línea base)
      - Puntos verdes  → consumo < LBEn  (mejores desempeños, usados para línea meta)
      - Línea roja     → LBEn (modelo ajustado, igual que antes)
      - Línea verde punteada → Línea meta de mejores desempeños (Anexo 3 resolución)
      - Cuadro con ecuación LBEn + ecuación meta + R² de cada una
      - Área sombreada verde entre LBEn y línea meta = potencial de ahorro
"""

import io
import numpy as np
import customtkinter as ctk
from PIL import Image
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ui.theme import COLORS, FONTS, get_chart_layout
import re


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

    def _render(self, fig: go.Figure, width: int = 1150):
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

    # ── Gráfico 1: Línea base ─────────────────────────────────────────────────
    # (sin cambios — se mantiene igual que antes)

    def plot_linea_base(self, resultado: dict, titulo_proyecto: str = ""):
        unidad = resultado.get("unidad", "")
        params = resultado.get("modelo_params", {})
        datos_por_mes   = params.get("datos_por_mes",  {})
        datos_depurados = params.get("datos_depurados", {})
        outliers_mes    = params.get("outliers", {})
        lben_mensual    = params.get("lben_mensual", {})
        ic_mensual      = params.get("ic_mensual", {})

        if not datos_por_mes or not any(datos_por_mes.values()):
            coc_dep = params.get("coc_depurados", {})
            if coc_dep and any(coc_dep.values()):
                self._plot_linea_base_cociente(resultado, titulo_proyecto)
            else:
                self._plot_linea_base_cronologico(resultado, titulo_proyecto)
            return

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]
        meses_x = NOMBRES

        n_years = max((len(v) for v in datos_por_mes.values() if v), default=0)

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
        layout["xaxis"]["title"]     = {"text": "Mes"}
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["title"]     = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"]             = {"l": 70, "r": 20, "t": 70, "b": 80}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["legend"]             = {
            "orientation": "h", "yanchor": "top", "y": -0.18,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        ic_sup_vals = [ic_mensual.get(m, (None,None))[1] for m in range(1,13)]
        ic_inf_vals = [ic_mensual.get(m, (None,None))[0] for m in range(1,13)]
        if any(v is not None for v in ic_sup_vals):
            ic_sup_clean = [v if v is not None else 0 for v in ic_sup_vals]
            ic_inf_clean = [v if v is not None else 0 for v in ic_inf_vals]
            fig.add_trace(go.Scatter(
                x=meses_x + meses_x[::-1],
                y=ic_sup_clean + ic_inf_clean[::-1],
                fill="toself", fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Intervalo de confianza", hoverinfo="skip", showlegend=True,
            ))

        outlier_set = set()
        for lst in outliers_mes.values():
            for v in lst:
                outlier_set.add(round(float(v), 4))

        años_por_mes = params.get("años_por_mes", {})
        años_vistos = []
        for mes in range(1, 13):
            for a in años_por_mes.get(mes, []):
                if a is not None and a not in años_vistos:
                    años_vistos.append(a)
        años_vistos.sort()

        def _label_año(yr_idx):
            if yr_idx < len(años_vistos):
                return str(años_vistos[yr_idx])
            return f"Año {yr_idx + 1}"

        for yr_idx in range(n_years):
            y_vals, hover = [], []
            label = _label_año(yr_idx)
            for mes in range(1, 13):
                vals = datos_por_mes.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.0f} {unidad}")
                else:
                    y_vals.append(None); hover.append("")

            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=meses_x, y=y_vals, mode="markers", name=label,
                marker=dict(color=color, size=9, line=dict(width=1.5, color="white")),
                text=hover, hovertemplate="%{text}<extra></extra>",
            ))

        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1]); y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.0f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out, mode="markers", name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out, hovertemplate="%{text}<extra></extra>",
            ))

        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            fig.add_trace(go.Scatter(
                x=meses_x, y=lben_vals, mode="lines+markers",
                name="LBEn (promedio mes)",
                line=dict(color="#E74C3C", width=2.5),
                marker=dict(color="#E74C3C", size=7),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

            meta_vals = []
            for mes in range(1, 13):
                lb = lben_mensual.get(mes)
                if lb is None:
                    meta_vals.append(None); continue
                vals_dep = datos_depurados.get(mes, [])
                valores_debajo = [v for v in vals_dep if v < lb]
                meta_vals.append(float(np.mean(valores_debajo)) if valores_debajo else lb * 0.90)
            if any(v is not None for v in meta_vals):
                fig.add_trace(go.Scatter(
                    x=meses_x, y=meta_vals, mode="lines+markers", name="Línea meta",
                    line=dict(color="#106B28", width=2.0, dash="dash"),
                    marker=dict(color="#0EA818", size=7, line=dict(width=1.5, color="white")),
                    hovertemplate="<b>%{x}</b><br>Meta: %{y:,.2f}<extra></extra>",
                ))

        fig.update_layout(**layout)
        self._render(fig)

    def _plot_linea_base_cociente(self, resultado: dict, titulo_proyecto: str = ""):
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
            "orientation": "h", "yanchor": "top", "y": -0.18,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        ic_sup_vals = [ic_mensual.get(m, (None,None))[1] for m in range(1,13)]
        ic_inf_vals = [ic_mensual.get(m, (None,None))[0] for m in range(1,13)]
        if any(v is not None for v in ic_sup_vals):
            ic_sup_c = [v if v is not None else 0 for v in ic_sup_vals]
            ic_inf_c = [v if v is not None else 0 for v in ic_inf_vals]
            fig.add_trace(go.Scatter(
                x=meses_x + meses_x[::-1], y=ic_sup_c + ic_inf_c[::-1],
                fill="toself", fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                name="Intervalo de confianza", hoverinfo="skip", showlegend=True,
            ))

        años_vistos = sorted({
            a for mes in range(1,13) for a in años_por_mes.get(mes, []) if a is not None
        })
        def _label_año(idx):
            return str(años_vistos[idx]) if idx < len(años_vistos) else f"Año {idx+1}"

        for yr_idx in range(n_years):
            y_vals, hover = [], []
            label = _label_año(yr_idx)
            for mes in range(1, 13):
                vals = coc_dep.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.4f} kWh/{variable}")
                else:
                    y_vals.append(None); hover.append("")
            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=meses_x, y=y_vals, mode="markers", name=label,
                marker=dict(color=color, size=9, line=dict(width=1.5, color="white")),
                text=hover, hovertemplate="%{text}<extra></extra>",
            ))

        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1]); y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.4f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out, mode="markers", name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out, hovertemplate="%{text}<extra></extra>",
            ))

        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            fig.add_trace(go.Scatter(
                x=meses_x, y=lben_vals, mode="lines+markers",
                name=f"LBEn (kWh/{variable})",
                line=dict(color="#E74C3C", width=2.5),
                marker=dict(color="#E74C3C", size=7),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.4f}<extra></extra>",
            ))

            meta_vals = []
            for mes in range(1, 13):
                lb = lben_mensual.get(mes)
                if lb is None:
                    meta_vals.append(None); continue
                vals_dep = coc_dep.get(mes, [])
                valores_debajo = [v for v in vals_dep if v < lb]
                meta_vals.append(float(np.mean(valores_debajo)) if valores_debajo else lb * 0.90)
            if any(v is not None for v in meta_vals):
                fig.add_trace(go.Scatter(
                    x=meses_x, y=meta_vals, mode="lines+markers", name="Línea meta ",
                    line=dict(color="#106B28", width=2.0, dash="dash"),
                    marker=dict(color="#0EA818", size=7, line=dict(width=1.5, color="white")),
                    hovertemplate="<b>%{x}</b><br>Meta: %{y:,.4f}<extra></extra>",
                ))

        fig.update_layout(**layout)
        self._render(fig)

    def _plot_linea_base_cronologico(self, resultado: dict, titulo_proyecto: str = ""):
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

    # ── Gráfico 1b: Seguimiento ───────────────────────────────────────────────

    def plot_seguimiento(self, resultado: dict, titulo_proyecto: str = ""):
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
            "orientation": "h", "yanchor": "top", "y": -0.22,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        if ic_sup and ic_inf:
            fig.add_trace(go.Scatter(
                x=list(fechas) + list(fechas)[::-1],
                y=list(ic_sup) + list(ic_inf)[::-1],
                fill="toself", fillcolor="rgba(46,134,193,0.10)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=True, name="Intervalo de confianza", hoverinfo="skip",
            ))

        if lb:
            fig.add_trace(go.Scatter(
                x=fechas, y=lb, mode="lines",
                name="Línea base (LBEn)",
                line=dict(color="#2E86C1", width=2.5, dash="dash"),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

        if consumo and lb:
            colores_pts = ["#27AE60" if c <= b else "#E74C3C"
                           for c, b in zip(consumo, lb)]
            fig.add_trace(go.Scatter(
                x=fechas, y=consumo, mode="lines+markers",
                name="Consumo real",
                line=dict(color="#E74C3C", width=2),
                marker=dict(color=colores_pts, size=9, line=dict(width=1.5, color="white")),
                hovertemplate=(
                    "<b>%{x}</b><br>"
                    f"Consumo: %{{y:,.0f}} {unidad}<extra></extra>"
                ),
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 2: Desviación ─────────────────────────────────────────────────

    def plot_desviacion(self, resultado: dict):
        fechas   = resultado.get("fechas", [])
        desv_pct = resultado.get("desviacion_pct", [])
        desv_abs = resultado.get("desviacion_abs", [])
        consumo  = resultado.get("consumo_real", [])
        lb       = resultado.get("linea_base", [])
        unidad   = resultado.get("unidad", "")

        VERDE = "#27AE60"; ROJO = "#E74C3C"
        colores = [VERDE if v <= 0 else ROJO for v in desv_pct]

        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": "Desviación respecto a la línea base",
            "x": 0.5, "xanchor": "center", "font": {"size": 15},
        }
        layout["yaxis"]["ticksuffix"] = "%"
        layout["yaxis"]["title"]      = {"text": "Desviación (%)"}
        layout["xaxis"]["title"]      = {"text": "Período"}
        layout["margin"]  = {"l": 70, "r": 30, "t": 60, "b": 60}
        layout["bargap"]  = 0.3
        layout["plot_bgcolor"] = "#FAFAFA"

        fig.add_hline(y=0, line_dash="dot", line_color="#95A5A6", line_width=1.5)

        c_real = [f"{c:,.0f}" for c in consumo]
        c_lb   = [f"{b:,.0f}" for b in lb]
        c_abs  = [f"{a:+,.0f}" for a in desv_abs]

        fig.add_trace(go.Bar(
            x=fechas, y=desv_pct, marker_color=colores, marker_line_width=0,
            name="Desviación (%)",
            customdata=list(zip(c_abs, c_real, c_lb)),
            hovertemplate=(
                "<b>%{x}</b><br>Desviación: <b>%{y:+.1f}%</b><br>"
                f"Diferencia: %{{customdata[0]}} {unidad}<br>"
                f"Real: %{{customdata[1]}} {unidad}<br>"
                f"LBEn: %{{customdata[2]}} {unidad}<extra></extra>"
            ),
            text=[f"{v:+.1f}%" for v in desv_pct],
            textposition="outside",
            textfont=dict(size=11, color=colores),
        ))

        fig.add_trace(go.Bar(x=[None], y=[None], name="Ahorro / Mejora",
                             marker_color=VERDE, marker_line_width=0))
        fig.add_trace(go.Bar(x=[None], y=[None], name="Incremento",
                             marker_color=ROJO,  marker_line_width=0))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico 3: CUSUM ──────────────────────────────────────────────────────

    def plot_cusum(self, resultado: dict):
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

        COLOR_BAJA  = "#27AE60"; COLOR_SUBE  = "#E74C3C"
        COLOR_BAJA_FILL = "rgba(39,174,96,0.10)"; COLOR_SUBE_FILL = "rgba(231,76,60,0.10)"

        for i in range(1, len(cusum)):
            baja  = cusum[i] <= cusum[i - 1]
            color = COLOR_BAJA if baja else COLOR_SUBE
            fig.add_trace(go.Scatter(
                x=[fechas[i - 1], fechas[i]], y=[cusum[i - 1], cusum[i]],
                mode="lines", line=dict(color=color, width=3.5),
                showlegend=False, hoverinfo="skip",
            ))

        cero = [0] * len(fechas)
        y_verde = [min(c, 0) for c in cusum]
        fig.add_trace(go.Scatter(
            x=list(fechas) + list(fechas)[::-1], y=y_verde + cero[::-1],
            fill="toself", fillcolor=COLOR_BAJA_FILL,
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
        ))
        y_rojo = [max(c, 0) for c in cusum]
        fig.add_trace(go.Scatter(
            x=list(fechas) + list(fechas)[::-1], y=y_rojo + cero[::-1],
            fill="toself", fillcolor=COLOR_SUBE_FILL,
            line=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo="skip",
        ))

        marker_colors = []
        for i in range(len(cusum)):
            if i == 0:
                marker_colors.append(COLOR_BAJA if cusum[i] <= 0 else COLOR_SUBE)
            else:
                marker_colors.append(COLOR_BAJA if cusum[i] <= cusum[i-1] else COLOR_SUBE)

        fig.add_trace(go.Scatter(
            x=fechas, y=cusum, mode="markers",
            marker=dict(color=marker_colors, size=12,
                        line=dict(width=2, color="white"), symbol="circle"),
            name="CUSUM",
            hovertemplate=(
                "<b>%{x}</b><br>"
                f"CUSUM acumulado: %{{y:,.1f}} {unidad}<extra></extra>"
            ),
        ))

        fig.add_hline(y=0, line_dash="dot", line_color="#95A5A6", line_width=1.5,
                      annotation_text="Referencia (0)", annotation_position="bottom right",
                      annotation_font_size=11, annotation_font_color="#95A5A6")

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

    # ── Gráfico ANR ───────────────────────────────────────────────────────────

    def plot_ajuste_no_rutinario(self, resultado: dict):
        resumen      = resultado.get("resumen_anr", {})
        detalle      = resumen.get("detalle", [])
        fechas_hist  = resultado.get("fechas_hist_original", [])
        consumo_orig = resultado.get("consumo_hist_original", [])
        consumo_ajust = resultado.get("consumo_hist", [])
        unidad = resultado.get("unidad", "")

        if not fechas_hist or not consumo_orig:
            return

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
        fig.add_trace(go.Scatter(
            x=fechas_str, y=consumo_orig, mode="lines+markers",
            name="Consumo original",
            line=dict(color="#95A5A6", width=2, dash="dash"),
            marker=dict(color="#95A5A6", size=6),
            hovertemplate="<b>%{x}</b><br>Original: %{y:,.2f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=fechas_str, y=consumo_ajust, mode="lines+markers",
            name="Consumo ajustado (ANR)",
            line=dict(color="#2E86C1", width=2.5),
            marker=dict(color="#2E86C1", size=6, line=dict(width=1.5, color="white")),
            hovertemplate="<b>%{x}</b><br>Ajustado: %{y:,.2f}<extra></extra>",
        ))

        x_anom, y_anom_orig, y_anom_ajust, hover_anom = [], [], [], []
        anom_dict = {r["fecha"]: r for r in detalle if r.get("ajustado")}
        for f_str, c_orig, c_ajust in zip(fechas_str, consumo_orig, consumo_ajust):
            if f_str in anom_dict:
                r = anom_dict[f_str]
                x_anom.append(f_str); y_anom_orig.append(c_orig); y_anom_ajust.append(c_ajust)
                hover_anom.append(
                    f"<b>{f_str}</b> — {r['motivo']}<br>"
                    f"Original: {r['valor_original']:,.2f}<br>"
                    f"Ajustado: {r['valor_ajustado']:,.2f}<br>"
                    f"Δ = {r['delta_pct']:+.1f}%"
                )

        if x_anom:
            for x_a, y_o, y_a in zip(x_anom, y_anom_orig, y_anom_ajust):
                fig.add_shape(
                    type="line", x0=x_a, x1=x_a, y0=y_o, y1=y_a,
                    line=dict(color="#E67E22", width=1.5, dash="dot"),
                )
            fig.add_trace(go.Scatter(
                x=x_anom, y=y_anom_ajust, mode="markers",
                name="Mes anómalo (corregido)",
                marker=dict(color="#E67E22", size=12, symbol="diamond",
                            line=dict(width=2, color="white")),
                text=hover_anom, hovertemplate="%{text}<extra></extra>",
            ))

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico scatter LBEn ±10% ─────────────────────────────────────────────

    def plot_scatter_lben_limites(self, resultado: dict, titulo_proyecto: str = ""):
        unidad    = resultado.get("unidad", "")
        params    = resultado.get("modelo_params", {})
        modelo_id = params.get("modelo_id", resultado.get("modelo_id", "promedio"))

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

        años_vistos = sorted({
            a for mes in range(1,13) for a in años_por_mes.get(mes, []) if a is not None
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
                   if es_cociente else (f"Consumo ({unidad})" if unidad else "Consumo"))
        layout["yaxis"]["title"]  = {"text": y_label}
        layout["margin"]          = {"l": 75, "r": 20, "t": 70, "b": 90}
        layout["plot_bgcolor"]    = "#FAFAFA"
        layout["legend"]          = {
            "orientation": "h", "yanchor": "top", "y": -0.22,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        x_out, y_out, lbl_out = [], [], []
        for mes in range(1, 13):
            for v in outliers_mes.get(mes, []):
                x_out.append(NOMBRES[mes-1]); y_out.append(v)
                lbl_out.append(f"{NOMBRES[mes-1]}: {v:,.2f} — outlier eliminado")
        if x_out:
            fig.add_trace(go.Scatter(
                x=x_out, y=y_out, mode="markers", name="Outlier eliminado",
                marker=dict(color="#E74C3C", size=10, symbol="x",
                            line=dict(width=2.5, color="#E74C3C")),
                text=lbl_out, hovertemplate="%{text}<extra></extra>",
            ))

        for yr_idx in range(n_years):
            y_vals, hover = [], []
            label = _label(yr_idx)
            for mes in range(1, 13):
                vals = fuente.get(mes, [])
                if yr_idx < len(vals):
                    y_vals.append(vals[yr_idx])
                    hover.append(f"{NOMBRES[mes-1]} {label}: {vals[yr_idx]:,.2f}")
                else:
                    y_vals.append(None); hover.append("")
            color = PALETA[yr_idx % len(PALETA)]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=y_vals, mode="markers", name=label,
                marker=dict(color=color, size=9, line=dict(width=1.5, color="white")),
                text=hover, hovertemplate="%{text}<extra></extra>",
            ))

        lben_vals = [lben_mensual.get(m) for m in range(1, 13)]
        if any(v is not None for v in lben_vals):
            lben_clean = [v if v is not None else None for v in lben_vals]
            sup10 = [v * 1.10 if v is not None else None for v in lben_clean]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=sup10, mode="lines", name="LBEn +10%",
                line=dict(color="#E67E22", width=1.8, dash="dot"),
                hovertemplate="<b>%{x}</b><br>+10%%: %{y:,.2f}<extra></extra>",
            ))
            inf10 = [v * 0.90 if v is not None else None for v in lben_clean]
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=inf10, mode="lines", name="LBEn −10%",
                line=dict(color="#27AE60", width=1.8, dash="dot"),
                fill="tonexty", fillcolor="rgba(39,174,96,0.06)",
                hovertemplate="<b>%{x}</b><br>-10%%: %{y:,.2f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=NOMBRES, y=lben_clean, mode="lines+markers",
                name="LBEn (promedio mes)",
                line=dict(color="#1B4F72", width=2.8),
                marker=dict(color="#1B4F72", size=8, line=dict(width=1.5, color="white")),
                hovertemplate="<b>%{x}</b><br>LBEn: %{y:,.2f}<extra></extra>",
            ))

            meta_vals_scatter = []
            for mes in range(1, 13):
                lb = lben_mensual.get(mes)
                if lb is None:
                    meta_vals_scatter.append(None); continue
                vals_dep = fuente.get(mes, [])
                valores_debajo = [v for v in vals_dep if v < lb]
                meta_vals_scatter.append(float(np.mean(valores_debajo)) if valores_debajo else lb * 0.90)
            if any(v is not None for v in meta_vals_scatter):
                fig.add_trace(go.Scatter(
                    x=NOMBRES, y=meta_vals_scatter, mode="lines+markers", name="Línea meta",
                    line=dict(color="#106B28", width=2.0, dash="dash"),
                    marker=dict(color="#0EA818", size=8, line=dict(width=1.5, color="white")),
                    hovertemplate="<b>%{x}</b><br>Meta: %{y:,.2f}<extra></extra>",
                ))

        fig.update_layout(**layout)
        self._render(fig)

    # ══════════════════════════════════════════════════════════════════════════
    # Gráfico de correlación — MODELO ESTADÍSTICO (Regresión)
    # Actualizado según Resolución UPME 16/2024 Anexo 3:
    #   - Puntos azules  → consumo > LBEn
    #   - Puntos verdes  → consumo < LBEn (mejores desempeños)
    #   - Línea roja     → LBEn (modelo ajustado)
    #   - Línea verde punteada → Línea meta de mejores desempeños
    #   - Área sombreada entre LBEn y línea meta
    # ══════════════════════════════════════════════════════════════════════════

    def plot_correlacion_variable(self, resultado: dict):
        """
        Scatter X = variable independiente principal, Y = consumo real del histórico.

        Puntos clasificados:
          - Verde  (▼ mejor desempeño): consumo_real < LBEn → usados para línea meta
          - Azul   (▲ sobre LBEn):     consumo_real ≥ LBEn

        Líneas:
          - Roja continua       → LBEn (modelo ajustado)
          - Verde punteada      → Línea meta (regresión de mejores desempeños)
          - Área sombreada verde → potencial de ahorro entre LBEn y línea meta
        """
        params    = resultado.get("modelo_params", {})
        unidad    = resultado.get("unidad", "")
        x_label   = resultado.get("x_label", "Variable")
        consumo_h = resultado.get("consumo_hist", [])
        fechas_h  = resultado.get("fechas_hist", [])

        if not consumo_h:
            return

        x_hist = params.get("x_hist", [])
        if not x_hist:
            x_hist = resultado.get("x_dispersion", [])
        if len(x_hist) != len(consumo_h):
            x_hist = x_hist[:len(consumo_h)]
        if not x_hist or len(x_hist) != len(consumo_h):
            return

        # ── Recuperar puntos clasificados desde params (si están disponibles) ─
        puntos_clasificados = params.get("puntos_mejor_desempeno", [])

        # Si no vienen pre-clasificados, clasificar ahora con lb_hist
        lb_hist = resultado.get("lb_hist", [])
        if not puntos_clasificados and lb_hist and len(lb_hist) == len(consumo_h):
            puntos_clasificados = [
                {
                    "x":        float(xi),
                    "y_real":   float(yi),
                    "y_lben":   float(lb),
                    "es_mejor": float(yi) < float(lb),
                    "periodo":  str(fi) if fi else str(i),
                }
                for i, (xi, yi, lb, fi) in enumerate(
                    zip(x_hist, consumo_h, lb_hist, fechas_h)
                )
            ]
        elif not puntos_clasificados:
            # Fallback: todos sin clasificar
            puntos_clasificados = [
                {
                    "x": float(xi), "y_real": float(yi),
                    "y_lben": None, "es_mejor": False,
                    "periodo": str(fi) if fi else str(i),
                }
                for i, (xi, yi, fi) in enumerate(zip(x_hist, consumo_h, fechas_h))
            ]

        # Separar en dos grupos
        mejores   = [p for p in puntos_clasificados if p.get("es_mejor")]
        sobre_lben = [p for p in puntos_clasificados if not p.get("es_mejor")]

        # Rango X para trazar las líneas
        x_arr = [p["x"] for p in puntos_clasificados]
        y_arr = [p["y_real"] for p in puntos_clasificados]

        if not x_arr:
            return

        x_min, x_max = min(x_arr), max(x_arr)
        x_line = list(np.linspace(x_min, x_max, 80))

        # ── Calcular línea LBEn ───────────────────────────────────────────────
        coefs  = params.get("coeficientes", {})
        indice = params.get("indice", None)
        r2     = params.get("r2", 0)

        y_lben_line = None
        ecuacion_lben = ""

        if coefs and len(coefs) >= 2:
            intercepto = coefs.get("Intercepto", 0)
            vars_ind   = [k for k in coefs if k != "Intercepto"]
            pendiente = None
            for nombre_var in vars_ind:
                if (x_label.lower() in nombre_var.lower() or
                        nombre_var.lower() in x_label.lower()):
                    pendiente = coefs[nombre_var]
                    break
            if pendiente is None and vars_ind:
                pendiente = coefs[vars_ind[0]]
            if pendiente is not None:
                y_lben_line   = [pendiente * xi + intercepto for xi in x_line]
                ecuacion_lben = _construir_ecuacion(params, x_label, r2)
        elif indice is not None:
            y_lben_line   = [indice * xi for xi in x_line]
            ecuacion_lben = f"y = {indice:.3f} × x<br>R² = {r2:.3f}"

        if y_lben_line is None:
            return

        # ── Calcular línea meta ───────────────────────────────────────────────
        linea_meta_params = params.get("coef_meta", [])   # [intercepto_meta, pendiente_meta]
        r2_meta           = params.get("r2_meta", None)
        ecuacion_meta     = params.get("ecuacion_meta", "")
        y_meta_line       = None

        if linea_meta_params and len(linea_meta_params) == 2:
            intercepto_meta, pendiente_meta = linea_meta_params
            y_meta_line = [pendiente_meta * xi + intercepto_meta for xi in x_line]


        # ── Construir gráfico ─────────────────────────────────────────────────
        fig    = go.Figure()
        layout = get_chart_layout()
        layout["title"] = {
            "text": f"Correlación energética y línea meta — {x_label}",
            "font": {"size": 15, "color": COLORS.text_primary},
            "x": 0.5, "xanchor": "center",
        }
        layout["xaxis"]["title"]     = {"text": x_label}
        layout["xaxis"]["tickangle"] = 0
        layout["yaxis"]["title"]     = {"text": f"Consumo ({unidad})" if unidad else "Consumo"}
        layout["margin"] = {"l": 75, "r": 120, "t": 75, "b": 100}
        layout["plot_bgcolor"]       = "#FAFAFA"
        layout["hovermode"]          = "closest"
        layout["legend"]             = {
            "orientation": "h", "yanchor": "top", "y": -0.20,
            "xanchor": "center", "x": 0.5,
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#E0E0E0", "borderwidth": 1,
        }

        # ── Área sombreada entre LBEn y línea meta ────────────────────────────
        if y_meta_line is not None:
            fig.add_trace(go.Scatter(
                x=x_line + x_line[::-1],
                y=y_lben_line + y_meta_line[::-1],
                fill="toself",
                fillcolor="rgba(39,174,96,0.12)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                name="Potencial de ahorro",
                hoverinfo="skip",
            ))

        # ── Puntos sobre LBEn (azul) ──────────────────────────────────────────
        if sobre_lben:
            fig.add_trace(go.Scatter(
                x=[p["x"]      for p in sobre_lben],
                y=[p["y_real"] for p in sobre_lben],
                mode="markers",
                name=f"Sobre LBEn",
                marker=dict(
                    color="#2E86C1", size=9,
                    line=dict(width=1.5, color="white"),
                    symbol="circle",
                ),
                text=[
                    f"{p['periodo']}<br>{x_label}: {p['x']:,.2f}<br>"
                    f"Consumo: {p['y_real']:,.0f} {unidad}<br>"
                    f"LBEn: {p['y_lben']:,.0f} {unidad}"
                    if p.get("y_lben") is not None else
                    f"{p['periodo']}<br>{x_label}: {p['x']:,.2f}<br>"
                    f"Consumo: {p['y_real']:,.0f} {unidad}"
                    for p in sobre_lben
                ],
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── Puntos de mejor desempeño (verde) ────────────────────────────────
        if mejores:
            fig.add_trace(go.Scatter(
                x=[p["x"]      for p in mejores],
                y=[p["y_real"] for p in mejores],
                mode="markers",
                name=f"Mejor desempeño",
                marker=dict(
                    color="#1E8449", size=10,
                    line=dict(width=1.5, color="white"),
                    symbol="diamond",
                ),
                text=[
                    f"{p['periodo']}<br>{x_label}: {p['x']:,.2f}<br>"
                    f"Consumo: {p['y_real']:,.0f} {unidad}<br>"
                    f"LBEn: {p['y_lben']:,.0f} {unidad}<br>"
                    f"<b>▼ Mejor desempeño</b>"
                    if p.get("y_lben") is not None else
                    f"{p['periodo']}<br>{x_label}: {p['x']:,.2f}<br>"
                    f"Consumo: {p['y_real']:,.0f} {unidad}"
                    for p in mejores
                ],
                hovertemplate="%{text}<extra></extra>",
            ))

        # ── Línea LBEn (roja continua) ────────────────────────────────────────
        fig.add_trace(go.Scatter(
            x=x_line, y=y_lben_line, mode="lines",
            name="LBEn (modelo ajustado)",
            line=dict(color="#E74C3C", width=2.5),
            hovertemplate=f"{x_label}: %{{x:,.2f}}<br>LBEn: %{{y:,.0f}} {unidad}<extra></extra>",
        ))

        # ── Línea meta (verde punteada) ───────────────────────────────────────
        if ecuacion_meta:
        #  Quitar (R²=...) que viene pegado a la ecuación
            ecuacion_meta_limpia = re.sub(r"\(R²\s*=\s*[\d\.]+\)", "", ecuacion_meta)


        fig.add_trace(
            go.Scatter(
                x=x_line,
                y=y_meta_line,
                mode="lines",
                name="Línea meta",
                line=dict(color="#1E8449", width=2.2, dash="dash"),
                hovertemplate=(
                    "<b>Línea meta</b><br>" +
                    f"{ecuacion_meta_limpia}<br>" +
                    (f"R² = {r2_meta:.3f}<br>" if r2_meta is not None else "") +
                    "<extra></extra>"
                )
            )
        )

        # ── Cuadro de ecuaciones y potencial de ahorro ────────────────────────
        # ── Cuadro 1: LBEn ───────────────────────────────────────────────────
        fig.add_annotation(
            xref="paper", yref="paper",
            x=0.02, y=0.97,
            xanchor="left", yanchor="top",
            text=ecuacion_lben,
            showarrow=False,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#D5D8DC",
            borderwidth=1,
            borderpad=8,
            font=dict(size=11, color=COLORS.text_primary, family=FONTS.family),
        )

        # ── Cuadro 2: Línea meta + ahorro ────────────────────────────────────

                

        fig.update_layout(**layout)
        self._render(fig)

    # ── Gráfico LBEn vs meta ──────────────────────────────────────────────────

    def plot_lben_vs_meta(self, resultado: dict, titulo_proyecto: str = ""):
        params   = resultado.get("modelo_params", {})
        unidad   = resultado.get("unidad", "")
        lben     = params.get("lben_mensual", {})

        datos_dep  = params.get("datos_depurados", {})
        coc_dep    = params.get("coc_depurados",   {})
        fuente_dep = datos_dep if any(datos_dep.values()) else coc_dep

        NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                   "Jul","Ago","Sep","Oct","Nov","Dic"]

        lben_vals = []; meta_vals = []; meses_lbl = []

        for mes in range(1, 13):
            lb = lben.get(mes)
            if lb is None:
                continue
            vals_dep = fuente_dep.get(mes, [])
            meta = float(np.percentile(vals_dep, 10)) if vals_dep else lb * 0.90
            lben_vals.append(lb); meta_vals.append(meta); meses_lbl.append(NOMBRES[mes-1])

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
        layout["yaxis"]["autorange"] = "reversed"
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

        fig.add_trace(go.Bar(
            y=meses_lbl, x=lben_vals, name="LBEn mensual", orientation="h",
            marker=dict(color="#1B4F72", line=dict(color="#154360", width=0.8)),
            hovertemplate="<b>%{y}</b><br>LBEn: %{x:,.2f}<extra></extra>",
            text=[f"{v:,.1f}" for v in lben_vals], textposition="inside",
            insidetextanchor="end", textfont=dict(color="white", size=10),
        ))
        fig.add_trace(go.Bar(
            y=meses_lbl, x=meta_vals, name="Meta (mejor desempeño — percentil 10)",
            orientation="h",
            marker=dict(color="#1E8449", line=dict(color="#186A3B", width=0.8)),
            hovertemplate="<b>%{y}</b><br>Meta: %{x:,.2f}<extra></extra>",
            text=[f"{v:,.1f}" for v in meta_vals], textposition="inside",
            insidetextanchor="end", textfont=dict(color="white", size=10),
        ))

        x_max = max(max(lben_vals), max(meta_vals)) * 1.02
        for i, (lb, mt, mes) in enumerate(zip(lben_vals, meta_vals, meses_lbl)):
            diff_pct = (mt - lb) / lb * 100 if lb != 0 else 0
            color_txt = "#27AE60" if diff_pct <= 0 else "#E74C3C"
            fig.add_annotation(
                x=x_max, y=mes, text=f"{diff_pct:+.1f}%", showarrow=False,
                font=dict(size=10, color=color_txt, family=FONTS.family), xanchor="left",
            )

        layout["xaxis"]["range"] = [0, x_max * 1.12]
        fig.update_layout(**layout)
        self._render(fig)


# ── Helper ─────────────────────────────────────────────────────────────────────

def _construir_ecuacion(params: dict, x_label: str, r2: float) -> str:
    coefs = params.get("coeficientes", {})
    if not coefs:
        indice = params.get("indice")
        if indice:
            return f"y = {indice:.4f} × x<br>R² = {r2:.3f}"
        return f"R² = {r2:.3f}"

    nombres = list(coefs.keys())
    valores = list(coefs.values())

    if len(nombres) == 1:
        return f"ȳ = {valores[0]:,.1f}<br>R² = {r2:.3f}"

    if len(nombres) == 2:
        intercepto = valores[0]; pendiente = valores[1]
        signo = "+" if intercepto >= 0 else "−"
        return (
            f"LBEn = {pendiente:.4f}x {signo} {abs(intercepto):,.1f}<br>"
            f"R² = {r2:.3f}"
        )

    terminos = []
    for nombre, val in list(coefs.items())[1:]:
        terminos.append(f"{val:.4f}·{nombre}")
    intercepto = valores[0]
    signo = "+" if intercepto >= 0 else "−"
    ec = "LBEn = " + " + ".join(terminos) + f" {signo} {abs(intercepto):,.1f}"
    return f"{ec}<br>R² = {r2:.3f}"