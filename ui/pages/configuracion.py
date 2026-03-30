"""
ui/pages/configuracion.py
=========================
Configuración con DOS períodos:
  • Período histórico  → entrena el modelo (línea base)
  • Período de reporte → se compara contra la línea base (opcional)
"""

import customtkinter as ctk
from datetime import date
from ui.theme import COLORS, FONTS, SIZES
from data.plantilla import generar_plantilla

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
         "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
AÑOS  = [str(y) for y in range(2015, date.today().year + 2)]


class ConfiguracionPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self.modelo = None
        self.var_entries = []
        self._build()

    def on_enter(self, modelo: dict = None, **kwargs):
        if modelo:
            self.modelo = modelo
            self.app.sesion.modelo_id = modelo["id"]
            self._refresh()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color=COLORS.bg_card, corner_radius=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkButton(header, text="← Modelos", width=90, height=32,
                      fg_color="transparent", hover_color=COLORS.bg_main,
                      text_color=COLORS.text_secondary,
                      font=(FONTS.family, FONTS.size_sm),
                      command=lambda: self.app.show_page("ModelosPage")).pack(side="left", padx=16, pady=14)

        self.title_lbl = ctk.CTkLabel(header, text="Configuración",
                                       font=(FONTS.family, FONTS.size_lg, "bold"),
                                       text_color=COLORS.text_primary)
        self.title_lbl.pack(side="left", padx=8)

        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=60, pady=30)
        self.body.grid_columnconfigure(0, weight=1)

    def _refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.var_entries.clear()

        m = self.modelo
        self.title_lbl.configure(text=f"Configuración — {m['nombre']}")

        # ── Información del proyecto ───────────────────────────────────────────
        self._section(self.body, "Información del proyecto")
        info_card = self._card(self.body)

        self.entry_proyecto = self._field(info_card, "Nombre del proyecto", "Planta Norte — 2024")
        self.entry_unidad   = self._field(info_card, "Unidad de energía", "kWh")

        # ── Período histórico ──────────────────────────────────────────────────
        self._section(self.body, "1. Período histórico  (para construir la línea base)")

        # Explicación breve
        ctk.CTkLabel(self.body,
                     text="Son los datos pasados con los que se ajusta el modelo. Deben ser representativos\n"
                          "del consumo normal, sin interrupciones ni anomalías.",
                     font=(FONTS.family, FONTS.size_sm),
                     text_color=COLORS.text_secondary,
                     justify="left").pack(anchor="w", pady=(0, 6))

        hist_card = self._card(self.body)
        self._build_picker(hist_card, prefijo="hist",
                           default_ini_año=str(date.today().year - 3),
                           default_fin_año=str(date.today().year - 2),
                           min_meses=12)

        # ── Período de reporte ────────────────────────────────────────────────
        self._section(self.body, "2. Período de reporte  (para evaluar el desempeño)")

        ctk.CTkLabel(self.body,
                     text="Son los datos nuevos que se comparan contra la línea base para detectar\n"
                          "ahorros o incrementos de consumo. Puede omitirse si aún no tienes datos nuevos.",
                     font=(FONTS.family, FONTS.size_sm),
                     text_color=COLORS.text_secondary,
                     justify="left").pack(anchor="w", pady=(0, 6))

        rep_card = self._card(self.body)

        # Toggle "tengo datos de reporte"
        toggle_row = ctk.CTkFrame(rep_card, fg_color="transparent")
        toggle_row.pack(fill="x", padx=16, pady=(14, 4))
        self.var_tiene_reporte = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(toggle_row,
                        text="Tengo datos de reporte para evaluar",
                        variable=self.var_tiene_reporte,
                        font=(FONTS.family, FONTS.size_sm),
                        command=self._toggle_reporte).pack(side="left")

        self.rep_picker_frame = ctk.CTkFrame(rep_card, fg_color="transparent")
        self.rep_picker_frame.pack(fill="x")
        self._build_picker(self.rep_picker_frame, prefijo="rep",
                           default_ini_año=str(date.today().year - 1),
                           default_fin_año=str(date.today().year),
                           min_meses=1)

        # ── Variables ──────────────────────────────────────────────────────────
        self._section(self.body, "Variables del modelo")
        vars_card = self._card(self.body)

        ctk.CTkLabel(vars_card, text="Variable dependiente (consumo energético)",
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(16, 2))
        self.entry_dep = self._field(vars_card, "Nombre columna consumo", "Consumo_kWh",
                                     hint="Debe coincidir exactamente con el encabezado en tu Excel")

        if m["id"] in ("cociente", "regresion"):
            ctk.CTkFrame(vars_card, fg_color=COLORS.border, height=1).pack(fill="x", padx=16, pady=8)
            ctk.CTkLabel(vars_card, text="Variables independientes",
                         font=(FONTS.family, FONTS.size_sm, "bold"),
                         text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(0, 4))
            hint = "Solo 1 variable (ej. Producción_ton)" if m["id"] == "cociente" \
                   else "Puedes agregar más variables para regresión múltiple"
            ctk.CTkLabel(vars_card, text=hint,
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary).pack(anchor="w", padx=16, pady=(0, 8))
            self.vars_container = ctk.CTkFrame(vars_card, fg_color="transparent")
            self.vars_container.pack(fill="x", padx=16)
            self._add_var_field()
            if m["id"] == "regresion":
                ctk.CTkButton(vars_card, text="+ Agregar variable", height=32,
                              fg_color="transparent", border_width=1,
                              border_color=COLORS.primary, text_color=COLORS.primary,
                              font=(FONTS.family, FONTS.size_sm),
                              command=self._add_var_field).pack(anchor="w", padx=16, pady=8)

        # ── Opciones avanzadas ─────────────────────────────────────────────────
        #self._section(self.body, "Opciones avanzadas")
        #opt_card = self._card(self.body)
        #self.var_confianza = ctk.StringVar(value="95")
        #self._field_dropdown(opt_card, "Nivel de confianza (%)", self.var_confianza, ["90", "95", "99"])
        #if m["id"] == "regresion":
         #   self.var_forzar = ctk.BooleanVar(value=False)
          #  r = ctk.CTkFrame(opt_card, fg_color="transparent")
           # r.pack(fill="x", padx=16, pady=(0, 12))
            #ctk.CTkCheckBox(r, text="Forzar intercepto en cero",
             #               variable=self.var_forzar,
              #              font=(FONTS.family, FONTS.size_sm)).pack(side="left")

        # ── Acciones ──────────────────────────────────────────────────────────
        actions = ctk.CTkFrame(self.body, fg_color="transparent")
        actions.pack(fill="x", pady=(24, 0))

        ctk.CTkButton(actions, text="📥  Descargar plantilla Excel",
                      font=(FONTS.family, FONTS.size_base),
                      fg_color=COLORS.accent, hover_color=COLORS.accent_hover,
                      height=44, corner_radius=SIZES.button_radius,
                      command=self._descargar_plantilla).pack(side="left", padx=(0, 12))

        ctk.CTkButton(actions, text="Continuar → Cargar datos",
                      font=(FONTS.family, FONTS.size_base, "bold"),
                      fg_color=COLORS.primary, hover_color=COLORS.primary_hover,
                      height=44, corner_radius=SIZES.button_radius,
                      command=self._guardar_y_continuar).pack(side="left")

    # ── Picker reutilizable ───────────────────────────────────────────────────

    def _build_picker(self, parent, prefijo, default_ini_año, default_fin_año, min_meses=12):
        """Construye una fila Desde/Hasta con su resumen. prefijo = 'hist' o 'rep'."""
        var_ini_mes = ctk.StringVar(value="Enero")
        var_ini_año = ctk.StringVar(value=default_ini_año)
        var_fin_mes = ctk.StringVar(value="Diciembre")
        var_fin_año = ctk.StringVar(value=default_fin_año)

        setattr(self, f"var_{prefijo}_ini_mes", var_ini_mes)
        setattr(self, f"var_{prefijo}_ini_año", var_ini_año)
        setattr(self, f"var_{prefijo}_fin_mes", var_fin_mes)
        setattr(self, f"var_{prefijo}_fin_año", var_fin_año)

        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(10, 4))

        def _opt(var, values, w=130):
            ctk.CTkOptionMenu(row, variable=var, values=values,
                              font=(FONTS.family, FONTS.size_sm), width=w,
                              fg_color=COLORS.bg_main, text_color=COLORS.text_primary,
                              command=lambda _: _resumen()).pack(side="left", padx=(0, 5))

        ctk.CTkLabel(row, text="Desde", font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(side="left", padx=(0, 8))
        _opt(var_ini_mes, MESES)
        _opt(var_ini_año, AÑOS, 88)
        ctk.CTkLabel(row, text="Hasta", font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(side="left", padx=(12, 8))
        _opt(var_fin_mes, MESES)
        _opt(var_fin_año, AÑOS, 88)

        lbl = ctk.CTkLabel(parent, text="", font=(FONTS.family, FONTS.size_sm),
                           text_color=COLORS.text_secondary)
        lbl.pack(anchor="w", padx=16, pady=(0, 10))
        setattr(self, f"lbl_{prefijo}_resumen", lbl)

        def _resumen():
            try:
                ini = self._fecha(getattr(self, f"var_{prefijo}_ini_mes").get(),
                                  getattr(self, f"var_{prefijo}_ini_año").get())
                fin = self._fecha(getattr(self, f"var_{prefijo}_fin_mes").get(),
                                  getattr(self, f"var_{prefijo}_fin_año").get())
                n = (fin.year - ini.year) * 12 + (fin.month - ini.month) + 1
                if n <= 0:
                    lbl.configure(text="⚠  Fecha de fin anterior al inicio", text_color=COLORS.error)
                    return
                ok = n >= min_meses
                sufijo = f"  — mínimo recomendado: {min_meses}" if not ok else ""
                lbl.configure(
                    text=f"{'✓' if ok else '⚠'}  {getattr(self, f'var_{prefijo}_ini_mes').get()} "
                         f"{getattr(self, f'var_{prefijo}_ini_año').get()}  →  "
                         f"{getattr(self, f'var_{prefijo}_fin_mes').get()} "
                         f"{getattr(self, f'var_{prefijo}_fin_año').get()}  ({n} meses){sufijo}",
                    text_color=COLORS.success if ok else COLORS.warning,
                )
            except Exception:
                pass

        _resumen()

    def _toggle_reporte(self):
        if self.var_tiene_reporte.get():
            self.rep_picker_frame.pack(fill="x")
        else:
            self.rep_picker_frame.pack_forget()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fecha(mes_nombre, año):
        return date(int(año), MESES.index(mes_nombre) + 1, 1)

    def _fechas_periodo(self, prefijo):
        ini = self._fecha(getattr(self, f"var_{prefijo}_ini_mes").get(),
                          getattr(self, f"var_{prefijo}_ini_año").get())
        fin = self._fecha(getattr(self, f"var_{prefijo}_fin_mes").get(),
                          getattr(self, f"var_{prefijo}_fin_año").get())
        fechas, año, mes = [], ini.year, ini.month
        while date(año, mes, 1) <= fin:
            fechas.append(date(año, mes, 1))
            mes += 1
            if mes > 12:
                mes = 1; año += 1
        return fechas

    def _add_var_field(self):
        idx = len(self.var_entries) + 1
        row = ctk.CTkFrame(self.vars_container, fg_color="transparent")
        row.pack(fill="x", pady=3)
        entry = ctk.CTkEntry(row, placeholder_text=f"Variable {idx} (ej. Temperatura_C)",
                              font=(FONTS.family, FONTS.size_sm), height=34)
        entry.pack(side="left", fill="x", expand=True)
        self.var_entries.append(entry)
        if idx > 1:
            ctk.CTkButton(row, text="✕", width=34, height=34,
                          fg_color="#FADBD8", text_color=COLORS.error,
                          command=lambda r=row, e=entry: self._remove_var(r, e)).pack(side="left", padx=(4, 0))

    def _remove_var(self, row, entry):
        if entry in self.var_entries:
            self.var_entries.remove(entry)
        row.destroy()

    def _descargar_plantilla(self):
        self._guardar_sesion()
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"plantilla_{self.modelo['id']}.xlsx",
        )
        if not path:
            return
        vars_ind       = [e.get().strip() for e in self.var_entries if e.get().strip()]
        fechas_hist    = self._fechas_periodo("hist")
        fechas_rep     = self._fechas_periodo("rep") if self.var_tiene_reporte.get() else []
        generar_plantilla(
            path=path,
            modelo_id=self.modelo["id"],
            col_consumo=self.entry_dep.get() or "Consumo_kWh",
            vars_independientes=vars_ind,
            fechas_historico=fechas_hist,
            fechas_reporte=fechas_rep,
            nombre_proyecto=self.entry_proyecto.get(),
            unidad=self.entry_unidad.get() or "kWh",
        )
        n = len(fechas_hist) + len(fechas_rep)
        self._toast(f"Plantilla lista — {n} períodos en total ✓")

    def _guardar_y_continuar(self):
        self._guardar_sesion()
        self.app.show_page("DatosPage")

    def _guardar_sesion(self):
        s = self.app.sesion
        s.nombre_proyecto     = self.entry_proyecto.get()
        s.unidad_energia      = self.entry_unidad.get() or "kWh"
        s.col_consumo         = self.entry_dep.get() if hasattr(self, "entry_dep") else "Consumo_kWh"
        s.vars_independientes = [e.get().strip() for e in self.var_entries if e.get().strip()]
        s.nivel_confianza     = int(self.var_confianza.get()) if hasattr(self, "var_confianza") else 95
        s.tiene_reporte       = self.var_tiene_reporte.get() if hasattr(self, "var_tiene_reporte") else False
        s.periodo_historico   = (f"{self.var_hist_ini_mes.get()} {self.var_hist_ini_año.get()} – "
                                  f"{self.var_hist_fin_mes.get()} {self.var_hist_fin_año.get()}")
        if s.tiene_reporte:
            s.periodo_reporte = (f"{self.var_rep_ini_mes.get()} {self.var_rep_ini_año.get()} – "
                                  f"{self.var_rep_fin_mes.get()} {self.var_rep_fin_año.get()}")

    def _toast(self, msg):
        t = ctk.CTkToplevel(self)
        t.geometry("420x60+{}+{}".format(self.winfo_rootx()+40, self.winfo_rooty()+self.winfo_height()-80))
        t.overrideredirect(True)
        t.configure(fg_color=COLORS.success)
        ctk.CTkLabel(t, text=msg, text_color="white",
                     font=(FONTS.family, FONTS.size_sm, "bold")).pack(expand=True)
        t.after(2800, t.destroy)

    # ── Helpers UI ────────────────────────────────────────────────────────────

    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title,
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.primary).pack(anchor="w", pady=(20, 4))

    def _card(self, parent):
        card = ctk.CTkFrame(parent, fg_color=COLORS.bg_card,
                            corner_radius=SIZES.card_radius,
                            border_width=1, border_color=COLORS.border)
        card.pack(fill="x", pady=(0, 6))
        return card

    def _field(self, parent, label, placeholder="", hint=""):
        ctk.CTkLabel(parent, text=label,
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(12, 2))
        entry = ctk.CTkEntry(parent, placeholder_text=placeholder,
                              font=(FONTS.family, FONTS.size_sm), height=36)
        entry.pack(fill="x", padx=16, pady=(0, 24))
        if hint:
            ctk.CTkLabel(parent, text=hint,
                         font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary).pack(anchor="w", padx=16, pady=(0, 4))
        return entry

    def _field_dropdown(self, parent, label, var, values):
        ctk.CTkLabel(parent, text=label,
                     font=(FONTS.family, FONTS.size_sm, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkOptionMenu(parent, variable=var, values=values,
                          font=(FONTS.family, FONTS.size_sm),
                          fg_color=COLORS.bg_main,
                          text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(0, 8))
