"""
ui/pages/monitoreo.py
=====================
Flujo de monitoreo:

  1. El usuario selecciona un proyecto guardado (izquierda)
  2. Panel derecho muestra info del proyecto
  3. Sección "Actualizar reporte":
       a. Preview de cuántos meses nuevos quiere agregar
          (parte del último mes que ya tiene la hoja 'Reporte' del Excel)
       b. Botón "Descargar Excel actualizado" → toma el Excel del proyecto,
          agrega las nuevas filas vacías al final de la hoja 'Reporte',
          y lo guarda (en el mismo archivo o donde el usuario elija)
       c. El usuario llena los nuevos valores y lo sube
       d. Al subir: reemplaza el Excel del proyecto y recalcula todo
"""

import os
import re
from datetime import date
import customtkinter as ctk
from tkinter import filedialog
from ui.theme import COLORS, FONTS, SIZES

_MESES_ABREV = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


class MonitoreoPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._proyecto_sel = None
        self._resultado    = None
        self._build()

    def on_enter(self, **kwargs):
        self._refrescar_lista()

    # ═════════════════════════════════════════════════════════════════════════
    # ESTRUCTURA
    # ═════════════════════════════════════════════════════════════════════════
    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color=COLORS.bg_card, corner_radius=0, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(hdr, text="← Inicio", width=80, height=32,
                      fg_color="transparent", hover_color=COLORS.bg_main,
                      text_color=COLORS.text_secondary,
                      font=(FONTS.family, FONTS.size_sm),
                      command=lambda: self.app.show_page("IntroPage")
                      ).grid(row=0, column=0, padx=16)

        ctk.CTkLabel(hdr, text="📡  Monitoreo de proyectos",
                     font=(FONTS.family, FONTS.size_lg, "bold"),
                     text_color=COLORS.text_primary
                     ).grid(row=0, column=1, sticky="w", padx=4)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, minsize=270, weight=0)
        body.grid_columnconfigure(1, weight=1)

        lista_card = ctk.CTkFrame(body, fg_color=COLORS.bg_card,
                                   corner_radius=10, border_width=1,
                                   border_color=COLORS.border)
        lista_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        lista_card.grid_rowconfigure(1, weight=1)
        lista_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(lista_card, text="Proyectos guardados",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.primary
                     ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 6))

        self.lista_sv = ctk.CTkScrollableFrame(lista_card, fg_color="transparent")
        self.lista_sv.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 8))
        self.lista_sv.grid_columnconfigure(0, weight=1)

        self.right_sv = ctk.CTkScrollableFrame(body, fg_color="transparent")
        self.right_sv.grid(row=0, column=1, sticky="nsew")
        self.right_sv.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.right_sv,
                     text="📋\n\nSelecciona un proyecto de la lista",
                     font=(FONTS.family, FONTS.size_md),
                     text_color=COLORS.text_secondary,
                     justify="center").pack(expand=True, pady=100)

    # ═════════════════════════════════════════════════════════════════════════
    # LISTA
    # ═════════════════════════════════════════════════════════════════════════
    def _refrescar_lista(self):
        for w in self.lista_sv.winfo_children():
            w.destroy()
        self._limpiar_derecha()

        from data.gestor_proyectos import listar_proyectos
        proyectos = listar_proyectos()
        if not proyectos:
            ctk.CTkLabel(self.lista_sv,
                         text="Sin proyectos.\nCrea uno desde\n'Comenzar →'",
                         font=(FONTS.family, FONTS.size_sm),
                         text_color=COLORS.text_secondary,
                         justify="center").pack(pady=40)
            return
        for p in proyectos:
            self._card_proyecto(p)

    def _card_proyecto(self, p: dict):
        card = ctk.CTkFrame(self.lista_sv, fg_color=COLORS.bg_main,
                             corner_radius=8, border_width=1,
                             border_color=COLORS.border, cursor="hand2")
        card.pack(fill="x", padx=4, pady=3)

        # Fila superior: nombre + botón eliminar
        fila_top = ctk.CTkFrame(card, fg_color="transparent")
        fila_top.pack(fill="x", padx=6, pady=(6, 0))
        fila_top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(fila_top, text=p.get("nombre_proyecto", "Sin nombre"),
                     font=(FONTS.family, FONTS.size_xs, "bold"),
                     text_color=COLORS.primary, anchor="w"
                     ).grid(row=0, column=0, sticky="w", padx=4)

        btn_del = ctk.CTkButton(fila_top, text="✕", width=22, height=22,
                                fg_color="transparent",
                                hover_color="#FADBD8",
                                text_color=COLORS.text_secondary,
                                font=(FONTS.family, FONTS.size_xs, "bold"),
                                corner_radius=4,
                                command=lambda proj=p: self._confirmar_eliminar(proj))
        btn_del.grid(row=0, column=1, padx=(2, 2))

        ctk.CTkLabel(card,
                     text=f"{p.get('modelo_id','').title()}  ·  {p.get('guardado_en','')[:10]}",
                     font=(FONTS.family, FONTS.size_xs),
                     text_color=COLORS.text_secondary, anchor="w"
                     ).pack(fill="x", padx=10, pady=(0, 8))

        def _click(e, proj=p):
            # No seleccionar si el click fue en el botón eliminar
            self._seleccionar(proj)
        def _on(e):  card.configure(fg_color=COLORS.primary_light)
        def _off(e): card.configure(fg_color=COLORS.bg_main)
        # Bind solo en card y label de subtítulo, no en el botón eliminar
        bind_widgets = [card] + [w for w in card.winfo_children()
                                  if w != btn_del] + list(fila_top.winfo_children())[:-1]
        for w in bind_widgets:
            w.bind("<Button-1>", _click)
            w.bind("<Enter>", _on); w.bind("<Leave>", _off)

    def _confirmar_eliminar(self, p: dict):
        """Muestra ventana de confirmación antes de eliminar el proyecto."""
        import tkinter as tk
        from tkinter import messagebox
        nombre = p.get("nombre_proyecto", "este proyecto")
        confirmar = messagebox.askyesno(
            title="Eliminar proyecto",
            message=f"¿Seguro que quieres eliminar '{nombre}'?\n\nEsto solo borra el registro guardado.\nEl archivo Excel NO se elimina.",
            icon="warning",
        )
        if confirmar:
            from data.gestor_proyectos import eliminar_proyecto
            eliminar_proyecto(p["_archivo"])
            self._refrescar_lista()

    # ═════════════════════════════════════════════════════════════════════════
    # PANEL DERECHO
    # ═════════════════════════════════════════════════════════════════════════
    def _limpiar_derecha(self):
        for w in self.right_sv.winfo_children():
            w.destroy()
        self._resultado = None

    def _seleccionar(self, p: dict):
        self._proyecto_sel = p
        self._limpiar_derecha()
        self._panel_info(p)
        self._panel_actualizar(p)
        self._sep = ctk.CTkFrame(self.right_sv, fg_color=COLORS.border, height=2)
        self._sep.pack(fill="x", padx=4, pady=(8, 0))

    # ── Info del proyecto ─────────────────────────────────────────────────────
    def _panel_info(self, p: dict):
        sv = self.right_sv
        ctk.CTkLabel(sv, text=p.get("nombre_proyecto", "Proyecto"),
                     font=(FONTS.family, FONTS.size_xl, "bold"),
                     text_color=COLORS.primary, anchor="w"
                     ).pack(fill="x", padx=4, pady=(4, 6))

        info = ctk.CTkFrame(sv, fg_color=COLORS.primary_light,
                             corner_radius=8, border_width=1,
                             border_color=COLORS.border)
        info.pack(fill="x", padx=4, pady=(0, 8))
        info.grid_columnconfigure((0, 1, 2), weight=1)

        campos = [
            ("Modelo",            p.get("modelo_id", "—").title()),
            ("Unidad",            p.get("unidad_energia", "—")),
            ("Período histórico", p.get("periodo_historico", "—")),
            ("Columna consumo",   p.get("col_consumo", "—")),
            ("Guardado",          p.get("guardado_en", "")[:10]),
        ]
        for i, (lbl, val) in enumerate(campos):
            r, c = divmod(i, 3)
            f = ctk.CTkFrame(info, fg_color="transparent")
            f.grid(row=r, column=c, sticky="ew", padx=12, pady=6)
            ctk.CTkLabel(f, text=lbl,
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary, anchor="w").pack(anchor="w")
            ctk.CTkLabel(f, text=val,
                         font=(FONTS.family, FONTS.size_sm, "bold"),
                         text_color=COLORS.primary, anchor="w").pack(anchor="w")

    # ── Panel de actualización de reporte ─────────────────────────────────────
    def _panel_actualizar(self, p: dict):
        sv = self.right_sv
        ruta = p.get("ruta_excel", "")
        existe = os.path.exists(ruta) if ruta else False

        card = ctk.CTkFrame(sv, fg_color=COLORS.bg_card,
                             corner_radius=10, border_width=2,
                             border_color=COLORS.primary)
        card.pack(fill="x", padx=4, pady=(0, 4))

        ctk.CTkLabel(card, text="📤  Actualizar datos de reporte",
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.primary
                     ).pack(anchor="w", padx=16, pady=(14, 4))

        # Estado del Excel del proyecto
        icon  = "✅" if existe else "⚠️"
        color = COLORS.success if existe else COLORS.error
        fila_xls = ctk.CTkFrame(card, fg_color="transparent")
        fila_xls.pack(fill="x", padx=16, pady=(0, 4))
        nombre_xls = os.path.basename(ruta) if ruta else "No definido"
        ctk.CTkLabel(fila_xls,
                     text=f"{icon}  Excel del proyecto: {nombre_xls}",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=color).pack(side="left")
        if not existe:
            ctk.CTkButton(fila_xls, text="Buscar",
                          font=(FONTS.family, FONTS.size_xs),
                          fg_color=COLORS.primary, height=26, width=70,
                          command=lambda: self._rebuscar_excel(p)
                          ).pack(side="left", padx=8)

        # Estado del reporte actual
        if existe:
            n_reporte, ultimo_mes = self._info_reporte(ruta)
            if n_reporte > 0:
                ctk.CTkLabel(card,
                             text=f"📅  Reporte actual: {n_reporte} mes(es) — último: {ultimo_mes}",
                             font=(FONTS.family, FONTS.size_sm),
                             text_color=COLORS.text_secondary
                             ).pack(anchor="w", padx=16, pady=(0, 4))
            else:
                ctk.CTkLabel(card,
                             text="📅  Sin datos de reporte aún",
                             font=(FONTS.family, FONTS.size_sm),
                             text_color=COLORS.text_secondary
                             ).pack(anchor="w", padx=16, pady=(0, 4))

        ctk.CTkFrame(card, fg_color=COLORS.border, height=1
                     ).pack(fill="x", padx=16, pady=(4, 10))

        # Cuántos meses nuevos
        ctk.CTkLabel(card, text="¿Cuántos meses nuevos quieres agregar?",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary, anchor="w"
                     ).pack(anchor="w", padx=16, pady=(0, 6))

        fila_meses = ctk.CTkFrame(card, fg_color="transparent")
        fila_meses.pack(fill="x", padx=16, pady=(0, 4))

        self.entry_meses = ctk.CTkEntry(fila_meses, width=80, height=34,
                                         font=(FONTS.family, FONTS.size_md, "bold"),
                                         justify="center")
        self.entry_meses.insert(0, "6")
        self.entry_meses.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(fila_meses, text="meses nuevos",
                     font=(FONTS.family, FONTS.size_sm),
                     text_color=COLORS.text_secondary).pack(side="left")

        self.lbl_preview = ctk.CTkLabel(card, text="",
                                         font=(FONTS.family, FONTS.size_xs),
                                         text_color=COLORS.primary)
        self.lbl_preview.pack(anchor="w", padx=16, pady=(0, 6))
        self.entry_meses.bind("<KeyRelease>", lambda e: self._preview_fechas(p))
        if existe:
            self._preview_fechas(p)

        # Mensaje estado descarga
        self.lbl_descarga = ctk.CTkLabel(card, text="",
                                          font=(FONTS.family, FONTS.size_xs),
                                          text_color=COLORS.success,
                                          wraplength=560, justify="left")
        self.lbl_descarga.pack(anchor="w", padx=16)

        ctk.CTkButton(card,
                      text="⬇  Descargar Excel con filas nuevas",
                      font=(FONTS.family, FONTS.size_sm, "bold"),
                      fg_color=COLORS.primary, hover_color=COLORS.primary_hover,
                      height=36, corner_radius=6,
                      command=lambda: self._descargar_expandido(p, existe, ruta)
                      ).pack(anchor="w", padx=16, pady=(6, 10))

        # Subir Excel llenado
        ctk.CTkFrame(card, fg_color=COLORS.border, height=1
                     ).pack(fill="x", padx=16, pady=(0, 10))

        ctk.CTkLabel(card,
                     text="📂  Subir Excel con los nuevos datos llenados",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary, anchor="w"
                     ).pack(anchor="w", padx=16, pady=(0, 4))

        ctk.CTkLabel(card,
                     text=(
                         "Llena los valores nuevos en la hoja 'Reporte' y sube el archivo.\n"
                         "El Excel del proyecto se actualizará y los gráficos se recalcularán."
                     ),
                     font=(FONTS.family, FONTS.size_sm),
                     text_color=COLORS.text_secondary, justify="left"
                     ).pack(anchor="w", padx=16, pady=(0, 8))

        self.lbl_subida_ok  = ctk.CTkLabel(card, text="",
                                            font=(FONTS.family, FONTS.size_xs),
                                            text_color=COLORS.success)
        self.lbl_subida_ok.pack(anchor="w", padx=16)

        self.progress_bar = ctk.CTkProgressBar(card, mode="indeterminate",
                                               height=8, corner_radius=4,
                                               progress_color=COLORS.accent)
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 0))
        self.progress_bar.pack_forget()  # oculta al inicio

        self.lbl_subida_err = ctk.CTkLabel(card, text="",
                                            font=(FONTS.family, FONTS.size_xs),
                                            text_color=COLORS.error,
                                            wraplength=560, justify="left")
        self.lbl_subida_err.pack(anchor="w", padx=16)

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(6, 14))

        ctk.CTkButton(btns, text="📂  Subir y actualizar proyecto",
                      font=(FONTS.family, FONTS.size_sm, "bold"),
                      fg_color=COLORS.accent, hover_color=COLORS.accent_hover,
                      height=38, corner_radius=6,
                      command=lambda: self._subir_y_calcular(p, existe, ruta)
                      ).pack(side="left", padx=(0, 8))

        if existe:
            ctk.CTkButton(btns, text="🔄  Recalcular",
                          font=(FONTS.family, FONTS.size_sm),
                          fg_color="transparent",
                          hover_color=COLORS.primary_light,
                          text_color=COLORS.primary,
                          border_width=1, border_color=COLORS.primary,
                          height=38, corner_radius=6,
                          command=lambda: self._calcular(p, ruta)
                          ).pack(side="left")

    # ═════════════════════════════════════════════════════════════════════════
    # LÓGICA
    # ═════════════════════════════════════════════════════════════════════════

    def _info_reporte(self, ruta: str):
        """Devuelve (n_filas_reporte, ultimo_mes_str)."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
            if "Reporte" not in wb.sheetnames:
                wb.close(); return 0, "—"
            ws = wb["Reporte"]
            ultima = None
            count  = 0
            for row in ws.iter_rows(min_row=4, max_col=1, values_only=True):
                if row[0] is not None and str(row[0]).strip():
                    ultima = str(row[0]).strip()
                    count += 1
            wb.close()
            return count, (ultima or "—")
        except Exception:
            return 0, "—"

    def _ultimo_mes_reporte(self, ruta: str):
        """Devuelve date del último mes en la hoja Reporte, o None."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
            if "Reporte" not in wb.sheetnames:
                wb.close(); return None
            ws  = wb["Reporte"]
            ult = None
            for row in ws.iter_rows(min_row=4, max_col=1, values_only=True):
                if row[0] is not None and str(row[0]).strip():
                    ult = str(row[0]).strip()
            wb.close()
            if ult:
                m = re.match(r"^([a-záéíóúñ]{3})-(\d{4})$", ult.lower())
                if m:
                    mes_n = _MESES_ABREV.get(m.group(1), 0)
                    if mes_n:
                        return date(int(m.group(2)), mes_n, 1)
        except Exception:
            pass
        return None

    def _ultimo_mes_historico(self, ruta: str):
        """Devuelve date del último mes en la hoja Histórico, o None."""
        try:
            from data.lector_excel import leer_excel
            df = leer_excel(ruta, hoja="Histórico")
            if len(df) > 0:
                val = df.iloc[-1, 0]
                if hasattr(val, 'year'):
                    return date(val.year, val.month, 1)
                s = str(val).strip().lower()
                m = re.match(r"^([a-záéíóúñ]+)[-/\s](\d{4})$", s)
                if m:
                    mes_n = _MESES_ABREV.get(m.group(1)[:3], 0)
                    if mes_n:
                        return date(int(m.group(2)), mes_n, 1)
        except Exception:
            pass
        return None

    def _fechas_desde(self, ultimo: date, n: int):
        """Genera n fechas mensuales a partir del mes siguiente a 'ultimo'."""
        fechas = []
        año, mes = ultimo.year, ultimo.month
        for _ in range(n):
            mes += 1
            if mes > 12:
                mes = 1; año += 1
            fechas.append(date(año, mes, 1))
        return fechas

    def _fmt(self, d: date) -> str:
        ab = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
        return f"{ab[d.month-1]}-{d.year}"

    def _preview_fechas(self, p: dict):
        ruta = p.get("ruta_excel", "")
        if not ruta or not os.path.exists(ruta):
            self.lbl_preview.configure(text="")
            return
        try:
            n = int(self.entry_meses.get())
            if n < 1 or n > 60:
                raise ValueError()
        except ValueError:
            self.lbl_preview.configure(
                text="  ⚠  Ingresa un número entre 1 y 60", text_color=COLORS.error)
            return

        # Primero intenta leer último mes del Reporte; si no, del Histórico
        ultimo = self._ultimo_mes_reporte(ruta) or self._ultimo_mes_historico(ruta)
        if not ultimo:
            self.lbl_preview.configure(text="")
            return

        fechas = self._fechas_desde(ultimo, n)
        self.lbl_preview.configure(
            text=f"  → {self._fmt(fechas[0])}  a  {self._fmt(fechas[-1])}  ({n} períodos nuevos)",
            text_color=COLORS.primary)

    # ── Descargar Excel expandido ─────────────────────────────────────────────
    def _descargar_expandido(self, p: dict, existe: bool, ruta: str):
        if not existe:
            self.lbl_descarga.configure(
                text="⚠  Busca primero el Excel del proyecto.", text_color=COLORS.error)
            return
        try:
            n = int(self.entry_meses.get())
            if n < 1 or n > 60:
                raise ValueError()
        except ValueError:
            self.lbl_descarga.configure(
                text="⚠  Ingresa un número de meses válido (1–60).", text_color=COLORS.error)
            return

        ultimo = self._ultimo_mes_reporte(ruta) or self._ultimo_mes_historico(ruta)
        if not ultimo:
            self.lbl_descarga.configure(
                text="⚠  No se pudo leer la fecha del Excel.", text_color=COLORS.error)
            return

        nuevas_fechas = self._fechas_desde(ultimo, n)
        nombre_base   = os.path.splitext(os.path.basename(ruta))[0]
        sugerido      = f"{nombre_base}_actualizado.xlsx"

        path_dest = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=sugerido,
            title="Guardar Excel con filas nuevas",
        )
        if not path_dest:
            return

        try:
            from data.plantilla import expandir_reporte
            n_exist, n_new = expandir_reporte(
                path_origen=ruta,
                path_destino=path_dest,
                nuevas_fechas=nuevas_fechas,
                col_consumo=p.get("col_consumo", "Consumo_kWh"),
                vars_independientes=p.get("vars_independientes", []),
                unidad=p.get("unidad_energia", "kWh"),
            )
        except Exception as e:
            self.lbl_descarga.configure(
                text=f"❌  Error al generar el archivo: {e}",
                text_color=COLORS.error)
            return

        nombre = os.path.basename(path_dest)
        if n_new > 0:
            self.lbl_descarga.configure(
                text=(f"✅  {nombre}\n"
                      f"     {n_exist} mes(es) existentes conservados  +  {n_new} mes(es) nuevos agregados\n"
                      f"     Llena los valores nuevos en la hoja 'Reporte' y súbelo abajo."),
                text_color=COLORS.success)
        else:
            self.lbl_descarga.configure(
                text=f"ℹ️  {nombre}  —  No se agregaron meses (todos ya existían).",
                text_color=COLORS.text_secondary)

    # ── Subir Excel llenado y recalcular ──────────────────────────────────────
    def _rebuscar_excel(self, p: dict):
        path = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx *.xls")],
            title="Buscar Excel del proyecto",
        )
        if not path:
            return
        from data.gestor_proyectos import actualizar_ruta_excel
        actualizar_ruta_excel(p["_archivo"], path)
        p["ruta_excel"] = path
        self._seleccionar(p)

    def _subir_y_calcular(self, p: dict, existe: bool, ruta_actual: str):
        if not existe:
            self.lbl_subida_err.configure(
                text="⚠  El Excel base no se encontró. Búscalo primero.")
            return
        path_nuevo = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx *.xls")],
            title="Seleccionar Excel con datos actualizados",
        )
        if not path_nuevo:
            return
        self.lbl_subida_err.configure(text="")

        # Si el archivo subido es distinto al del proyecto, actualizar la ruta
        # (no copiamos encima para evitar WinError 32 si está abierto en Excel)
        import os
        if os.path.normpath(path_nuevo) != os.path.normpath(ruta_actual):
            from data.gestor_proyectos import actualizar_ruta_excel
            actualizar_ruta_excel(p["_archivo"], path_nuevo)
            p["ruta_excel"] = path_nuevo
            ruta_actual = path_nuevo

        self._calcular(p, ruta_actual)

    def _calcular(self, p: dict, ruta: str):
        from data.lector_excel import leer_excel
        from data.validador import validar_dataframe
        from core.calculadora import calcular

        col_consumo = p.get("col_consumo", "Consumo_kWh")
        vars_ind    = p.get("vars_independientes", [])
        modelo_id   = p.get("modelo_id", "promedio")
        nivel_conf  = p.get("nivel_confianza", 95)

        try:
            df_hist = leer_excel(ruta, hoja="Histórico")
            err_h = validar_dataframe(df_hist, col_consumo, vars_ind)
            if err_h:
                self.lbl_subida_err.configure(text="❌ Histórico — " + " | ".join(err_h))
                return

            df_rep = None
            try:
                df_rep_raw = leer_excel(ruta, hoja="Reporte")
                df_rep = df_rep_raw.dropna(subset=[col_consumo]).reset_index(drop=True)
                if len(df_rep) == 0:
                    df_rep = None
                    self.lbl_subida_ok.configure(
                        text="✅  Archivo cargado — sin datos de reporte llenados todavía.",
                        text_color=COLORS.text_secondary)
                else:
                    err_r = validar_dataframe(df_rep, col_consumo, vars_ind)
                    if err_r:
                        self.lbl_subida_err.configure(
                            text="❌ Hoja Reporte — " + " | ".join(err_r))
                        return
                    self.lbl_subida_ok.configure(
                        text=f"✅  {len(df_rep)} mes(es) de reporte cargados",
                        text_color=COLORS.success)
                    # Mostrar barra de progreso indeterminada
                    self.progress_bar.pack(fill="x", padx=16, pady=(4, 4))
                    self.progress_bar.start()
                    self.update_idletasks()
            except Exception:
                pass  # Sin hoja Reporte es válido

            resultado = calcular(df_hist, df_rep, modelo_id,
                                  col_consumo, vars_ind, nivel_conf)
            # Ocultar barra de progreso al terminar
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            resultado["unidad"] = p.get("unidad_energia", "kWh")
            self._resultado = resultado

            s = self.app.sesion
            s.nombre_proyecto     = p.get("nombre_proyecto", "")
            s.unidad_energia      = p.get("unidad_energia", "kWh")
            s.modelo_id           = modelo_id
            s.col_consumo         = col_consumo
            s.vars_independientes = vars_ind
            s.nivel_confianza     = nivel_conf
            s.df_historico        = df_hist
            s.df_reporte          = df_rep
            s.resultado           = resultado

            # Ir a la página de resultados
            self.app.show_page("ResultadosPage", desde="MonitoreoPage")

        except Exception as exc:
            self.progress_bar.stop()
            self.progress_bar.pack_forget()
            self.lbl_subida_err.configure(text=f"❌ Error: {exc}")