"""
core/models/regresion.py
========================
Modelo Estadístico de Regresión Lineal — Resolución UPME 16/2024

  Y = β₀ + β₁·X₁ + β₂·X₂ + ... + βₖ·Xₖ + ε

Datos que exige la resolución UPME 16/2024:
  - Ecuación ajustada con coeficientes
  - R² ≥ 0.75  (variación explicada por el modelo)
  - CV(RMSE) ≤ 20%  (precisión del modelo)
  - p-valor < 0.05 por variable (significancia estadística)
  - Correlación de Pearson (r) entre cada variable y el consumo
  - F-estadístico (significancia global del modelo)
  - VIF si hay más de una variable (multicolinealidad)
  - Mínimo 3 períodos por variable independiente

Variable principal para gráfico:
  La que tenga mayor correlación absoluta con el consumo (|r de Pearson|).
  Esto garantiza que el gráfico de correlación siempre muestre
  la relación más relevante, incluso en regresión múltiple.
"""

import numpy as np
import statsmodels.api as sm
from scipy import stats

from core.models.base import ModeloBase


class ModeloRegresion(ModeloBase):

    def ajustar(self):
        df, y, fechas = self._extraer_vectores()
        n = len(y)
        k = len(self.vars_independientes)

        # ── Validaciones previas ──────────────────────────────────────────────
        if k == 0:
            raise ValueError("La regresión requiere al menos una variable independiente.")
        if n < k * 3:
            raise ValueError(
                f"Datos insuficientes: con {k} variable(s) se necesitan al menos "
                f"{k * 3} períodos (tienes {n})."
            )

        # ── PASO 1: Matriz X ──────────────────────────────────────────────────
        X_cols = []
        for col in self.vars_independientes:
            if col not in df.columns:
                raise ValueError(f"Columna '{col}' no encontrada en los datos.")
            X_cols.append(df[col].astype(float).values)

        X       = np.column_stack(X_cols) if k > 1 else X_cols[0].reshape(-1, 1)
        y_arr   = np.array(y, dtype=float)
        X_const = sm.add_constant(X, has_constant="add")

        # ── PASO 2: OLS ───────────────────────────────────────────────────────
        ols        = sm.OLS(y_arr, X_const).fit()
        intercepto = float(ols.params[0])
        coefs_vals = ols.params[1:].tolist()
        linea_base = ols.fittedvalues.tolist()

        # ── PASO 3: Bondad de ajuste ──────────────────────────────────────────
        r2          = float(ols.rsquared)
        r2_ajustado = float(ols.rsquared_adj)
        aic         = float(ols.aic)
        bic         = float(ols.bic)
        f_stat      = float(ols.fvalue)   if ols.fvalue   is not None else 0.0
        p_valor_f   = float(ols.f_pvalue) if ols.f_pvalue is not None else 1.0

        # p-valores y t-estadísticos por variable
        p_valores = {
            col: round(float(pv), 6)
            for col, pv in zip(self.vars_independientes, ols.pvalues[1:])
        }
        t_stats = {
            col: round(float(tv), 4)
            for col, tv in zip(self.vars_independientes, ols.tvalues[1:])
        }

        # ── PASO 4: Correlación de Pearson por variable ───────────────────────
        # r de Pearson entre cada variable independiente y el consumo.
        # La resolución lo usa para verificar que cada variable realmente
        # impacta el consumo. También sirve para elegir la variable principal
        # del gráfico de correlación.
        pearson_r = {}
        for col, x_col in zip(self.vars_independientes, X_cols):
            r_val, _ = stats.pearsonr(x_col, y_arr)
            pearson_r[col] = round(float(r_val), 4)

        # Variable con mayor correlación absoluta → eje X del gráfico
        var_principal = max(pearson_r, key=lambda c: abs(pearson_r[c]))
        idx_principal = self.vars_independientes.index(var_principal)
        x_hist_principal = X_cols[idx_principal].tolist()

        # ── PASO 5: RMSE y CV(RMSE) ───────────────────────────────────────────
        residuos = [yi - yp for yi, yp in zip(y, linea_base)]
        rmse     = float(np.sqrt(np.mean([e**2 for e in residuos])))
        media_y  = float(np.mean(y))
        cv_rmse  = (rmse / media_y * 100) if media_y != 0 else 0.0

        # ── PASO 6: VIF — solo si hay más de una variable ─────────────────────
        vif = {}
        if k > 1:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            for i, col in enumerate(self.vars_independientes):
                vif[col] = round(float(variance_inflation_factor(X_const, i + 1)), 2)

        # ── PASO 7: Intervalo de confianza ────────────────────────────────────
        sem    = float(np.std(residuos, ddof=k + 1)) if n > k + 1 else rmse
        t_crit = stats.t.ppf(1 - self.alpha / 2, df=max(n - k - 1, 1))
        ic_sup = [yp + t_crit * sem for yp in linea_base]
        ic_inf = [yp - t_crit * sem for yp in linea_base]

        # ── PASO 8: Advertencias según Resolución UPME ────────────────────────
        advertencias = []

        # 8.1 R² mínimo recomendado 0.75
        if r2 < 0.75:
            advertencias.append(
                f"R² = {r2:.3f} está por debajo del mínimo recomendado (0.75). "
                "El modelo explica poco la variación del consumo."
            )
        
        # 8.2 CV(RMSE) ≤ 20%
        if cv_rmse > 20:
            advertencias.append(
                f"CV(RMSE) = {cv_rmse:.1f}% supera el límite recomendado del 20%. "
                "El error es alto respecto al consumo promedio."
            )
        
        # 8.3 p-valor < 0.05 por variable
        vars_no_sig = [col for col, pv in p_valores.items() if pv >= 0.05]
        if vars_no_sig:
            advertencias.append(
                f"Variable(s) no significativa(s) (p ≥ 0.05): "
                f"{', '.join(vars_no_sig)}. Considera eliminarlas del modelo."
            )
        
        # 8.4 VIF > 10 indica multicolinealidad alta
        if vif:
            vars_vif = [col for col, v in vif.items() if v > 10]
            if vars_vif:
                advertencias.append(
                    f"Multicolinealidad alta (VIF > 10) en: "
                    f"{', '.join(vars_vif)}. Las variables pueden estar correlacionadas."
                )
        
        # 8.5 Modelo global no significativo
        if p_valor_f >= 0.05:
            advertencias.append(
                f"El modelo global no es significativo (F p-valor = {p_valor_f:.4f}). "
                "Las variables no explican el consumo mejor que el azar."
            )
        
        # 8.6 Correlaciones bajas (|r| < 0.50)
        vars_corr_baja = [col for col, r in pearson_r.items() if abs(r) < 0.50]
        if vars_corr_baja:
            advertencias.append(
                f"Correlación baja con el consumo (|r| < 0.50) en: "
                f"{', '.join(vars_corr_baja)}. Verifica si estas variables son relevantes."
            )
        
        # 8.7 Verificar que hay al menos 3 períodos por variable (ya validado arriba)

        # ── PASO 9: Coeficientes y params ─────────────────────────────────────
        coefs_dict = {"Intercepto": round(intercepto, 6)}
        for nombre, val in zip(self.vars_independientes, coefs_vals):
            coefs_dict[nombre] = round(val, 6)

        self.params = {
            # Ecuación del modelo
            "coeficientes":    coefs_dict,
            # Bondad de ajuste (requeridos por la resolución)
            "r2":              round(r2, 4),
            "r2_ajustado":     round(r2_ajustado, 4),
            "rmse":            round(rmse, 4),
            "cv_rmse":         round(cv_rmse, 2),
            # Significancia estadística
            "p_valores":       p_valores,
            "t_estadisticos":  t_stats,
            "f_estadistico":   round(f_stat, 4),
            "p_valor_f":       round(p_valor_f, 6),
            # Correlación de Pearson por variable (requerida por resolución)
            "pearson_r":       pearson_r,
            "var_principal":   var_principal,   # variable con mayor |r|
            # Multicolinealidad
            "vif":             vif,
            # Criterios de información
            "aic":             round(aic, 2),
            "bic":             round(bic, 2),
            # Para IC en reporte
            "sem":             round(sem, 4),
            "n":               n,
            "k":               k,
            # Eje X del gráfico = variable principal (mayor |r con consumo|)
            "x_hist":          x_hist_principal,
            "advertencias":    advertencias,
        }

        # ── Atributos base ────────────────────────────────────────────────────
        self.consumo_real = y
        self.linea_base   = linea_base
        self.ic_superior  = ic_sup
        self.ic_inferior  = ic_inf
        self.fechas       = fechas
        self.coeficientes = coefs_dict
        self.advertencias = advertencias
        self._reg         = ols