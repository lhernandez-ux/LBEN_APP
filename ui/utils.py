# ui/utils.py
import sys
import os

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # Estamos corriendo como .exe
                # → busca el archivo en la carpeta temporal del exe
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)