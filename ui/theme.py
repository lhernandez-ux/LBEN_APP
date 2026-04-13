"""
ui/theme.py
===========
Centro de control visual de la aplicación.
"""

from dataclasses import dataclass


@dataclass
class ColorScheme:
    # Primarios — verde oscuro institucional
    primary: str = "#1A3C34"
    primary_dark: str = "#0F2420"
    primary_hover: str = "#255C4F"
    primary_light: str = "#D5F0EB"

    # Acento — amarillo-verde energético
    accent: str = "#C8E500"
    accent_hover: str = "#D4E800"

    # Mejora / ahorro
    improvement: str = "#27AE60"
    degradation: str = "#C0392B"
    neutral: str = "#7F8C8D"

    # Fondos
    bg_main: str = "#EAEAEA"
    bg_card: str = "#FFFFFF"
    bg_sidebar: str = "#1A3C34"
    bg_sidebar_hover: str = "#255C4F"

    # Texto
    text_primary: str = "#1A1A1A"
    text_secondary: str = "#566573"
    text_white: str = "#FDFEFE"
    text_on_dark: str = "#FDFEFE"
    text_on_dark_muted: str = "#AAB7B8"

    # Bordes
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
    family      = "Inter"
    family_mono = "Courier New"

    size_xs: int = 11
    size_sm: int = 12
    size_base: int = 13
    size_md: int = 15
    size_lg: int = 18
    size_xl: int = 22
    size_2xl: int = 28
    size_3xl: int = 36
    size_title: int = 28

    weight_normal: str = "normal"
    weight_bold: str = "bold"


@dataclass
class Dimensions:
    sidebar_width: int = 190
    topbar_height: int = 52
    card_radius: int = 12
    button_radius: int = 8
    padding_sm: int = 8
    padding_md: int = 16
    padding_lg: int = 24
    padding_xl: int = 32


# ── Instancias globales ───────────────────────────────────────────────────────
COLORS = ColorScheme()
FONTS = Typography()
DIMS = Dimensions()
SIZES = DIMS


def get_font(size_attr: str = "size_base", weight: str = "normal") -> tuple:
    size = getattr(FONTS, size_attr, FONTS.size_base)
    return (FONTS.family, size, weight)


def get_chart_layout() -> dict:
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