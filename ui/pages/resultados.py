"""
ui/pages/resultados.py
======================
3 pestañas:
  📈 Línea base  → histórico: puntos (verde=dentro IC, rojo=outlier) + LBEn + banda IC
  📊 Desempeño   → barras desviación arriba + tabla completa abajo
  📡 Seguimiento → reporte vs LBEn (gráfico de línea) + CUSUM abajo
"""

import customtkinter as ctk
from ui.theme import COLORS, FONTS, SIZES
from ui.components.chart_widget import ChartWidget

TABS = ["📈 Línea base", "📊 Desempeño", "📡 Seguimiento"]


class ResultadosPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def on_enter(self, **kwargs):
        self._desde = kwargs.get("desde", None)
        self._render_resultados()

    def _volver(self):
        # Si viene de monitoreo, volver ahí; si no, a DatosPage
        if getattr(self, "_desde", None) == "MonitoreoPage":
            self.app.show_page("MonitoreoPage")
        else:
            self.app.show_page("DatosPage")

    # ─────────────────────────────────────────────────────────────────────────
    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color=COLORS.bg_card, corner_radius=0, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(hdr, text="← Volver", width=80, height=32,
                      fg_color="transparent", hover_color=COLORS.bg_main,
                      text_color=COLORS.text_secondary,
                      font=(FONTS.family, FONTS.size_sm),
                      command=self._volver
                      ).grid(row=0, column=0, padx=16)

        self.lbl_titulo = ctk.CTkLabel(
            hdr, text="Resultados",
            font=(FONTS.family, FONTS.size_lg, "bold"),
            text_color=COLORS.text_primary)
        self.lbl_titulo.grid(row=0, column=1, sticky="w", padx=4)

        ctk.CTkButton(hdr, text="📤 Exportar informe",
                      font=(FONTS.family, FONTS.size_sm),
                      fg_color=COLORS.primary, hover_color=COLORS.primary_hover,
                      height=34, corner_radius=SIZES.button_radius,
                      command=self._exportar).grid(row=0, column=2, padx=16)

        self.tabs = ctk.CTkTabview(
            self,
            fg_color=COLORS.bg_main,
            segmented_button_fg_color=COLORS.bg_card,
            segmented_button_selected_color=COLORS.primary,
            segmented_button_selected_hover_color=COLORS.primary_hover,
            segmented_button_unselected_color=COLORS.bg_card,
            text_color=COLORS.text_primary,
            text_color_disabled=COLORS.text_secondary,
        )
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=16, pady=(8, 12))
        for name in TABS:
            self.tabs.add(name)

    # ─────────────────────────────────────────────────────────────────────────
    def _render_resultados(self):
        s = self.app.sesion
        if not getattr(s, "resultado", None):
            return
        r = s.resultado
        r["unidad"] = s.unidad_energia
        self.lbl_titulo.configure(
            text=f"Resultados — {s.nombre_proyecto or 'Análisis'}")
        for name in TABS:
            for w in self.tabs.tab(name).winfo_children():
                w.destroy()
        self._tab_linea_base(r, s)
        self._tab_desempeno(r, s)
        self._tab_seguimiento(r, s)
        # Si viene de monitoreo, abrir directamente la pestaña de seguimiento
        if getattr(self, "_desde", None) == "MonitoreoPage":
            self.tabs.set("📡 Seguimiento")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Línea base
    # Scroll vertical:
    #   └─ advertencias (si hay)
    #   └─ gráfico histórico (puntos coloreados + LBEn + banda IC)
    #   └─ tabla 12 LBEn mensuales
    # ══════════════════════════════════════════════════════════════════════════
    def _tab_linea_base(self, r, s):
        tab = self.tabs.tab("📈 Línea base")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        sv = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        sv.grid(row=0, column=0, sticky="nsew")
        sv.grid_columnconfigure(0, weight=1)

        # Advertencias — bloque colapsable
        advertencias = r.get("advertencias_modelo", [])
        if advertencias:
            self._bloque_advertencias(sv, advertencias)

        # Gráfico histórico — puntos coloreados + LBEn + banda IC
        g = ChartWidget(sv, height=480)
        g.pack(fill="x", padx=12, pady=(12, 8))
        g.plot_linea_base(r, titulo_proyecto=s.nombre_proyecto or "")

        # Tabla 12 LBEn mensuales — COMPLETA (6 columnas) en ResultadosPage
        tabla_lben = r.get("tabla_lben_completa", [])
        cols_lben  = r.get("cols_lben_completa", [])
        if tabla_lben and cols_lben:
            self._card_tabla_lben(sv, tabla_lben, cols_lben)

    def _bloque_advertencias(self, parent, advertencias: list):
        """Bloque colapsable con contador — se expande al hacer clic."""
        n = len(advertencias)
        contenedor = ctk.CTkFrame(parent, fg_color="transparent")
        contenedor.pack(fill="x", padx=12, pady=(8, 0))

        # Botón toggle
        btn_var = ctk.StringVar(value=f"⚠  {n} advertencia(s) del modelo  ▾")
        btn = ctk.CTkButton(
            contenedor,
            textvariable=btn_var,
            fg_color="#FEF9E7",
            hover_color="#FDF3CD",
            text_color="#7D6608",
            border_width=1,
            border_color="#F0B429",
            corner_radius=6,
            height=30,
            font=(FONTS.family, FONTS.size_xs, "bold"),
            anchor="w",
        )
        btn.pack(fill="x")

        # Panel de detalle (oculto por defecto)
        detalle = ctk.CTkFrame(contenedor, fg_color="#FEFCE8",
                               corner_radius=0, border_width=1,
                               border_color="#F0B429")
        visible = [False]

        for txt in advertencias:
            ctk.CTkLabel(detalle, text=f"  • {txt}",
                         font=(FONTS.family, FONTS.size_xs),
                         text_color="#7D6608",
                         justify="left", wraplength=860,
                         anchor="w").pack(fill="x", padx=10, pady=2)
        ctk.CTkFrame(detalle, fg_color="transparent", height=6).pack()

        def _toggle():
            if visible[0]:
                detalle.pack_forget()
                btn_var.set(f"⚠  {n} advertencia(s) del modelo  ▾")
            else:
                detalle.pack(fill="x")
                btn_var.set(f"⚠  {n} advertencia(s) del modelo  ▴")
            visible[0] = not visible[0]

        btn.configure(command=_toggle)

    def _card_tabla_lben(self, parent, filas, columnas):
        """Tabla completa de 6 columnas con IC, outliers y LBEn."""
        card = ctk.CTkFrame(parent, fg_color=COLORS.bg_card,
                             corner_radius=10, border_width=1,
                             border_color=COLORS.border)
        card.pack(fill="x", padx=12, pady=(0, 20))

        ctk.CTkLabel(card,
                     text="📋  Línea Base Energética mensual — Resolución UPME 16/2024",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=16, pady=(14, 8))

        tbl = ctk.CTkFrame(card, fg_color="transparent")
        tbl.pack(padx=14, pady=(0, 14), fill="x")

        for c in range(len(columnas)):
            tbl.grid_columnconfigure(c, weight=1)

        # Encabezados
        for c, col in enumerate(columnas):
            h = ctk.CTkFrame(tbl, fg_color=COLORS.primary, corner_radius=0, height=34)
            h.grid(row=0, column=c, sticky="ew", padx=1, pady=(0, 2))
            h.grid_propagate(False)
            ctk.CTkLabel(h, text=col,
                         font=(FONTS.family, FONTS.size_xs, "bold"),
                         text_color="white"
                         ).place(relx=0.5, rely=0.5, anchor="center")

        # Filas
        for ri, fila in enumerate(filas):
            bg = COLORS.bg_card if ri % 2 == 0 else "#F4F6F8"
            tiene_out = str(fila[2]) not in ("—", "-", "0", "")
            sin_datos = fila[4] == "Sin datos"
            if tiene_out:  bg = "#FADBD8"
            if sin_datos:  bg = "#F0F0F0"

            for ci, valor in enumerate(fila):
                cell = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0, height=30)
                cell.grid(row=ri + 1, column=ci, sticky="ew", padx=1, pady=1)
                cell.grid_propagate(False)
                color = COLORS.text_primary
                if ci == 4 and not sin_datos:  color = COLORS.accent
                elif ci == 2 and tiene_out:    color = COLORS.error
                ctk.CTkLabel(cell, text=str(valor),
                             font=(FONTS.family, FONTS.size_xs),
                             text_color=color
                             ).place(relx=0.5, rely=0.5, anchor="center")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Desempeño
    # Scroll vertical:
    #   └─ gráfico barras desviación %
    #   └─ tabla desempeño completa
    # ══════════════════════════════════════════════════════════════════════════
    def _tab_desempeno(self, r, s):
        tab = self.tabs.tab("📊 Desempeño")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        sv = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        sv.grid(row=0, column=0, sticky="nsew")
        sv.grid_columnconfigure(0, weight=1)

        g = ChartWidget(sv, height=400)
        g.pack(fill="x", padx=12, pady=(12, 8))
        g.plot_desviacion(r)

        ctk.CTkLabel(sv, text="Tabla de desempeño",
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=16, pady=(8, 4))

        self._card_tabla_desempeno(
            sv,
            filas=r.get("tabla_desempeno", []),
            columnas=r.get("columnas_desempeno", []),
        )

    def _card_tabla_desempeno(self, parent, filas, columnas):
        card = ctk.CTkFrame(parent, fg_color=COLORS.bg_card,
                             corner_radius=8, border_width=1,
                             border_color=COLORS.border)
        card.pack(fill="x", padx=12, pady=(0, 20))

        tbl = ctk.CTkFrame(card, fg_color="transparent")
        tbl.pack(fill="x", padx=12, pady=12)

        try:
            di = columnas.index("Desviación (%)")
        except ValueError:
            di = -1

        for c in range(len(columnas)):
            tbl.grid_columnconfigure(c, weight=1)

        for c, col in enumerate(columnas):
            h = ctk.CTkFrame(tbl, fg_color=COLORS.primary, corner_radius=0, height=36)
            h.grid(row=0, column=c, sticky="ew", padx=1, pady=(0, 2))
            h.grid_propagate(False)
            ctk.CTkLabel(h, text=col,
                         font=(FONTS.family, FONTS.size_sm, "bold"),
                         text_color="white"
                         ).place(relx=0.5, rely=0.5, anchor="center")

        for ri, fila in enumerate(filas):
            bg = COLORS.bg_card if ri % 2 == 0 else "#F7F9FA"
            if di >= 0:
                try:
                    v = float(str(fila[di]).replace("%","").replace("+","").replace(",",".").strip())
                    if v < -2:   bg = "#D5F5E3"
                    elif v > 2:  bg = "#FADBD8"
                except ValueError:
                    pass

            for ci, valor in enumerate(fila):
                cell = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0, height=34)
                cell.grid(row=ri + 1, column=ci, sticky="ew", padx=1, pady=1)
                cell.grid_propagate(False)
                color = COLORS.text_primary
                if di >= 0 and ci == di:
                    try:
                        v = float(str(valor).replace("%","").replace("+","").replace(",",".").strip())
                        color = COLORS.improvement if v <= 0 else COLORS.degradation
                    except ValueError:
                        pass
                ctk.CTkLabel(cell, text=str(valor),
                             font=(FONTS.family, FONTS.size_sm),
                             text_color=color
                             ).place(relx=0.5, rely=0.5, anchor="center")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Seguimiento
    #   Desde monitoreo: layout 2 columnas (tabla LBEn izq | gráficos der)
    #   Desde creación:  scroll vertical normal
    # ══════════════════════════════════════════════════════════════════════════
    def _tab_seguimiento(self, r, s):
        tab = self.tabs.tab("📡 Seguimiento")
        tab.grid_rowconfigure(0, weight=1)
        # Resetear columnas — evita que quede la división de una sesión anterior
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=0, minsize=0)

        desde_monitoreo = getattr(self, "_desde", None) == "MonitoreoPage"

        if desde_monitoreo and r.get("tiene_reporte"):
            self._tab_seguimiento_monitoreo(tab, r, s)
        else:
            self._tab_seguimiento_normal(tab, r, s)

    def _tab_seguimiento_normal(self, tab, r, s):
        """Layout original: scroll vertical con gráficos apilados."""
        sv = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        sv.grid(row=0, column=0, sticky="nsew")
        sv.grid_columnconfigure(0, weight=1)

        if not r.get("tiene_reporte"):
            msg = ctk.CTkFrame(sv, fg_color=COLORS.bg_card,
                               corner_radius=10, border_width=1,
                               border_color=COLORS.border)
            msg.pack(fill="x", padx=12, pady=40)
            ctk.CTkLabel(msg,
                         text="📋  Sin datos de reporte aún",
                         font=(FONTS.family, FONTS.size_md, "bold"),
                         text_color=COLORS.primary
                         ).pack(pady=(24, 6))
            ctk.CTkLabel(msg,
                         text="Ve a Monitoreo para agregar períodos de reporte\ny ver el seguimiento energético aquí.",
                         font=(FONTS.family, FONTS.size_sm),
                         text_color=COLORS.text_secondary,
                         justify="center"
                         ).pack(pady=(0, 24))
            return

        g1 = ChartWidget(sv, height=480)
        g1.pack(fill="x", padx=12, pady=(12, 8))
        g1.plot_seguimiento(r, titulo_proyecto=s.nombre_proyecto or "")

        ctk.CTkLabel(sv, text="CUSUM — Acumulado de desviaciones",
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=16, pady=(8, 4))

        g2 = ChartWidget(sv, height=420)
        g2.pack(fill="x", padx=12, pady=(0, 20))
        g2.plot_cusum(r)

    def _tab_seguimiento_monitoreo(self, tab, r, s):
        """Layout dos columnas: tabla LBEn fija a la izquierda | gráficos a la derecha."""
        tab.grid_columnconfigure(0, weight=0, minsize=280)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # ── Columna izquierda: tabla LBEn (fija) ─────────────────────────────
        col_izq = ctk.CTkFrame(tab, fg_color=COLORS.bg_card,
                                corner_radius=10, border_width=1,
                                border_color=COLORS.border)
        col_izq.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        col_izq.grid_rowconfigure(1, weight=1)
        col_izq.grid_columnconfigure(0, weight=1)

        # Título dinámico según modelo
        modelo_id = getattr(s, "modelo_id", "promedio")
        titulo_izq = "📋  LBEn mensual" if modelo_id == "promedio" else "📊  Índice energético"
        ctk.CTkLabel(col_izq, text=titulo_izq,
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.primary
                     ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        sv_izq = ctk.CTkScrollableFrame(col_izq, fg_color="transparent")
        sv_izq.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        sv_izq.grid_columnconfigure(0, weight=1)

        self._tabla_lben_simple(sv_izq, r)

        # ── Columna derecha: gráficos con scroll ──────────────────────────────
        sv_der = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        sv_der.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        sv_der.grid_columnconfigure(0, weight=1)

        if not r.get("tiene_reporte"):
            msg = ctk.CTkFrame(sv_der, fg_color=COLORS.bg_card,
                               corner_radius=10, border_width=1,
                               border_color=COLORS.border)
            msg.pack(fill="x", padx=4, pady=40)
            ctk.CTkLabel(msg,
                         text="📋  Sin datos de reporte aún",
                         font=(FONTS.family, FONTS.size_md, "bold"),
                         text_color=COLORS.primary
                         ).pack(pady=(24, 6))
            ctk.CTkLabel(msg,
                         text="Ve a Monitoreo para agregar períodos de reporte\ny ver el seguimiento energético aquí.",
                         font=(FONTS.family, FONTS.size_sm),
                         text_color=COLORS.text_secondary,
                         justify="center"
                         ).pack(pady=(0, 24))
            return

        # KPIs resumen
        self._kpis_resumen(sv_der, r)

        # Gráfico seguimiento
        ctk.CTkLabel(sv_der, text="📈  Consumo real vs LBEn",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=4, pady=(8, 2))

        g1 = ChartWidget(sv_der, height=360)
        g1.pack(fill="x", padx=4, pady=(0, 8))
        g1.plot_seguimiento(r, titulo_proyecto=s.nombre_proyecto or "")

        # Gráfico CUSUM
        ctk.CTkLabel(sv_der, text="📉  CUSUM — Acumulado de desviaciones",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=4, pady=(4, 2))

        g2 = ChartWidget(sv_der, height=320)
        g2.pack(fill="x", padx=4, pady=(0, 20))
        g2.plot_cusum(r)

    def _tabla_lben_simple(self, parent, r: dict):
        """Tabla compacta para el panel lateral — LBEn (promedio) o índice (cociente)."""
        filas = r.get("tabla_lben_mensual", [])
        cols  = r.get("cols_lben_mensual", ["Mes", "LBEn"])
        if not filas:
            ctk.CTkLabel(parent, text="Sin datos",
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary).pack(pady=20)
            return

        n_cols = len(cols) if cols else 2
        tbl = ctk.CTkFrame(parent, fg_color="transparent")
        tbl.pack(fill="x", padx=6, pady=4)
        for c in range(n_cols):
            tbl.grid_columnconfigure(c, weight=1)

        for c, txt in enumerate(cols):
            h = ctk.CTkFrame(tbl, fg_color=COLORS.primary, corner_radius=4, height=30)
            h.grid(row=0, column=c, sticky="ew", padx=1, pady=(0, 2))
            h.grid_propagate(False)
            ctk.CTkLabel(h, text=txt,
                         font=(FONTS.family, FONTS.size_xs, "bold"),
                         text_color="white"
                         ).place(relx=0.5, rely=0.5, anchor="center")

        for ri, fila in enumerate(filas):
            fila = list(fila) if not isinstance(fila, list) else fila
            mes = fila[0] if fila else ""
            lben_val = fila[1] if len(fila) > 1 else ""
            bg = COLORS.bg_card if ri % 2 == 0 else "#F4F6F8"
            sin = str(lben_val) == "Sin datos"
            if sin: bg = "#F0F0F0"

            cm = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0, height=28)
            cm.grid(row=ri+1, column=0, sticky="ew", padx=(1, 0), pady=1)
            cm.grid_propagate(False)
            ctk.CTkLabel(cm, text=mes,
                         font=(FONTS.family, FONTS.size_xs, "bold"),
                         text_color=COLORS.text_primary
                         ).place(relx=0.08, rely=0.5, anchor="w")

            cl = ctk.CTkFrame(tbl, fg_color=bg, corner_radius=0, height=28)
            cl.grid(row=ri+1, column=1, sticky="ew", padx=(0, 1), pady=1)
            cl.grid_propagate(False)
            ctk.CTkLabel(cl, text=str(lben_val),
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.accent if not sin else COLORS.text_secondary
                         ).place(relx=0.92, rely=0.5, anchor="e")

    def _kpis_resumen(self, parent, r: dict):
        """Tarjetas KPI: meses con ahorro, excesos, desviación promedio."""
        fechas = r.get("fechas", [])
        desv   = r.get("desviacion_pct", [])
        if not fechas or not desv:
            return

        excesos = sum(1 for d in desv if d > 0)
        ahorros = sum(1 for d in desv if d <= 0)
        prom    = sum(desv) / len(desv)

        card = ctk.CTkFrame(parent, fg_color=COLORS.bg_card,
                             corner_radius=8, border_width=1,
                             border_color=COLORS.border)
        card.pack(fill="x", padx=4, pady=(4, 8))
        card.grid_columnconfigure((0, 1, 2), weight=1)

        kpis = [
            (str(ahorros),    "Meses con ahorro",   "#27AE60"),
            (str(excesos),    "Meses sobre LBEn",   COLORS.error if excesos else COLORS.text_secondary),
            (f"{prom:+.1f}%", "Desviación promedio", "#27AE60" if prom <= 0 else COLORS.error),
        ]
        for col, (val, lbl, color) in enumerate(kpis):
            f = ctk.CTkFrame(card, fg_color="transparent")
            f.grid(row=0, column=col, padx=12, pady=10, sticky="ew")
            ctk.CTkLabel(f, text=val,
                         font=(FONTS.family, FONTS.size_xl, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(f, text=lbl,
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary).pack()

    # ─────────────────────────────────────────────────────────────────────────
    def _exportar(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("PDF", "*.pdf")],
            initialfile=f"informe_{self.app.sesion.nombre_proyecto or 'resultado'}.xlsx",
        )
        if not path:
            return
        from core.exportador import exportar_informe
        exportar_informe(path, self.app.sesion.resultado, self.app.sesion)
