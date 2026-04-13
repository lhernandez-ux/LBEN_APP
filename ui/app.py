"""
ui/app.py
=========
Ventana raíz y enrutador de páginas.
Nunca contiene lógica de negocio.
"""

import customtkinter as ctk
from ui.theme import COLORS
from ui.pages.intro import IntroPage
from ui.pages.modelos import ModelosPage
from ui.pages.configuracion import ConfiguracionPage
from ui.pages.datos import DatosPage
from ui.pages.resultados import ResultadosPage
from ui.pages.monitoreo import MonitoreoPage
from data.sesion import Sesion


# ── Configuración global de CustomTkinter ─────────────────────────────────────
#ctk.set_appearance_mode("light")
#ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Ventana principal. Gestiona el stack de páginas y la sesión."""

    def __init__(self):
        super().__init__()

        self.title("Línea Base Energética")
        self.geometry("1100x700")
        self.minsize(1000, 650)
        self.configure(fg_color=COLORS.bg_main)

        # Icono (opcional — coloca un archivo .ico en assets/)
        # self.iconbitmap("ui/assets/icon.ico")

        # Estado compartido entre páginas
        self.sesion = Sesion()

        # Contenedor único — las páginas se apilan aquí
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Instanciar todas las páginas
        self.pages: dict[str, ctk.CTkFrame] = {}
        for PageClass in (IntroPage, ModelosPage, ConfiguracionPage, DatosPage, ResultadosPage, MonitoreoPage):
            page = PageClass(self.container, app=self)
            name = PageClass.__name__
            self.pages[name] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.show_page("IntroPage")

    def show_page(self, name: str, **kwargs):
        """Trae una página al frente y opcionalmente le pasa datos."""
        page = self.pages[name]
        if hasattr(page, "on_enter"):
            page.on_enter(**kwargs)
        page.tkraise()
