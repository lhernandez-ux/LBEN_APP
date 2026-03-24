"""
ui/components/tabla_widget.py
==============================
Tabla de desempeño con celdas bien espaciadas y filas coloreadas.
"""

import customtkinter as ctk
from ui.theme import COLORS, FONTS

_BG_MEJORA   = "#D5F5E3"
_BG_DEGRADAR = "#FADBD8"
_ROW_H       = 34    # altura de cada fila en píxeles


class TablaWidget(ctk.CTkFrame):
    def __init__(self, parent, filas: list, columnas: list, **kwargs):
        super().__init__(parent, fg_color=COLORS.bg_card,
                         corner_radius=12, border_width=1,
                         border_color=COLORS.border, **kwargs)
        self._filas    = filas
        self._columnas = columnas
        self._build()

    def _build(self):
        # Título
        ctk.CTkLabel(self, text="Tabla de desempeño",
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=16, pady=(14, 6))

        if not self._columnas:
            ctk.CTkLabel(self, text="Sin datos disponibles",
                         text_color=COLORS.text_secondary,
                         font=(FONTS.family, FONTS.size_sm)).pack(pady=20)
            return

        # Índice de columna de desviación
        try:
            desv_idx = self._columnas.index("Desviación (%)")
        except ValueError:
            desv_idx = -1

        # Scroll para tablas grandes
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        n_cols = len(self._columnas)
        for c in range(n_cols):
            scroll.grid_columnconfigure(c, weight=1, minsize=90)

        # ── Encabezados ───────────────────────────────────────────────────────
        for c, col in enumerate(self._columnas):
            hdr = ctk.CTkFrame(scroll, fg_color=COLORS.primary,
                               corner_radius=0, height=_ROW_H + 4)
            hdr.grid(row=0, column=c, sticky="ew", padx=1, pady=(0, 2))
            hdr.grid_propagate(False)
            ctk.CTkLabel(hdr, text=col,
                         font=(FONTS.family, FONTS.size_xs, "bold"),
                         text_color="white").place(relx=0.5, rely=0.5, anchor="center")

        # ── Filas ─────────────────────────────────────────────────────────────
        for r, fila in enumerate(self._filas):
            # Color de fondo de toda la fila
            bg = COLORS.bg_card if r % 2 == 0 else COLORS.bg_main
            if desv_idx >= 0:
                try:
                    val = float(
                        str(fila[desv_idx])
                        .replace("%", "").replace("+", "")
                        .replace(",", ".").strip()
                    )
                    if val < -2:
                        bg = _BG_MEJORA
                    elif val > 2:
                        bg = _BG_DEGRADAR
                except (ValueError, IndexError):
                    pass

            for c, valor in enumerate(fila):
                cell = ctk.CTkFrame(scroll, fg_color=bg,
                                    corner_radius=0, height=_ROW_H)
                cell.grid(row=r + 1, column=c, sticky="ew", padx=1, pady=1)
                cell.grid_propagate(False)

                # Color especial para columna de desviación
                txt_color = COLORS.text_primary
                if desv_idx >= 0 and c == desv_idx:
                    try:
                        v = float(str(valor).replace("%","").replace("+","")
                                  .replace(",",".").strip())
                        txt_color = COLORS.improvement if v <= 0 else COLORS.degradation
                    except (ValueError, IndexError):
                        pass

                ctk.CTkLabel(cell, text=str(valor),
                             font=(FONTS.family, FONTS.size_xs),
                             text_color=txt_color).place(relx=0.5, rely=0.5, anchor="center")
