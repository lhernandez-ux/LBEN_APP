"""
ui/pages/modelos.py
===================
Selección de modelo estadístico.
Estilo visual de seleccion_modelo.py, lógica original de modelos.py.
"""

import customtkinter as ctk
from PIL import Image
import os
from ui.utils import resource_path
from ui.theme import COLORS, FONTS, DIMS


MODELOS = [
    {
        "id": "promedio",
        "nombre": "Consumo Absoluto",
        "subtitulo": "Promedios Mensuales",
        "icono_archivo": "m1_icon.png",
        "descripcion": (
            "Estima la línea base como el promedio del "
            "consumo histórico mensual.\n\n"
            "Ideal cuando el consumo es relativamente "
            "constante y no depende o no se dispone de variables externas."
        ),
        "variables": "Solo consumo energético",
        "cuando": "Procesos continuos, consumo estable",
    },
    {
        "id": "cociente",
        "nombre": "Modelo de Cociente",
        "subtitulo": "Consumo Normalizado",
        "icono_archivo": "m2_icon.png",
        "descripcion": (
            "Calcula un índice de consumo energético "
            "normalizado por una variable (Ej: kWh/visitantes).\n\n"
            "Útil cuando el consumo escala proporcionalmente con una sola "
            "variable como usuarios o área."
        ),
        "variables": "Consumo + 1 variable (ej. producción)",
        "cuando": "Edificios con ocupación variable",
    },
    {
        "id": "regresion",
        "nombre": "Método Estadístico",
        "subtitulo": "Regresión Lineal",
        "icono_archivo": "m3_icon.png",
        "descripcion": (
            "Calcula el consumo en función de una o más "
            "variables independientes estadísticamente "
            "significativas.\n\n"
            "Puede detectar relaciones complejas entre variables"
        ),
        "variables": "Consumo + 1 o más variables significativas",
        "cuando": "Edificios con múltiples variables disponibles",
    },
]


class ModelosPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_topbar()
        self._build_cuerpo()

    # ── Topbar ────────────────────────────────────────────────────────────────
    def _build_topbar(self):
        topbar = ctk.CTkFrame(
            self, fg_color=COLORS.bg_card,
            corner_radius=0, height=DIMS.topbar_height
        )
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(1, weight=1)

        # Línea acento inferior
        ctk.CTkFrame(
            topbar, fg_color=COLORS.accent,
            height=2, corner_radius=0
        ).place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        ctk.CTkButton(
            topbar,
            text="← Inicio",
            font=(FONTS.family, FONTS.size_sm),
            fg_color="transparent",
            text_color=COLORS.primary,
            hover_color=COLORS.bg_main,
            width=90, height=32,
            corner_radius=DIMS.button_radius,
            command=lambda: self.app.show_page("IntroPage")
        ).grid(row=0, column=0, padx=16, pady=8, sticky="w")

        ctk.CTkLabel(
            topbar,
            text="Selecciona el modelo de LBEn",
            font=(FONTS.family, FONTS.size_md, "bold"),
            text_color=COLORS.primary
        ).grid(row=0, column=1, sticky="w", padx=8)

    # ── Cuerpo ────────────────────────────────────────────────────────────────
    def _build_cuerpo(self):
        cuerpo = ctk.CTkFrame(self, fg_color=COLORS.bg_main, corner_radius=0)
        cuerpo.grid(row=1, column=0, sticky="nsew")
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            cuerpo,
            text="Elige el modelo que mejor se adapte a tus datos y objetivos."
                 " Aparecerá resaltado el modelo recomendado en el ultimo análisis exploratorio",
            font=(FONTS.family, FONTS.size_sm),
            text_color=COLORS.text_secondary,
            justify="left"
        ).grid(row=0, column=0, sticky="w", padx=48, pady=(24, 16))

        cards_frame = ctk.CTkFrame(cuerpo, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="nsew", padx=48, pady=(0, 32))
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)
        cards_frame.grid_rowconfigure(0, weight=1)

        for col, modelo in enumerate(MODELOS):
            self._build_card(cards_frame, modelo, col)



    # ── Card ──────────────────────────────────────────────────────────────────
    def _build_card(self, parent, modelo, col):
        card = ctk.CTkFrame(
            parent,
            fg_color=COLORS.bg_card,
            corner_radius=DIMS.card_radius,
            border_width=1,
            border_color=COLORS.border
        )
        card.grid(
            row=0, column=col,
            padx=(0, 12) if col < 2 else 0,
            sticky="nsew", pady=4
        )
        card.grid_columnconfigure(0, weight=1)

        # Espaciador superior
        ctk.CTkFrame(
            card, fg_color="transparent", height=24
        ).grid(row=0, column=0, pady=(16, 0))

        # Ícono — imagen PNG o fallback emoji
        
        icon_path = resource_path(os.path.join("assets", modelo["icono_archivo"]))
        try:
            pil_img = Image.open(icon_path)
            ctk_img = ctk.CTkImage(
                light_image=pil_img, dark_image=pil_img, size=(48, 48)
            )
            ctk.CTkLabel(
                card, text="", image=ctk_img
            ).grid(row=1, column=0, padx=16, pady=(8, 0), sticky="w")
        except Exception:
            ctk.CTkLabel(
                card, text="📊",
                font=(FONTS.family, 32),
                text_color=COLORS.primary
            ).grid(row=1, column=0, padx=16, pady=(8, 0), sticky="w")

        # Título
        ctk.CTkLabel(
            card,
            text=modelo["nombre"],
            font=(FONTS.family, FONTS.size_md, "bold"),
            text_color=COLORS.primary
        ).grid(row=2, column=0, padx=16, pady=(16, 0), sticky="w")

        # Subtítulo
        ctk.CTkLabel(
            card,
            text=modelo["subtitulo"],
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary
        ).grid(row=3, column=0, padx=16, pady=(0, 12), sticky="w")

        # Separador
        ctk.CTkFrame(
            card, fg_color=COLORS.border, height=1, corner_radius=0
        ).grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))

        # Descripción
        ctk.CTkLabel(
            card,
            text=modelo["descripcion"],
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary,
            wraplength=240,
            justify="center"
        ).grid(row=5, column=0, padx=16, pady=(0, 16))

        # Fila elástica — empuja info box y botón al fondo
        card.grid_rowconfigure(6, weight=1)
        ctk.CTkFrame(card, fg_color="transparent", height=1).grid(row=6, column=0)

        # Info box
        info_frame = ctk.CTkFrame(
            card, fg_color=COLORS.bg_main, corner_radius=8
        )
        info_frame.grid(row=7, column=0, sticky="ew", padx=16, pady=(0, 12))

        ctk.CTkLabel(
            info_frame, text="Variables:",
            font=(FONTS.family, FONTS.size_xs, "bold"),
            text_color=COLORS.text_primary, anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 2))

        ctk.CTkLabel(
            info_frame, text=modelo["variables"],
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary, anchor="w",
            wraplength=220, justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 4))

        ctk.CTkLabel(
            info_frame, text="Recomendado para:",
            font=(FONTS.family, FONTS.size_xs, "bold"),
            text_color=COLORS.text_primary, anchor="w"
        ).pack(anchor="w", padx=12, pady=(4, 2))

        ctk.CTkLabel(
            info_frame, text=modelo["cuando"],
            font=(FONTS.family, FONTS.size_xs),
            text_color=COLORS.text_secondary, anchor="w",
            wraplength=220, justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Botón
        ctk.CTkButton(
            card,
            text="Seleccionar →",
            font=(FONTS.family, FONTS.size_sm, "bold"),
            fg_color=COLORS.primary,
            text_color=COLORS.text_white,
            hover_color=COLORS.primary_hover,
            corner_radius=DIMS.button_radius,
            height=40,
            command=lambda m=modelo: self.app.show_page("ConfiguracionPage", modelo=m)
        ).grid(row=8, column=0, padx=16, pady=(0, 20), sticky="ew")