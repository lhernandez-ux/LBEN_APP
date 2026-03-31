"""
core/models/base.py
===================
Clase base abstracta para todos los modelos de línea base.
Define la interfaz que deben implementar promedio, cociente y regresión.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import pandas as pd
import numpy as np
from scipy import stats


class ModeloBase(ABC):
    """
    Interfaz común para todos los modelos estadísticos.

    Atributos que deben estar disponibles después de ajustar():
        consumo_real  : list[float]
        linea_base    : list[float]
        ic_superior   : list[float]
        ic_inferior   : list[float]
        fechas        : list
        params        : dict   — parámetros internos del modelo
    """

    def __init__(
        self,
        df: pd.DataFrame,
        col_consumo: str,
        vars_independientes: List[str],
        nivel_confianza: int = 95,
        frecuencia: str = "mensual",  # ← NUEVO PARÁMETRO con valor por defecto
    ):
        self.df                 = df.copy()
        self.col_consumo        = col_consumo
        self.vars_independientes = vars_independientes
        self.alpha              = 1 - nivel_confianza / 100
        self.nivel_confianza    = nivel_confianza
        self.frecuencia         = frecuencia  # ← ALMACENAR FRECUENCIA

        # Salidas — se llenan en ajustar()
        self.consumo_real: List[float] = []
        self.linea_base:   List[float] = []
        self.ic_superior:  List[float] = []
        self.ic_inferior:  List[float] = []
        self.fechas:       list        = []
        self.params:       dict        = {}

    @abstractmethod
    def ajustar(self) -> None:
        """Realiza el ajuste del modelo y llena todos los atributos."""
        ...

    # ── Helpers de uso común ─────────────────────────────────────────────────

    def _extraer_vectores(self):
        """Extrae y limpia Y y fecha del DataFrame."""
        df = self.df.dropna(subset=[self.col_consumo])
        y = df[self.col_consumo].astype(float).tolist()

        # Fechas: primera columna que no sea la de consumo
        fecha_col = [c for c in df.columns if c != self.col_consumo]
        fechas = df[fecha_col[0]].tolist() if fecha_col else list(range(len(y)))

        return df, y, fechas

    def _intervalo_confianza_mean(self, y: list, y_pred: list, alpha: float, n_params: int = 1):
        """
        Calcula intervalos de confianza para predicciones de la media.
        Retorna (ic_superior, ic_inferior).
        """
        n = len(y)
        errores = [r - p for r, p in zip(y, y_pred)]
        sem = float(np.std(errores, ddof=n_params))
        t_crit = stats.t.ppf(1 - alpha / 2, df=max(n - n_params, 1))
        margen = t_crit * sem

        ic_sup = [p + margen for p in y_pred]
        ic_inf = [p - margen for p in y_pred]
        return ic_sup, ic_inf