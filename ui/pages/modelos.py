"""
ui/pages/modelos.py
===================
Selección de modelo estadístico, ordenados de menor a mayor complejidad.
"""

import customtkinter as ctk
from ui.theme import COLORS, FONTS, SIZES


MODELOS = [
    {
        "id": "promedio",
        "nombre": "Modelo de Promedio",
        "nivel": "Básico",
        "nivel_color": "#1E8449",
        "nivel_bg": "#D5F5E3",      # fondo claro del badge
        "descripcion": (
            "Estima la línea base como el promedio del consumo histórico.\n"
            "Ideal cuando el consumo es relativamente constante y no\n"
            "depende de variables externas."
        ),
        "variables": "Solo consumo energético",
        "cuando": "Procesos continuos, consumo estable",
        "icono": "═",
    },
    {
        "id": "cociente",
        "nombre": "Modelo de Cociente",
        "nivel": "Intermedio",
        "nivel_color": "#B7950B",
        "nivel_bg": "#FEF9E7",
        "descripcion": (
            "Calcula un índice de intensidad energética (consumo / variable).\n"
            "Útil cuando el consumo escala proporcionalmente con\n"
            "una variable como producción o área."
        ),
        "variables": "Consumo + 1 variable (ej. producción)",
        "cuando": "Industria con producción variable",
        "icono": "÷",
    },
    {
        "id": "regresion",
        "nombre": "Regresión Lineal",
        "nivel": "Avanzado",
        "nivel_color": "#1A5276",
        "nivel_bg": "#D6EAF8",
        "descripcion": (
            "Modela el consumo en función de una o múltiples variables\n"
            "independientes usando mínimos cuadrados. Entrega R², SEM\n"
            "y permite detectar ahorros estadísticamente significativos."
        ),
        "variables": "Consumo + 1 o más variables independientes",
        "cuando": "Edificios, plantas con múltiples factores",
        "icono": "∿",
    },
]


class ModelosPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=COLORS.bg_main)
        self.app = app
        self._build()

    def _build(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ── Encabezado ────────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=COLORS.bg_card, corner_radius=0,
                               border_width=0, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        ctk.CTkButton(header, text="← Inicio", width=80, height=32,
                      fg_color="transparent", hover_color=COLORS.bg_main,
                      text_color=COLORS.text_secondary,
                      font=(FONTS.family, FONTS.size_sm),
                      command=lambda: self.app.show_page("IntroPage")).pack(side="left", padx=16, pady=14)

        ctk.CTkLabel(header, text="Selecciona el modelo estadístico",
                     font=(FONTS.family, FONTS.size_lg, "bold"),
                     text_color=COLORS.text_primary).pack(side="left", padx=8)

        # ── Contenido ─────────────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=40, pady=30)
        scroll.grid_columnconfigure((0, 1, 2), weight=1)

        subtitle = ctk.CTkLabel(
            scroll,
            text="Los modelos están ordenados de menor a mayor complejidad. Elige el que mejor\nse adapte a tus datos y objetivos de análisis.",
            font=(FONTS.family, FONTS.size_base),
            text_color=COLORS.text_secondary,
            justify="left",
        )
        subtitle.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 24))

        for i, modelo in enumerate(MODELOS):
            self._card(scroll, modelo, i)

    def _card(self, parent, modelo: dict, col: int):
        card = ctk.CTkFrame(parent, fg_color=COLORS.bg_card, corner_radius=SIZES.card_radius,
                            border_width=1, border_color=COLORS.border)
        card.grid(row=1, column=col, padx=10, sticky="nsew")

        # Icono grande
        ctk.CTkLabel(card, text=modelo["icono"],
                     font=(FONTS.family, 48, "bold"),
                     text_color=modelo["nivel_color"]).pack(pady=(28, 4))

        # Nivel badge
        badge_frame = ctk.CTkFrame(card, fg_color=modelo["nivel_bg"],
                                   corner_radius=12, height=24)
        badge_frame.pack(pady=(0, 8))
        ctk.CTkLabel(badge_frame, text=f"  {modelo['nivel']}  ",
                     font=(FONTS.family, FONTS.size_xs, "bold"),
                     text_color=modelo["nivel_color"]).pack()

        # Título
        ctk.CTkLabel(card, text=modelo["nombre"],
                     font=(FONTS.family, FONTS.size_md, "bold"),
                     text_color=COLORS.text_primary).pack(padx=20)

        # Descripción
        ctk.CTkLabel(card, text=modelo["descripcion"],
                     font=(FONTS.family, FONTS.size_sm),
                     text_color=COLORS.text_secondary,
                     justify="left", wraplength=240).pack(padx=20, pady=(8, 4))

        # Info pills
        info_frame = ctk.CTkFrame(card, fg_color=COLORS.bg_main, corner_radius=8)
        info_frame.pack(padx=20, pady=8, fill="x")

        ctk.CTkLabel(info_frame, text="Variables:",
                     font=(FONTS.family, FONTS.size_xs, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=10, pady=(8, 0))
        ctk.CTkLabel(info_frame, text=modelo["variables"],
                     font=(FONTS.family, FONTS.size_xs),
                     text_color=COLORS.text_secondary).pack(anchor="w", padx=10)

        ctk.CTkLabel(info_frame, text="Recomendado para:",
                     font=(FONTS.family, FONTS.size_xs, "bold"),
                     text_color=COLORS.text_primary).pack(anchor="w", padx=10, pady=(6, 0))
        ctk.CTkLabel(info_frame, text=modelo["cuando"],
                     font=(FONTS.family, FONTS.size_xs),
                     text_color=COLORS.text_secondary).pack(anchor="w", padx=10, pady=(0, 8))

        # Botón seleccionar
        ctk.CTkButton(
            card,
            text=f"Seleccionar →",
            font=(FONTS.family, FONTS.size_base, "bold"),
            fg_color=modelo["nivel_color"],
            hover_color=COLORS.primary_hover,
            height=40,
            corner_radius=SIZES.button_radius,
            command=lambda m=modelo: self.app.show_page("ConfiguracionPage", modelo=m),
        ).pack(padx=20, pady=(8, 24), fill="x")
