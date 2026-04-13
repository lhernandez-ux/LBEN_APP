"""
ui/pages/intro.py
=================
Pantalla de bienvenida con el diseño de home.py y la lógica original de intro.py
"""

import customtkinter as ctk
from PIL import Image
import os
from ui.utils import resource_path
from ui.theme import COLORS, FONTS, DIMS


class IntroPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=0)  # sidebar
        self.grid_columnconfigure(1, weight=1)  # contenido
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_contenido()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(
            self,
            fg_color=COLORS.bg_sidebar,
            width=DIMS.sidebar_width,
            corner_radius=0
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        # Espaciador superior
        ctk.CTkFrame(sidebar, fg_color="transparent", height=1).pack(expand=True)

        # Contenedor central
        cnt = ctk.CTkFrame(sidebar, fg_color="transparent")
        cnt.pack(fill="x")


        # Logo o ícono
    
        logo_path = resource_path(os.path.join("assets", "logo_lben.png"))
        if os.path.exists(logo_path):
            img = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(130, 130)
            )
            ctk.CTkLabel(cnt, image=img, text="").pack(pady=(0, 20))
        else:
            ctk.CTkLabel(
                cnt, text="⚡",
                font=(FONTS.family, 42),
                text_color=COLORS.accent
            ).pack(pady=(0, 20))

        ctk.CTkLabel(
            cnt, text="Línea Base\nEnergética",
            font=(FONTS.family, FONTS.size_lg, "bold"),
            text_color=COLORS.text_on_dark,
            justify="center"
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            cnt, text="Resolución UPME\n016 de 2024",
            font=(FONTS.family, FONTS.size_xs),
            text_color="#7A9B8E",
            justify="center"
        ).pack(pady=(0, 24))

        # Separador
        ctk.CTkFrame(cnt, fg_color="#2D4F45", height=1, width=160).pack(pady=8)

        ctk.CTkLabel(
            cnt,
            text="Modelos de referencia para\nmonitoreo del\nDesempeño Energético",
            font=(FONTS.family, FONTS.size_xs),
            text_color="#7A9B8E",
            justify="center",
            wraplength=180
        ).pack(pady=(16, 0))

        # Espaciador inferior
        ctk.CTkFrame(sidebar, fg_color="transparent", height=1).pack(expand=True)

        # Versión
        ctk.CTkLabel(
            sidebar, text="v1.0.0",
            font=(FONTS.family, FONTS.size_xs),
            text_color="#4A6B5E"
        ).pack(side="bottom", pady=16)

    # ── Contenido principal ───────────────────────────────────────────────────
    def _build_contenido(self):
        contenido = ctk.CTkFrame(self, fg_color=COLORS.bg_main, corner_radius=0)
        contenido.grid(row=0, column=1, sticky="nsew")
        contenido.grid_columnconfigure(0, weight=1)
        contenido.grid_rowconfigure(3, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        header = ctk.CTkFrame(contenido, fg_color=COLORS.bg_main, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=48, pady=(40, 0))

        ctk.CTkLabel(
            header,
            text="Bienvenido",
            font=(FONTS.family, FONTS.size_2xl, "bold"),
            text_color=COLORS.primary
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text="Esta herramienta permite establecer la línea base y monitorear el desempeño energético en Edificios,\n"
                 "de acuerdo con la Resolución 016 de 2024.",
            font=(FONTS.family, FONTS.size_md),
            text_color=COLORS.text_secondary,
            justify="left"
        ).pack(anchor="w", pady=(6, 0))

        # ── Cards de features ─────────────────────────────────────────────────
        features = ctk.CTkFrame(contenido, fg_color=COLORS.bg_main, corner_radius=0)
        features.grid(row=1, column=0, sticky="ew", padx=48, pady=(28, 0))

        self._feature_card(features, "📊", "3 Modelos",
                           "Absoluto · Cociente · Métodos Estadísticos", 0)
        self._feature_card(features, "📥", "Hojas de Cálculo",
                           "Descarga y Edita tus Datos", 1)
        self._feature_card(features, "📈", "Gráficos",
                           "Línea base · Desempeño Acum.", 2)

        # ── Rutas principales ─────────────────────────────────────────────────
        rutas = ctk.CTkFrame(contenido, fg_color=COLORS.bg_main, corner_radius=0)
        rutas.grid(row=2, column=0, sticky="ew", padx=48, pady=(28, 0))
        rutas.grid_columnconfigure((0, 1), weight=1)

        # Card Nuevo Proyecto (antes "Análisis Exploratorio")
        self._ruta_card(
            rutas,
            icono="🔍",
            titulo="Nuevo Proyecto",
            descripcion="Selecciona un modelo y configura\ntu análisis energético\ndesde cero.",
            boton_texto="Empezar",
            boton_cmd=lambda: self.app.show_page("ModelosPage"),
            destacado=True,
            col=0
        )

        # Card Abrir Monitoreo (antes "Modelado Directo")
        self._ruta_card(
            rutas,
            icono="📡",
            titulo="Abrir Monitoreo",
            descripcion="Continúa el seguimiento de\nun proyecto existente\nde desempeño energético.",
            boton_texto="Abrir",
            boton_cmd=lambda: self.app.show_page("MonitoreoPage"),
            destacado=False,
            col=1
        )

        # ── Footer ────────────────────────────────────────────────────────────
        footer = ctk.CTkFrame(contenido, fg_color=COLORS.bg_main, corner_radius=0)
        footer.grid(row=3, column=0, sticky="sew", padx=48, pady=(20, 32))
        footer.grid_columnconfigure(0, weight=1)

        # Botón guía (por ahora sin acción)
        ctk.CTkButton(
            footer,
            text="📖  Guía de uso y documentación",
            font=(FONTS.family, FONTS.size_md),
            fg_color=COLORS.bg_card,
            text_color=COLORS.primary,
            hover_color=COLORS.border,
            border_width=1,
            border_color=COLORS.border,
            corner_radius=DIMS.button_radius,
            height=44,
            command=lambda: None      # sin acción por ahora
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            footer,
            text="© 2026 — Herramienta de análisis energético  |  UPME 016/2024",
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary
        ).grid(row=1, column=0, pady=(8, 0))

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _feature_card(self, parent, icono, titulo, subtitulo, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS.bg_card,
            corner_radius=DIMS.card_radius,
            border_width=1,
            border_color=COLORS.border
        )
        card.grid(row=0, column=col,
                  padx=(0, 12) if col < 2 else 0,
                  sticky="ew")
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(
            card, text=icono,
            font=(FONTS.family, 24)
        ).pack(pady=(16, 4))

        ctk.CTkLabel(
            card, text=titulo,
            font=(FONTS.family, FONTS.size_sm, "bold"),
            text_color=COLORS.primary
        ).pack()

        ctk.CTkLabel(
            card, text=subtitulo,
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary
        ).pack(pady=(2, 16))

    def _ruta_card(self, parent, icono, titulo, descripcion,
                   boton_texto, boton_cmd, destacado, col):
        fg    = COLORS.primary if destacado else COLORS.bg_card
        txt   = COLORS.text_on_dark if destacado else COLORS.primary
        txt2  = "#A8C4BC" if destacado else COLORS.text_secondary
        btn_fg  = COLORS.accent if destacado else COLORS.primary
        btn_txt = COLORS.primary if destacado else COLORS.text_on_dark

        card = ctk.CTkFrame(
            parent,
            fg_color=fg,
            corner_radius=DIMS.card_radius,
            border_width=1,
            border_color=COLORS.border
        )
        card.grid(row=0, column=col,
                  padx=(0, 12) if col == 0 else 0,
                  sticky="nsew", pady=4)

        ctk.CTkLabel(
            card, text=icono,
            font=(FONTS.family, 28)
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            card, text=titulo,
            font=(FONTS.family, FONTS.size_lg, "bold"),
            text_color=txt
        ).pack()

        ctk.CTkLabel(
            card, text=descripcion,
            font=(FONTS.family, FONTS.size_sm),
            text_color=txt2,
            justify="center"
        ).pack(pady=(8, 16), padx=16)

        ctk.CTkButton(
            card,
            text=boton_texto,
            font=(FONTS.family, FONTS.size_sm, "bold"),
            fg_color=btn_fg,
            text_color=btn_txt,
            hover_color=COLORS.accent_hover if destacado else COLORS.primary_hover,
            corner_radius=DIMS.button_radius,
            height=38,
            command=boton_cmd
        ).pack(pady=(0, 20), padx=24, fill="x")