import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

# Redirigir errores a un archivo log en el escritorio
log_path = os.path.join(os.path.expanduser("~"), "Desktop", "lben_error.txt")
sys.stderr = open(log_path, "w", encoding="utf-8")
sys.stdout = open(log_path, "a", encoding="utf-8")

try:
    from ui.app import App
    app = App()
    app.mainloop()
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    sys.stderr.close()