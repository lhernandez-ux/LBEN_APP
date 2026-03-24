"""
ui/theme.py
===========
Centro de control visual de la aplicación.
Cambia colores, fuentes y tamaños AQUÍ sin tocar ninguna otra pantalla.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ColorScheme:
    # Primarios
    primary: str = "#1B4F72"          # Azul oscuro institucional
    primary_hover: str = "#2E86C1"
    primary_light: str = "#D6EAF8"

    # Acento verde energía
    accent: str = "#1E8449"
    accent_hover: str = "#27AE60"
    accent_light: str = "#D5F5E3"

    # Mejora / ahorro (CUSUM verde)
    improvement: str = "#27AE60"
    degradation: str = "#C0392B"
    neutral: str = "#7F8C8D"

    # Fondos
    bg_main: str = "#F0F3F4"
    bg_card: str = "#FFFFFF"
    bg_sidebar: str = "#1B2631"
    bg_sidebar_hover: str = "#2C3E50"

    # Texto
    text_primary: str = "#1C2833"
    text_secondary: str = "#566573"
    text_on_dark: str = "#FDFEFE"
    text_on_dark_muted: str = "#AAB7B8"

    # Bordes / separadores
    border: str = "#D5D8DC"
    border_light: str = "#EBF5FB"

    # Gráficos
    chart_baseline: str = "#2E86C1"
    chart_real: str = "#E74C3C"
    chart_predicted: str = "#F39C12"
    chart_cusum_pos: str = "#27AE60"
    chart_cusum_neg: str = "#C0392B"

    # Estados
    success: str = "#1E8449"
    warning: str = "#B7950B"
    error: str = "#922B21"
    info: str = "#1A5276"


@dataclass
class Typography:
    # Fuente principal — cámbiala aquí para toda la app
    family: str = "Segoe UI"          # Windows / mac: cambia a "SF Pro Display" o "Helvetica Neue"
    family_mono: str = "Consolas"

    # Tamaños
    size_xs: int = 10
    size_sm: int = 12
    size_base: int = 13
    size_md: int = 15
    size_lg: int = 18
    size_xl: int = 22
    size_2xl: int = 28
    size_3xl: int = 36

    # Pesos (CustomTkinter usa strings)
    weight_normal: str = "normal"
    weight_bold: str = "bold"


@dataclass
class Sizing:
    sidebar_width: int = 220
    header_height: int = 60
    card_radius: int = 12
    button_radius: int = 8
    padding_sm: int = 8
    padding_md: int = 16
    padding_lg: int = 24
    padding_xl: int = 32


# ── Instancias globales (importa desde aquí) ──────────────────────────────────
COLORS = ColorScheme()
FONTS = Typography()
SIZES = Sizing()


def get_font(size_attr: str = "size_base", weight: str = "normal") -> tuple:
    """Retorna una tupla (familia, tamaño, peso) compatible con tkinter."""
    size = getattr(FONTS, size_attr, FONTS.size_base)
    return (FONTS.family, size, weight)


def get_chart_layout() -> dict:
    """Retorna el layout base de Plotly con el estilo de la app."""
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": COLORS.bg_card,
        "font": {"family": FONTS.family, "color": COLORS.text_primary, "size": 12},
        "title_font": {"family": FONTS.family, "size": 15, "color": COLORS.text_primary},
        "legend": {
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": COLORS.border,
            "borderwidth": 1,
        },
        "margin": {"l": 60, "r": 30, "t": 50, "b": 50},
        "xaxis": {
            "gridcolor": COLORS.border_light,
            "linecolor": COLORS.border,
            "showgrid": True,
            "zeroline": False,
            "tickangle": -90,
            "tickfont": {"size": 11},
        },
        "yaxis": {
            "gridcolor": COLORS.border_light,
            "linecolor": COLORS.border,
            "showgrid": True,
            "zeroline": False,
        },
        "hovermode": "x unified",
    }
