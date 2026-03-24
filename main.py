"""
Herramienta de Línea Base Energética
Punto de entrada principal de la aplicación.
"""

import sys
import os

# Asegura que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(__file__))

from ui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
