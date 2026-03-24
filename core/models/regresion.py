"""
core/models/regresion.py
========================
Modelo de Regresión Lineal — VERSIÓN BASE (pendiente de fórmulas definitivas)

TODO: Reemplazar los cálculos marcados con # ← FÓRMULA con la lógica real.

Puede ser regresión simple (1 variable) o múltiple (varias variables).
"""

import numpy as np
from core.models.base import ModeloBase


class ModeloRegresion(ModeloBase):

    def ajustar(self):
        df, y, fechas = self._extraer_vectores()
        # y      = lista de consumos históricos
        # fechas = etiquetas de período

        if not self.vars_independientes:
            raise ValueError("La regresión requiere al menos una variable independiente.")

        # Construye la matriz de variables independientes
        X_cols = []
        for col in self.vars_independientes:
            if col not in df.columns:
                raise ValueError(f"Columna '{col}' no encontrada.")
            X_cols.append(df[col].astype(float).tolist())
        # X_cols = lista de listas, una por variable
        # Si vars = ['Produccion', 'Temperatura']:
        #   X_cols = [[980, 900, ...], [18, 22, ...]]

        n = len(y)
        k = len(X_cols)  # número de variables independientes

        # ══════════════════════════════════════════════════════════════════════
        # BLOQUE 1 — COEFICIENTES DE LA REGRESIÓN
        # Encuentra los valores β₀, β₁, β₂, ... que mejor ajustan:
        #   y = β₀ + β₁·x₁ + β₂·x₂ + ... + ε
        #
        # Datos disponibles:
        #   y       → lista de n consumos (variable dependiente)
        #   X_cols  → lista de listas con las variables independientes
        #   n       → número de períodos
        #   k       → número de variables independientes
        #
        # Debes producir:
        #   intercepto    → float (β₀, consumo base cuando variables = 0)
        #   coeficientes  → lista de k floats [β₁, β₂, ...] uno por variable
        #
        # PLACEHOLDER actual (OLS con numpy o statsmodels):
        X = np.column_stack(X_cols) if k > 1 else np.array(X_cols[0]).reshape(-1, 1)
        X_const = np.column_stack([np.ones(n), X])  # agrega columna de 1s para β₀

        try:
            # Solución analítica: β = (XᵀX)⁻¹ Xᵀy
            beta = np.linalg.lstsq(X_const, y, rcond=None)[0]  # ← FÓRMULA
            intercepto   = float(beta[0])
            coeficientes_vals = beta[1:].tolist()
        except Exception:
            intercepto = float(np.mean(y))
            coeficientes_vals = [0.0] * k
        # ══════════════════════════════════════════════════════════════════════

        # ══════════════════════════════════════════════════════════════════════
        # BLOQUE 2 — LÍNEA BASE (predicciones del modelo)
        # Aplica los coeficientes para predecir el consumo de cada período.
        #
        # Datos disponibles:
        #   intercepto, coeficientes_vals, X_cols, n
        #
        # Debes producir:
        #   linea_base → lista de n valores predichos (ŷ)
        #
        # PLACEHOLDER actual:
        linea_base = []
        for i in range(n):
            pred = intercepto + sum(c * X_cols[j][i]
                                    for j, c in enumerate(coeficientes_vals))  # ← FÓRMULA
            linea_base.append(pred)
        # ══════════════════════════════════════════════════════════════════════

        # ══════════════════════════════════════════════════════════════════════
        # BLOQUE 3 — R² (bondad de ajuste)
        # Mide qué tan bien explica el modelo la variación del consumo.
        # R²=1 = ajuste perfecto. R²=0 = no explica nada.
        # Mínimo recomendado según ISO 50006 / ASHRAE Guideline 14: R² ≥ 0.75
        #
        # Datos disponibles:
        #   y, linea_base
        #
        # Debes producir:
        #   r2 → float entre 0 y 1
        #
        # PLACEHOLDER actual:
        media_y  = float(np.mean(y))
        ss_res   = sum((yi - yp) ** 2 for yi, yp in zip(y, linea_base))  # ← FÓRMULA
        ss_tot   = sum((yi - media_y) ** 2 for yi in y)                  # ← FÓRMULA
        r2       = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0           # ← FÓRMULA
        # ══════════════════════════════════════════════════════════════════════

        # ══════════════════════════════════════════════════════════════════════
        # BLOQUE 4 — INTERVALO DE CONFIANZA
        # Banda alrededor de cada predicción.
        # En regresión el IC varía por período (no es constante como en promedio).
        #
        # Datos disponibles:
        #   y, linea_base, self.alpha, n, k
        #
        # Debes producir:
        #   ic_sup → lista de n valores
        #   ic_inf → lista de n valores
        #
        # PLACEHOLDER actual (±t*SEM de los residuos):
        from scipy import stats
        errores = [yi - yp for yi, yp in zip(y, linea_base)]
        sem     = float(np.std(errores, ddof=k + 1)) if n > k + 1 else 0.0  # ← FÓRMULA
        t_crit  = stats.t.ppf(1 - self.alpha / 2, df=max(n - k - 1, 1))     # ← FÓRMULA
        ic_sup  = [yp + t_crit * sem for yp in linea_base]                   # ← FÓRMULA
        ic_inf  = [yp - t_crit * sem for yp in linea_base]                   # ← FÓRMULA
        # ══════════════════════════════════════════════════════════════════════

        # ══════════════════════════════════════════════════════════════════════
        # BLOQUE 5 — PARÁMETROS DEL MODELO
        # IMPORTANTE: el dict "coeficientes" es usado en calculadora.py y en
        # chart_widget.py para construir la ecuación del gráfico.
        # Estructura esperada:
        #   {"Intercepto": β₀, "NombreVar1": β₁, "NombreVar2": β₂, ...}
        #
        # Agrega aquí todos los diagnósticos que quieras mostrar:
        #   r2, r2_ajustado, p_valores, VIF, AIC, BIC, etc.
        coefs_dict = {"Intercepto": round(intercepto, 6)}
        for nombre, val in zip(self.vars_independientes, coeficientes_vals):
            coefs_dict[nombre] = round(val, 6)

        params = {
            "coeficientes": coefs_dict,    # ← IMPORTANTE: mantén esta estructura
            "r2":           round(r2, 4),
            "sem":          round(sem, 4),
            "n":            n,
            "k":            k,
            # Agrega aquí: "r2_ajustado", "p_valores", "vif", "aic", "bic"
            # cuando tengas los cálculos listos
        }
        # ══════════════════════════════════════════════════════════════════════

        # — No tocar desde aquí hacia abajo —
        self.consumo_real = y
        self.linea_base   = linea_base
        self.ic_superior  = ic_sup
        self.ic_inferior  = ic_inf
        self.fechas       = fechas
        self.params       = params
        self.coeficientes = coefs_dict
