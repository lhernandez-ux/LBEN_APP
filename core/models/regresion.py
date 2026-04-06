"""
core/models/regresion.py
========================
Modelo Estadístico de Regresión Lineal — Resolución UPME 16/2024

  Y = β₀ + β₁·X₁ + β₂·X₂ + ... + βₖ·Xₖ + ε

Requisitos según Resolución UPME 16/2024 (sección 7.5.3 y Anexo 3):

  1. Normalización del consumo a 30 días (ecuación 1 de la resolución).
     Consumo_normalizado = (Consumo_factura / Días_facturación) × 30
     ─ Esto se aplica ANTES de llamar al modelo (en la carga de datos),
       pero el modelo lo verifica y advierte si detecta variación sospechosa.

  2. Selección de variables relevantes:
     ─ Se corre una regresión inicial con TODAS las variables suministradas.
     ─ Cualquier variable con p-value ≥ 0.05 se elimina.
     ─ Se recorre el modelo sin las variables no significativas (stepwise
       backward según la resolución: "correr nuevamente el modelo estadístico
       sin tener en cuenta la variable que no produce cambios significativos").
     ─ Si ninguna variable resulta significativa, se lanza advertencia crítica.

  3. Estadísticos exigidos por la resolución:
     ─ R² y R² ajustado.
     ─ P-value por variable (columna Probabilidad del output de Excel).
     ─ F-estadístico y su p-value (significancia global).
     ─ CV(RMSE) ≤ 20 % (precisión del modelo).
     ─ VIF si hay más de una variable (multicolinealidad).
     ─ Correlación de Pearson (r) entre cada variable y el consumo.

  4. Verificación del modelo:
     ─ % Error por observación = (consumo_real − LBEn) / LBEn × 100.
     ─ Error promedio reportado (resolución lo muestra en Anexo 3).
     ─ Advertencia si más del 20 % de observaciones superan el 5 % de error.

  5. Línea meta (Anexo 3, resolución UPME 16/2024):
     ─ Se identifican los puntos donde consumo_real < LBEn (mejores desempeños).
     ─ Con esos puntos se corre una nueva regresión lineal simple con la
       variable principal (mayor |r de Pearson|).
     ─ La línea meta es la ecuación resultante de esa regresión de mejores
       desempeños evaluada sobre el rango completo de la variable principal.
     ─ Potencial de ahorro mensual = LBEn - línea_meta (para cada período).

  6. Variable principal para gráfico:
     ─ La que tenga mayor |r de Pearson| con el consumo.

  7. Mínimo de datos:
     ─ Al menos 3 períodos por variable independiente (la resolución recomienda
       mínimo 36 datos mensuales —3 años— pero acepta menos si se justifica).
"""

import numpy as np
import statsmodels.api as sm
from scipy import stats

from core.models.base import ModeloBase


# ── Constante de nivel de confianza recomendado por la resolución ─────────────
_NIVEL_CONFIANZA_RESOLUCION = 0.95  # 95 % (sección 7.5.3)
_PVALUE_UMBRAL = 0.05               # Umbral de significancia (sección 7.5.3)
_CV_MAXIMO = 20.0                   # CV(RMSE) máximo recomendado (%)
_R2_MINIMO = 0.75                   # R² mínimo recomendado (sección 7.4.3)
_VIF_MAXIMO = 10.0                  # VIF máximo antes de advertir multicolinealidad
_PEARSON_MINIMO = 0.50              # |r| mínimo para considerar variable relevante
_ERROR_OBS_MAX = 0.05               # 5 % de error por observación (Anexo 3)
_PROP_OBS_ERROR = 0.20              # Se advierte si > 20 % de obs. superan el umbral


