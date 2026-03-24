"""
ui/pages/datos.py
=================
Carga el archivo Excel y lee las dos hojas: 'Histórico' y 'Reporte'.
Si el archivo no tiene hoja 'Reporte' (usuario sin datos nuevos) también funciona.
"""

import customtkinter as ctk
from tkinter import filedialog
from ui.theme import COLORS, FONTS, SIZES
from data.lector_excel import leer_excel
from data.validador import validar_dataframe


class DatosPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def on_enter(self, **kwargs):
        self._actualizar_info()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS.bg_card, corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkButton(header, text="← Configuración", width=110, height=32,
                      fg_color="transparent", hover_color=COLORS.bg_main,
                      text_color=COLORS.text_secondary,
                      font=(FONTS.family, FONTS.size_sm),
                      command=lambda: self.app.show_page("ConfiguracionPage")).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(header, text="Cargar datos",
                     font=(FONTS.family, FONTS.size_lg, "bold"),
                     text_color=COLORS.text_primary).pack(side="left", padx=8)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=60, pady=30)
        body.grid_columnconfigure(0, weight=1)

        # ── Info configuración activa ──────────────────────────────────────────
        self.info_card = ctk.CTkFrame(body, fg_color=COLORS.primary_light,
                                       corner_radius=SIZES.card_radius,
                                       border_width=1, border_color=COLORS.border)
        self.info_card.pack(fill="x", pady=(0, 20))
        self.lbl_info = ctk.CTkLabel(self.info_card, text="",
                                      font=(FONTS.family, FONTS.size_sm),
                                      text_color=COLORS.primary, justify="left")
        self.lbl_info.pack(anchor="w", padx=16, pady=12)

        # ── Zona de carga ─────────────────────────────────────────────────────
        upload_card = ctk.CTkFrame(body, fg_color=COLORS.bg_card,
                                   corner_radius=SIZES.card_radius,
                                   border_width=2, border_color=COLORS.border)
        upload_card.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(upload_card, text="📂", font=(FONTS.family, 40)).pack(pady=(24, 4))
        ctk.CTkLabel(upload_card, text="Selecciona el archivo Excel con tus datos",
                     font=(FONTS.family, FONTS.size_md),
                     text_color=COLORS.text_primary).pack()
        ctk.CTkLabel(upload_card,
                     text="El archivo debe tener las hojas 'Histórico' (obligatoria) y 'Reporte' (opcional)",
                     font=(FONTS.family, FONTS.size_xs),
                     text_color=COLORS.text_secondary).pack(pady=(2, 12))

        ctk.CTkButton(upload_card, text="Seleccionar archivo Excel",
                      font=(FONTS.family, FONTS.size_base, "bold"),
                      fg_color=COLORS.primary, hover_color=COLORS.primary_hover,
                      height=40, corner_radius=SIZES.button_radius,
                      command=self._seleccionar_archivo).pack(pady=(0, 24))

        self.lbl_archivo = ctk.CTkLabel(body, text="Ningún archivo cargado",
                                         font=(FONTS.family, FONTS.size_sm),
                                         text_color=COLORS.text_secondary)
        self.lbl_archivo.pack(anchor="w", pady=(0, 8))

        # ── Previews de las dos hojas ──────────────────────────────────────────
        # Histórico
        self.prev_hist = self._make_preview(body, "Histórico — primeras 5 filas")
        self.prev_hist.pack_forget()

        # Reporte
        self.prev_rep = self._make_preview(body, "Reporte — primeras 5 filas")
        self.prev_rep.pack_forget()

        # ── Errores ───────────────────────────────────────────────────────────
        self.error_lbl = ctk.CTkLabel(body, text="",
                                       font=(FONTS.family, FONTS.size_sm),
                                       text_color=COLORS.error, wraplength=620)
        self.error_lbl.pack(anchor="w")

        # ── Botón calcular ────────────────────────────────────────────────────
        self.btn_calcular = ctk.CTkButton(
            body, text="Calcular línea base →",
            font=(FONTS.family, FONTS.size_lg, "bold"),
            fg_color=COLORS.accent, hover_color=COLORS.accent_hover,
            height=52, corner_radius=SIZES.button_radius,
            state="disabled", command=self._calcular,
        )
        self.btn_calcular.pack(anchor="w", pady=(20, 0))

    def _make_preview(self, parent, titulo):
        frame = ctk.CTkFrame(parent, fg_color=COLORS.bg_card,
                              corner_radius=SIZES.card_radius,
                              border_width=1, border_color=COLORS.border)
        ctk.CTkLabel(frame, text=titulo,
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(12, 0))
        txt = ctk.CTkTextbox(frame, height=160,
                              font=(FONTS.family_mono, FONTS.size_xs),
                              fg_color=COLORS.bg_main)
        txt.pack(fill="x", padx=16, pady=(4, 14))
        frame._textbox = txt
        return frame

    def _actualizar_info(self):
        s = self.app.sesion
        texto = (
            f"Modelo: {s.modelo_id.title() if s.modelo_id else '—'}   |   "
            f"Columna consumo: {s.col_consumo}   |   "
            f"Período histórico: {s.periodo_historico or '—'}"
        )
        if s.tiene_reporte and s.periodo_reporte:
            texto += f"\nPeríodo de reporte: {s.periodo_reporte}"
        self.lbl_info.configure(text=texto)

    def _seleccionar_archivo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Excel", "*.xlsx *.xls")],
            title="Seleccionar archivo de datos",
        )
        if not path:
            return

        s = self.app.sesion
        self.error_lbl.configure(text="")
        errores = []

        try:
            # ── Hoja Histórico ────────────────────────────────────────────────
            df_hist = leer_excel(path, hoja="Histórico")
            err_h = validar_dataframe(df_hist, s.col_consumo, s.vars_independientes)
            if err_h:
                errores += [f"[Histórico] {e}" for e in err_h]
            else:
                s.df_historico = df_hist
                self._mostrar_preview(self.prev_hist, df_hist)

            # ── Hoja Reporte (opcional) ───────────────────────────────────────
            s.df_reporte = None
            try:
                df_rep = leer_excel(path, hoja="Reporte")
                err_r = validar_dataframe(df_rep, s.col_consumo, s.vars_independientes)
                if err_r:
                    errores += [f"[Reporte] {e}" for e in err_r]
                else:
                    s.df_reporte = df_rep
                    self._mostrar_preview(self.prev_rep, df_rep)
            except Exception:
                # No hay hoja Reporte — es válido
                self.prev_rep.pack_forget()

            s.ruta_excel = path   # guarda la ruta para el gestor de proyectos
            nombre = path.split("\\")[-1].split("/")[-1]
            n_hist = len(df_hist) if s.df_historico is not None else 0
            n_rep  = len(s.df_reporte) if s.df_reporte is not None else 0
            self.lbl_archivo.configure(
                text=f"✓  {nombre}   (Histórico: {n_hist} filas"
                     + (f"  |  Reporte: {n_rep} filas" if n_rep else "  |  Sin reporte")
                     + ")",
                text_color=COLORS.success,
            )

            if errores:
                self.error_lbl.configure(text="⚠  " + "\n".join(errores))
                self.btn_calcular.configure(state="disabled")
            else:
                self.btn_calcular.configure(state="normal")

        except Exception as exc:
            self.error_lbl.configure(text=f"❌ Error al leer el archivo: {exc}")
            self.btn_calcular.configure(state="disabled")

    def _mostrar_preview(self, frame, df):
        frame._textbox.configure(state="normal")
        frame._textbox.delete("1.0", "end")
        frame._textbox.insert("1.0", df.head(5).to_string())
        frame._textbox.configure(state="disabled")
        frame.pack(fill="x", pady=(0, 12))

    def _calcular(self):
        from core.calculadora import calcular
        from data.gestor_proyectos import guardar_proyecto
        s = self.app.sesion
        self.error_lbl.configure(text="")
        try:
            resultado = calcular(
                df_historico=s.df_historico,
                df_reporte=s.df_reporte,
                modelo_id=s.modelo_id,
                col_consumo=s.col_consumo,
                vars_independientes=s.vars_independientes,
                nivel_confianza=s.nivel_confianza,
            )
            s.resultado = resultado
            # Guarda el proyecto automáticamente para poder abrirlo en Monitoreo
            if s.nombre_proyecto and s.ruta_excel:
                try:
                    guardar_proyecto(s, s.ruta_excel)
                except Exception:
                    pass  # guardar es opcional, no bloquea
            self.app.show_page("ResultadosPage")
        except Exception as exc:
            self.error_lbl.configure(text=f"❌ Error en el cálculo: {exc}")
