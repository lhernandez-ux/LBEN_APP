"""
ui/pages/intro.py
=================
Pantalla de bienvenida con branding y botón de inicio.
"""

import customtkinter as ctk
from ui.theme import COLORS, FONTS, SIZES, get_font


class IntroPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def _build(self):
        # Fondo dividido: panel izquierdo oscuro + derecho claro
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        # ── Panel izquierdo (branding) ────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color=COLORS.bg_sidebar, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")
        left.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)

        # Logo / ícono (texto grande si no hay imagen)
        icon_lbl = ctk.CTkLabel(
            left,
            text="⚡",
            font=(FONTS.family, 72),
            text_color=COLORS.accent,
        )
        icon_lbl.grid(row=1, column=0, pady=(0, 8))

        app_name = ctk.CTkLabel(
            left,
            text="Línea Base\nEnergética",
            font=(FONTS.family, FONTS.size_2xl, "bold"),
            text_color=COLORS.text_on_dark,
            justify="center",
        )
        app_name.grid(row=2, column=0, pady=(0, 12))

        tagline = ctk.CTkLabel(
            left,
            text="Modelos de referencia para\neficiencia energética ",
            font=(FONTS.family, FONTS.size_sm),
            text_color=COLORS.text_on_dark_muted,
            justify="center",
        )
        tagline.grid(row=3, column=0)

        version = ctk.CTkLabel(
            left,
            text="v1.0.0",
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_on_dark_muted,
        )
        version.grid(row=4, column=0, pady=(0, 24))

        # ── Panel derecho (contenido bienvenida) ──────────────────────────────
        right = ctk.CTkFrame(self, fg_color=COLORS.bg_main, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)
        right.grid_columnconfigure(0, weight=1)

        welcome = ctk.CTkLabel(
            right,
            text="Bienvenido",
            font=(FONTS.family, FONTS.size_3xl, "bold"),
            text_color=COLORS.text_primary,
        )
        welcome.grid(row=1, column=0, padx=60, sticky="w")

        desc = ctk.CTkLabel(
            right,
            text=(
                "Esta herramienta te permite establecer la línea base de\n"
                "consumo energético usando modelos estadísticos validados.\n\n"
                "Podrás descargar plantillas, cargar tus datos bases\n"
                "y obtener gráficos de desempeño y análisis CUSUM."
            ),
            font=(FONTS.family, FONTS.size_md),
            text_color=COLORS.text_secondary,
            justify="left",
        )
        desc.grid(row=2, column=0, padx=60, sticky="w")

        # Tarjetas de características
        features_frame = ctk.CTkFrame(right, fg_color="transparent")
        features_frame.grid(row=3, column=0, padx=60, sticky="ew", pady=(20, 0))

        features = [
            ("📊", "3 Modelos", "Promedio · Cociente · Regresión"),
            ("📥", "Plantilla Excel", "Descarga y llena tus datos"),
            ("📈", "Gráficos", "Línea base · CUSUM · Dispersión"),
        ]
        for i, (ico, title, sub) in enumerate(features):
            card = ctk.CTkFrame(features_frame, fg_color=COLORS.bg_card, corner_radius=SIZES.card_radius,
                                border_width=1, border_color=COLORS.border)
            card.grid(row=0, column=i, padx=8, sticky="ew")
            features_frame.grid_columnconfigure(i, weight=1)

            ctk.CTkLabel(card, text=ico, font=(FONTS.family, 28)).pack(pady=(16, 4))
            ctk.CTkLabel(card, text=title, font=(FONTS.family, FONTS.size_base, "bold"),
                         text_color=COLORS.text_primary).pack()
            ctk.CTkLabel(card, text=sub, font=(FONTS.family, FONTS.size_xs),
                         text_color=COLORS.text_secondary).pack(pady=(0, 16))

        # Botones de acción
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=60, sticky="w", pady=(32, 0))

        btn = ctk.CTkButton(
            btn_row,
            text="  Nuevo proyecto ",
            font=(FONTS.family, FONTS.size_lg, "bold"),
            fg_color=COLORS.primary,
            hover_color=COLORS.primary_hover,
            height=52,
            corner_radius=SIZES.button_radius,
            command=lambda: self.app.show_page("ModelosPage"),
        )
        btn.pack(side="left", padx=(0, 12))

        btn_mon = ctk.CTkButton(
            btn_row,
            text="📡  Abrir monitoreo",
            font=(FONTS.family, FONTS.size_base, "bold"),
            fg_color="transparent",
            hover_color=COLORS.primary_light,
            text_color=COLORS.primary,
            border_width=2,
            border_color=COLORS.primary,
            height=52,
            corner_radius=SIZES.button_radius,
            command=lambda: self.app.show_page("MonitoreoPage"),
        )
        btn_mon.pack(side="left")

        # Créditos
        ctk.CTkLabel(
            right,
            text="© 2026 — Herramienta de análisis energético",
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary,
        ).grid(row=6, column=0, pady=(0, 20))