class ModeloRegresion(ModeloBase):
    """
    Implementa el modelo estadístico de regresión lineal según la
    Resolución UPME 16 de 2024.

    Flujo interno
    ─────────────
    1. Validaciones previas (datos mínimos, columnas existentes).
    2. Regresión inicial con todas las variables.
    3. Selección backward: elimina variables con p-value ≥ 0.05 y recorre.
    4. Cálculo de estadísticos completos sobre el modelo final.
    5. Verificación del modelo (% error por observación).
    6. Línea meta: regresión sobre los mejores desempeños (Anexo 3).
    7. Construcción de advertencias según umbrales de la resolución.
    """

    def ajustar(self):
        df, y, fechas = self._extraer_vectores()
        n = len(y)
        k_inicial = len(self.vars_independientes)

        # ── 1. Validaciones previas ───────────────────────────────────────────
        if k_inicial == 0:
            raise ValueError(
                "La regresión requiere al menos una variable independiente."
            )
        if n < k_inicial * 3:
            raise ValueError(
                f"Datos insuficientes: con {k_inicial} variable(s) se necesitan "
                f"al menos {k_inicial * 3} períodos (tiene {n}). "
                "La resolución UPME 16/2024 recomienda mínimo 36 datos (3 años)."
            )
        for col in self.vars_independientes:
            if col not in df.columns:
                raise ValueError(f"Columna '{col}' no encontrada en los datos.")

        y_arr = np.array(y, dtype=float)

        # ── 2. Selección backward de variables según resolución ───────────────
        # "Si el valor presentado [p-value] es mayor a 0.05, se considera que
        #  dicha variable no produce cambios significativos en los consumos de
        #  energía por lo que resulta adecuado correr nuevamente el modelo
        #  estadístico sin tener en cuenta la variable que no produce cambios
        #  significativos." — sección 7.5.3
        vars_activas = list(self.vars_independientes)
        vars_eliminadas = []
        historial_eliminacion = []

        while True:
            X_cols_act = [df[v].astype(float).values for v in vars_activas]
            X_act = (
                np.column_stack(X_cols_act)
                if len(X_cols_act) > 1
                else X_cols_act[0].reshape(-1, 1)
            )
            X_const_act = sm.add_constant(X_act, has_constant="add")
            ols_act = sm.OLS(y_arr, X_const_act).fit()

            pvals_act = {
                v: float(pv)
                for v, pv in zip(vars_activas, ols_act.pvalues[1:])
            }

            # Variable con mayor p-value (la menos significativa)
            peor_var = max(pvals_act, key=lambda v: pvals_act[v])

            if pvals_act[peor_var] >= _PVALUE_UMBRAL:
                vars_eliminadas.append(peor_var)
                historial_eliminacion.append(
                    f"'{peor_var}' eliminada (p-value = {pvals_act[peor_var]:.4f} ≥ {_PVALUE_UMBRAL})"
                )
                vars_activas.remove(peor_var)
                if not vars_activas:
                    break
            else:
                break

        # ── 3. Modelo final ───────────────────────────────────────────────────
        if not vars_activas:
            vars_activas = list(self.vars_independientes)
            sin_vars_sig = True
        else:
            sin_vars_sig = False

        X_cols_fin = [df[v].astype(float).values for v in vars_activas]
        X_fin = (
            np.column_stack(X_cols_fin)
            if len(X_cols_fin) > 1
            else X_cols_fin[0].reshape(-1, 1)
        )
        k_fin = len(vars_activas)
        X_const_fin = sm.add_constant(X_fin, has_constant="add")
        ols = sm.OLS(y_arr, X_const_fin).fit()

        intercepto = float(ols.params[0])
        coefs_vals = ols.params[1:].tolist()
        linea_base = ols.fittedvalues.tolist()

        # ── 4. Estadísticos del modelo final ─────────────────────────────────
        r2          = float(ols.rsquared)
        r2_ajustado = float(ols.rsquared_adj)
        aic         = float(ols.aic)
        bic         = float(ols.bic)
        f_stat      = float(ols.fvalue)   if ols.fvalue   is not None else 0.0
        p_valor_f   = float(ols.f_pvalue) if ols.f_pvalue is not None else 1.0

        p_valores = {
            col: round(float(pv), 6)
            for col, pv in zip(vars_activas, ols.pvalues[1:])
        }
        t_stats = {
            col: round(float(tv), 4)
            for col, tv in zip(vars_activas, ols.tvalues[1:])
        }

        # 4a. Correlación de Pearson por variable
        pearson_r = {}
        for col, x_col in zip(vars_activas, X_cols_fin):
            r_val, _ = stats.pearsonr(x_col, y_arr)
            pearson_r[col] = round(float(r_val), 4)

        # Variable con mayor |r| → eje X del gráfico de correlación
        var_principal = max(pearson_r, key=lambda c: abs(pearson_r[c]))
        idx_principal = vars_activas.index(var_principal)
        x_hist_principal = X_cols_fin[idx_principal].tolist()

        # 4b. RMSE y CV(RMSE)
        residuos = [float(yi) - float(yp) for yi, yp in zip(y, linea_base)]
        rmse     = float(np.sqrt(np.mean([e ** 2 for e in residuos])))
        media_y  = float(np.mean(y))
        cv_rmse  = (rmse / media_y * 100) if media_y != 0 else 0.0

        # 4c. VIF (multicolinealidad)
        vif = {}
        if k_fin > 1:
            from statsmodels.stats.outliers_influence import variance_inflation_factor
            for i, col in enumerate(vars_activas):
                vif[col] = round(
                    float(variance_inflation_factor(X_const_fin, i + 1)), 2
                )

        # 4d. Intervalo de confianza al 95 %
        sem    = float(np.std(residuos, ddof=k_fin + 1)) if n > k_fin + 1 else rmse
        t_crit = stats.t.ppf(
            1 - (1 - self.nivel_confianza / 100) / 2,
            df=max(n - k_fin - 1, 1),
        )
        ic_sup = [yp + t_crit * sem for yp in linea_base]
        ic_inf = [yp - t_crit * sem for yp in linea_base]

        # ── 5. Verificación del modelo (Anexo 3, resolución) ─────────────────
        errores_pct = []
        for yi, yp in zip(y, linea_base):
            if yp != 0:
                errores_pct.append(abs((yi - yp) / yp) * 100)
            else:
                errores_pct.append(0.0)

        error_promedio = float(np.mean(errores_pct))
        n_obs_sobre_5pct = sum(1 for e in errores_pct if e > 5.0)
        prop_sobre_5pct  = n_obs_sobre_5pct / n if n > 0 else 0.0

        # ── 6. Línea meta — Mejores desempeños energéticos (Anexo 3) ─────────
        # Según la resolución (sección 8.1, Anexo 3):
        #   "Diferencia en el mes m = valor real − valor LBEn"
        #   "Aquellos resultados donde la diferencia es negativa representan
        #    el mejor desempeño energético."
        #   Con esos puntos se construye una nueva regresión (línea de tendencia)
        #   usando la variable principal, y el potencial de ahorro = LBEn - línea_meta.

        x_principal_arr = np.array(x_hist_principal, dtype=float)

        # Índices donde consumo_real < LBEn (mejores desempeños)
        indices_mejores = [
            i for i, (yi, yp) in enumerate(zip(y, linea_base))
            if float(yi) < float(yp)
        ]

        linea_meta           = None   # valores de la línea meta para cada período
        coef_meta            = None   # (intercepto_meta, pendiente_meta)
        r2_meta              = None
        potencial_ahorro_abs = None   # kWh/mes de ahorro potencial por período
        potencial_ahorro_pct = None   # % de ahorro potencial por período
        ahorro_promedio_pct  = None
        # Puntos para marcar en el gráfico: (x, y_real, índice, es_mejor_desempeno)
        puntos_mejor_desempeno = []

        if len(indices_mejores) >= 2:
            x_meta = x_principal_arr[indices_mejores]
            y_meta = np.array([float(y[i]) for i in indices_mejores])

            # Regresión lineal simple sobre los mejores desempeños
            X_meta_const = sm.add_constant(x_meta.reshape(-1, 1), has_constant="add")
            ols_meta = sm.OLS(y_meta, X_meta_const).fit()

            intercepto_meta = float(ols_meta.params[0])
            pendiente_meta  = float(ols_meta.params[1])
            r2_meta         = float(ols_meta.rsquared)
            coef_meta       = (intercepto_meta, pendiente_meta)

            # Evaluar la línea meta para TODOS los períodos (usando x_principal)
            linea_meta = [
                pendiente_meta * float(xi) + intercepto_meta
                for xi in x_principal_arr
            ]

            # Potencial de ahorro = LBEn - línea_meta (positivo = hay ahorro)
            potencial_ahorro_abs = [
                round(float(lb) - float(lm), 2)
                for lb, lm in zip(linea_base, linea_meta)
            ]
            potencial_ahorro_pct = [
                round((float(lb) - float(lm)) / float(lb) * 100, 2)
                if float(lb) != 0 else 0.0
                for lb, lm in zip(linea_base, linea_meta)
            ]
            ahorro_promedio_pct = round(
                float(np.mean([p for p in potencial_ahorro_pct if p > 0] or [0.0])), 2
            )

        # Construir lista de puntos para el gráfico de correlación,
        # clasificados como "mejor desempeño" o "sobre LBEn"
        for i in range(n):
            es_mejor = float(y[i]) < float(linea_base[i])
            puntos_mejor_desempeno.append({
                "x":          float(x_principal_arr[i]),
                "y_real":     float(y[i]),
                "y_lben":     float(linea_base[i]),
                "es_mejor":   es_mejor,
                "periodo":    str(fechas[i]) if i < len(fechas) else str(i + 1),
            })

        # ── 7. Advertencias según Resolución UPME 16/2024 ────────────────────
        advertencias = []

        if historial_eliminacion:
            advertencias.append(
                "Selección automática de variables (backward stepwise, "
                "resolución UPME 16/2024 sección 7.5.3): "
                + "; ".join(historial_eliminacion)
                + ". El modelo final usa: "
                + ", ".join(vars_activas) + "."
            )

        if sin_vars_sig:
            advertencias.append(
                "⚠ CRÍTICO: Ninguna variable independiente resultó significativa "
                "(p-value ≥ 0.05 en todas). El modelo no cumple los requisitos de "
                "la resolución UPME 16/2024. Revise las variables seleccionadas."
            )

        if r2 < _R2_MINIMO:
            advertencias.append(
                f"R² = {r2:.4f} está por debajo del mínimo recomendado "
                f"({_R2_MINIMO}). El modelo explica el {r2*100:.1f}% de la "
                "variación del consumo. Un R² bajo indica alto potencial de "
                "ahorro por control operacional (resolución UPME 16/2024, "
                "sección 7.5.3)."
            )

        if cv_rmse > _CV_MAXIMO:
            advertencias.append(
                f"CV(RMSE) = {cv_rmse:.1f}% supera el límite recomendado del "
                f"{_CV_MAXIMO}%. El error relativo es alto respecto al consumo "
                "promedio. Considere agregar variables relevantes adicionales."
            )

        if p_valor_f >= _PVALUE_UMBRAL:
            advertencias.append(
                f"El modelo global no es estadísticamente significativo "
                f"(F p-value = {p_valor_f:.4f} ≥ {_PVALUE_UMBRAL}). Las variables "
                "no explican el consumo mejor que el azar."
            )

        if vif:
            vars_vif_alto = [col for col, v in vif.items() if v > _VIF_MAXIMO]
            if vars_vif_alto:
                advertencias.append(
                    f"Multicolinealidad alta (VIF > {_VIF_MAXIMO}) en: "
                    f"{', '.join(vars_vif_alto)}. Considere eliminar una de las "
                    "variables correlacionadas para mejorar la estabilidad del modelo."
                )

        vars_corr_baja = [
            col for col, r in pearson_r.items() if abs(r) < _PEARSON_MINIMO
        ]
        if vars_corr_baja:
            advertencias.append(
                f"Correlación baja con el consumo (|r| < {_PEARSON_MINIMO}) en: "
                f"{', '.join(vars_corr_baja)}. Verifique si estas variables son "
                "realmente relevantes para el consumo energético."
            )

        if prop_sobre_5pct > _PROP_OBS_ERROR:
            advertencias.append(
                f"Verificación del modelo (Anexo 3, resolución UPME 16/2024): "
                f"{n_obs_sobre_5pct} de {n} observaciones ({prop_sobre_5pct*100:.1f}%) "
                f"presentan un error > 5%. Error promedio: {error_promedio:.2f}%. "
                "El modelo puede no estimar de forma confiable el consumo de energía."
            )

        if len(indices_mejores) < 2:
            advertencias.append(
                "Línea meta: no se encontraron suficientes períodos con consumo "
                "por debajo de la LBEn (mínimo 2) para construir la línea meta "
                "de mejores desempeños (Anexo 3, resolución UPME 16/2024)."
            )

        # ── 8. Coeficientes y ecuación final ─────────────────────────────────
        coefs_dict = {"Intercepto": round(intercepto, 6)}
        for nombre, val in zip(vars_activas, coefs_vals):
            coefs_dict[nombre] = round(val, 6)

        partes_ec = [f"{intercepto:+.4f}"]
        for nombre, val in zip(vars_activas, coefs_vals):
            signo = "+" if val >= 0 else ""
            partes_ec.append(f"{signo}{val:.4f}·{nombre}")
        ecuacion_str = "E = " + " ".join(partes_ec)

        # ── 9. Ecuación de la línea meta (para mostrar en gráfico) ───────────
        ecuacion_meta_str = None
        if coef_meta is not None:
            i_meta, p_meta = coef_meta
            signo_m = "+" if i_meta >= 0 else ""
            ecuacion_meta_str = (
                f"E_meta = {p_meta:.4f}·{var_principal} {signo_m}{i_meta:.4f}  "
                f"(R²={r2_meta:.3f})"
            )

        # ── 10. Verificación por observación (tabla para la UI) ───────────────
        tabla_verificacion = []
        for i, (yi, yp, ep) in enumerate(zip(y, linea_base, errores_pct)):
            fila = {
                "periodo":       str(fechas[i]) if i < len(fechas) else str(i + 1),
                "consumo_real":  round(float(yi), 2),
                "consumo_lben":  round(float(yp), 2),
                "error_pct":     round(ep, 2),
                "supera_umbral": ep > 5.0,
                "es_mejor_desempeno": float(yi) < float(yp),
            }
            if linea_meta is not None:
                fila["consumo_meta"]         = round(float(linea_meta[i]), 2)
                fila["potencial_ahorro_abs"] = round(float(potencial_ahorro_abs[i]), 2)
                fila["potencial_ahorro_pct"] = round(float(potencial_ahorro_pct[i]), 2)
            tabla_verificacion.append(fila)

        # ── 11. Guardar params ────────────────────────────────────────────────
        self.params = {
            # ── Ecuación del modelo ──────────────────────────────────────────
            "coeficientes":          coefs_dict,
            "ecuacion":              ecuacion_str,
            "vars_activas":          vars_activas,
            "vars_eliminadas":       vars_eliminadas,
            "historial_eliminacion": historial_eliminacion,

            # ── Bondad de ajuste ─────────────────────────────────────────────
            "r2":                    round(r2, 4),
            "r2_ajustado":           round(r2_ajustado, 4),
            "rmse":                  round(rmse, 4),
            "cv_rmse":               round(cv_rmse, 2),

            # ── Significancia estadística ────────────────────────────────────
            "p_valores":             p_valores,
            "t_estadisticos":        t_stats,
            "f_estadistico":         round(f_stat, 4),
            "p_valor_f":             round(p_valor_f, 6),

            # ── Correlación de Pearson ───────────────────────────────────────
            "pearson_r":             pearson_r,
            "var_principal":         var_principal,

            # ── Multicolinealidad ────────────────────────────────────────────
            "vif":                   vif,

            # ── Criterios de información ─────────────────────────────────────
            "aic":                   round(aic, 2),
            "bic":                   round(bic, 2),

            # ── Verificación del modelo (Anexo 3) ────────────────────────────
            "error_promedio_pct":    round(error_promedio, 2),
            "n_obs_sobre_5pct":      n_obs_sobre_5pct,
            "prop_sobre_5pct":       round(prop_sobre_5pct * 100, 1),
            "tabla_verificacion":    tabla_verificacion,

            # ── Línea meta — Mejores desempeños (Anexo 3) ────────────────────
            "linea_meta":                 [round(v, 2) for v in linea_meta] if linea_meta else [],
            "coef_meta":                  list(coef_meta) if coef_meta else [],
            "r2_meta":                    round(r2_meta, 4) if r2_meta is not None else None,
            "ecuacion_meta":              ecuacion_meta_str,
            "potencial_ahorro_abs":       potencial_ahorro_abs or [],
            "potencial_ahorro_pct":       potencial_ahorro_pct or [],
            "ahorro_promedio_pct":        ahorro_promedio_pct or 0.0,
            "n_mejores_desempenos":       len(indices_mejores),
            "indices_mejores_desempenos": indices_mejores,
            "puntos_mejor_desempeno":     puntos_mejor_desempeno,

            # ── Para IC en predicción del período de reporte ─────────────────
            "sem":                   round(sem, 4),
            "n":                     n,
            "k":                     k_fin,

            # ── Eje X del gráfico de correlación ─────────────────────────────
            "x_hist":                x_hist_principal,

            # ── Advertencias ─────────────────────────────────────────────────
            "advertencias":          advertencias,
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
        self._vars_activas = vars_activas


# ─────────────────────────────────────────────────────────────────────────────
# Función auxiliar: normalización a 30 días (ecuación 1, resolución UPME 16/2024)
# ─────────────────────────────────────────────────────────────────────────────

def normalizar_consumo_30_dias(consumo_factura: float, dias_facturacion: int) -> float:
    """
    Normaliza el consumo registrado en factura a un período estándar de 30 días.

    Ecuación 1 — Resolución UPME 16/2024, sección 7.5:
        Consumo_normalizado = (Consumo_factura / Días_facturación) × 30
    """
    if dias_facturacion <= 0:
        raise ValueError(
            f"Los días de facturación deben ser positivos (recibido: {dias_facturacion})."
        )
    return (consumo_factura / dias_facturacion) * 30