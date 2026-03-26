"""
core/calculadora.py
===================
Orquestador principal.

Flujo:
  0. Ajuste No Rutinario (ANR) — corrige meses anómalos marcados por el usuario.
  1. Ajusta el modelo con df_historico (ya corregido por ANR).
  2. Genera predicciones para df_historico (línea base del período histórico).
  3. Si existe df_reporte, genera predicciones para esos datos nuevos
     y calcula desempeño y CUSUM sobre el período de reporte.
  4. Si no hay df_reporte, el análisis se hace solo sobre el histórico.
"""

import numpy as np
import pandas as pd
from typing import Optional, List

from core.models.promedio import ModeloPromedio
from core.models.cociente import ModeloCociente
from core.models.regresion import ModeloRegresion
from core.cusum import calcular_cusum

MODELOS = {
    "promedio":  ModeloPromedio,
    "cociente":  ModeloCociente,
    "regresion": ModeloRegresion,
}


def calcular(
    df_historico: pd.DataFrame,
    df_reporte:   Optional[pd.DataFrame],
    modelo_id:    str,
    col_consumo:  str,
    vars_independientes: List[str],
    nivel_confianza: int = 95,
) -> dict:
    """
    Retorna un dict con todos los vectores y métricas para la UI.
    """
    if modelo_id not in MODELOS:
        raise ValueError(f"Modelo desconocido: {modelo_id}")

    # ── 0. Ajuste No Rutinario (ANR) ─────────────────────────────────────────
    from core.ajuste_no_rutinario import aplicar_ajuste_no_rutinario, resumen_anr
    df_hist_anr, log_anr, hay_anr = aplicar_ajuste_no_rutinario(
        df_historico, col_consumo
    )
    resumen_anr_dict = resumen_anr(log_anr) if hay_anr else {}

    # ── 1. Ajustar el modelo ──────────────────────────────────────────────────
    ModeloClass = MODELOS[modelo_id]
    modelo = ModeloClass(
        df=df_hist_anr,
        col_consumo=col_consumo,
        vars_independientes=vars_independientes,
        nivel_confianza=nivel_confianza,
    )
    modelo.ajustar()

    fechas_hist  = modelo.fechas
    consumo_hist = modelo.consumo_real
    lb_hist      = modelo.linea_base
    ic_sup_hist  = modelo.ic_superior
    ic_inf_hist  = modelo.ic_inferior

    # Consumo original sin ANR (para gráfico de auditoría)
    consumo_hist_original = (
        df_historico[col_consumo].astype(float).tolist()
        if hay_anr else []
    )

    # ── 2. Predicciones para el período de reporte ────────────────────────────
    if df_reporte is not None and len(df_reporte) > 0:
        fechas_rep, consumo_rep, lb_rep, ic_sup_rep, ic_inf_rep = \
            _predecir_reporte(modelo, df_reporte, col_consumo,
                              vars_independientes, nivel_confianza)
        tiene_reporte = True
    else:
        fechas_rep = consumo_rep = lb_rep = ic_sup_rep = ic_inf_rep = []
        tiene_reporte = False

    # ── 3. Vectores de análisis ───────────────────────────────────────────────
    if tiene_reporte:
        fechas_analisis  = fechas_rep
        consumo_analisis = consumo_rep
        lb_analisis      = lb_rep
    else:
        fechas_analisis  = fechas_hist
        consumo_analisis = consumo_hist
        lb_analisis      = lb_hist

    # ── 4. Desviaciones y CUSUM ───────────────────────────────────────────────
    desv_abs = [r - b for r, b in zip(consumo_analisis, lb_analisis)]
    desv_pct = [((r - b) / b * 100) if b != 0 else 0.0
                for r, b in zip(consumo_analisis, lb_analisis)]
    cusum = calcular_cusum(desv_abs)

    # ── 5. Variable de dispersión (para gráfico de correlación) ──────────────
    # Para regresión usamos la variable principal (mayor |r de Pearson|)
    # que ya calculó el modelo y guardó en params["var_principal"].
    # Para los otros modelos usamos la primera variable independiente.
    if modelo_id == "regresion" and modelo.params.get("var_principal"):
        var_principal = modelo.params["var_principal"]
        df_para_disp  = df_hist_anr   # siempre del histórico para el gráfico
        x_disp  = df_hist_anr[var_principal].tolist() if var_principal in df_hist_anr.columns else []
        x_label = var_principal
    else:
        df_para_disp = df_reporte if tiene_reporte else df_hist_anr
        x_disp, x_label = _x_dispersion(df_para_disp, vars_independientes)

    # ── 6. KPIs, tabla de desempeño ──────────────────────────────────────────
    kpis = _calcular_kpis(consumo_analisis, lb_analisis, modelo)
    tabla, cols = _construir_tabla(
        fechas_analisis, consumo_analisis, lb_analisis, desv_abs, desv_pct
    )

    # ── 7. Tabla LBEn mensual (promedio y cociente) ───────────────────────────
    tabla_lben_m, cols_lben_m = [], []
    tabla_lben_c, cols_lben_c = [], []

    if modelo_id == "promedio":
        tabla_lben_m, cols_lben_m = _construir_tabla_lben_mensual(modelo.params)
        tabla_lben_c, cols_lben_c = _construir_tabla_lben_completa(modelo.params)
    elif modelo_id == "cociente":
        tabla_lben_m, cols_lben_m = _construir_tabla_indice_cociente(
            modelo.params, vars_independientes,
            fechas_analisis, consumo_analisis, lb_analisis
        )
        tabla_lben_c = tabla_lben_m
        cols_lben_c  = cols_lben_m
    # regresión: no tiene tabla LBEn mensual fija (la ecuación es la LBEn)

    # ── 8. modelo_params: parámetros completos para la UI ────────────────────
    # Para regresión, modelo.params ya incluye x_hist (primera var independiente
    # del histórico). Para los otros modelos lo extraemos aquí.
    params_extra = {}
    if modelo_id != "regresion":
        params_extra["x_hist"] = _x_dispersion(df_hist_anr, vars_independientes)[0]

    modelo_params = {
        **modelo.params,
        "modelo_id": modelo_id,
        **params_extra,
    }

    return {
        # Período histórico
        "fechas_hist":     fechas_hist,
        "consumo_hist":    consumo_hist,
        "lb_hist":         lb_hist,
        "ic_sup_hist":     ic_sup_hist,
        "ic_inf_hist":     ic_inf_hist,

        # Período de reporte
        "fechas_rep":      fechas_rep,
        "consumo_rep":     consumo_rep,
        "lb_rep":          lb_rep,
        "tiene_reporte":   tiene_reporte,

        # Vectores de análisis
        "fechas":          fechas_analisis,
        "consumo_real":    consumo_analisis,
        "linea_base":      lb_analisis,
        "ic_superior":     ic_sup_rep if tiene_reporte else ic_sup_hist,
        "ic_inferior":     ic_inf_rep if tiene_reporte else ic_inf_hist,
        "desviacion_abs":  desv_abs,
        "desviacion_pct":  desv_pct,
        "cusum":           cusum,

        # Dispersión (para gráfico correlación)
        "x_dispersion":    x_disp,
        "x_label":         x_label,

        # Métricas y tablas
        "kpis":               kpis,
        "tabla_desempeno":    tabla,
        "columnas_desempeno": cols,
        "modelo_id":          modelo_id,
        "modelo_params":      modelo_params,

        # Tablas LBEn mensuales
        "tabla_lben_mensual":  tabla_lben_m,
        "cols_lben_mensual":   cols_lben_m,
        "tabla_lben_completa": tabla_lben_c,
        "cols_lben_completa":  cols_lben_c,

        # Advertencias del modelo
        "advertencias_modelo": getattr(modelo, "advertencias", []),

        # Ajuste No Rutinario
        "hay_anr":               hay_anr,
        "resumen_anr":           resumen_anr_dict,
        "consumo_hist_original": consumo_hist_original,
        "fechas_hist_original":  fechas_hist if hay_anr else [],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _predecir_reporte(modelo, df_rep, col_consumo, vars_ind, nivel_confianza):
    """
    Aplica el modelo ya ajustado al período de reporte.
    Cada tipo de modelo usa su propio mecanismo de predicción.
    """
    from scipy import stats

    df = df_rep.dropna(subset=[col_consumo]).copy()
    consumo = df[col_consumo].astype(float).tolist()
    col_fecha = [c for c in df.columns
                 if c != col_consumo and c not in vars_ind][0]
    fechas = df[col_fecha].tolist()

    mid = type(modelo).__name__

    if mid == "ModeloPromedio":
        # LBEn del mes correspondiente del histórico
        from core.models.promedio import _extraer_numero_mes
        lben_mensual = modelo.params.get("lben_mensual", {})
        media_global = modelo.params.get("media",
                       float(np.mean(consumo)) if consumo else 0)
        lb = []
        for fecha in fechas:
            num_mes = _extraer_numero_mes(fecha)
            lb_mes  = lben_mensual.get(num_mes)
            lb.append(lb_mes if lb_mes is not None else media_global)

    elif mid == "ModeloCociente":
        # LBEn_período = cociente_mes × variable_período
        from core.models.promedio import _extraer_numero_mes
        col_x         = vars_ind[0]
        x             = df[col_x].astype(float).tolist()
        lben_mensual  = modelo.params.get("lben_mensual", {})
        indice_global = modelo.params.get("indice", 1.0)
        lb = []
        for fecha, xi in zip(fechas, x):
            num_mes = _extraer_numero_mes(fecha)
            coc_mes = lben_mensual.get(num_mes, indice_global)
            lb.append((coc_mes if coc_mes is not None else indice_global) * xi)

    else:
        # Regresión: aplica la ecuación ajustada directamente
        import statsmodels.api as sm
        X = np.column_stack([df[v].astype(float).values for v in vars_ind]) \
            if len(vars_ind) > 1 else df[vars_ind[0]].astype(float).values.reshape(-1, 1)
        X_const = sm.add_constant(X, has_constant="add")

        if hasattr(modelo, "_reg"):
            lb = modelo._reg.predict(X_const).tolist()
        else:
            # Fallback manual con los coeficientes
            coefs = list(modelo.coeficientes.values())
            lb = [coefs[0] + sum(c * xi for c, xi in zip(coefs[1:], row))
                  for row in X.tolist()]

    # IC usando el SEM del histórico
    sem    = modelo.params.get("sem", 0)
    n      = len(consumo)
    k      = modelo.params.get("k", 1)
    t_crit = stats.t.ppf(
        1 - (1 - nivel_confianza / 100) / 2,
        df=max(n - k - 1, 1)
    )
    ic_sup = [p + t_crit * sem for p in lb]
    ic_inf = [p - t_crit * sem for p in lb]

    return fechas, consumo, lb, ic_sup, ic_inf


def _x_dispersion(df, vars_ind):
    """Primera variable independiente para el gráfico de correlación."""
    if vars_ind and vars_ind[0] in df.columns:
        return df[vars_ind[0]].tolist(), vars_ind[0]
    return list(range(len(df))), "Período"


def _calcular_kpis(consumo_real, linea_base, modelo) -> dict:
    """
    KPIs de desempeño del análisis.
    Para regresión usa el R² real de statsmodels; para otros lo recalcula.
    """
    n      = len(consumo_real)
    err    = [r - b for r, b in zip(consumo_real, linea_base)]
    sem    = float(np.std(err, ddof=1)) if n > 1 else 0.0
    media  = float(np.mean(consumo_real)) if n > 0 else 1.0
    cv     = (sem / media * 100) if media != 0 else 0.0

    # R²: usar el del modelo si ya lo calculó (regresión), sino calcularlo aquí
    r2 = modelo.params.get("r2", None)
    if r2 is None:
        ss_res = sum(e**2 for e in err)
        ss_tot = sum((r - media)**2 for r in consumo_real)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

    kpis = {
        "r2":         round(float(r2), 4),
        "sem":        round(sem, 2),
        "cv":         round(cv, 2),
        "n_periodos": n,
    }
    if hasattr(modelo, "coeficientes"):
        kpis["coeficientes"] = modelo.coeficientes
    return kpis


def _construir_tabla(fechas, consumo_real, linea_base, desv_abs, desv_pct):
    cols = ["Período", "Consumo real", "Línea base",
            "Desviación abs.", "Desviación (%)"]
    filas = [
        [str(f), f"{r:,.2f}", f"{b:,.2f}", f"{d:+,.2f}", f"{p:+.1f}%"]
        for f, r, b, d, p in zip(fechas, consumo_real, linea_base,
                                  desv_abs, desv_pct)
    ]
    return filas, cols


def _construir_tabla_lben_mensual(modelo_params: dict) -> tuple:
    """Tabla resumida 2 columnas: Mes + LBEn. Usada en MonitoreoPage."""
    from core.models.promedio import _NOMBRES_MES
    lben = modelo_params.get("lben_mensual", {})
    cols = ["Mes", "LBEn (kWh/mes)"]
    filas = [
        [_NOMBRES_MES[mes],
         f"{lben[mes]:,.2f}" if lben.get(mes) is not None else "Sin datos"]
        for mes in range(1, 13)
    ]
    return filas, cols


def _construir_tabla_lben_completa(modelo_params: dict) -> tuple:
    """Tabla completa 6 columnas: Mes, N datos, Outliers, IC inf, LBEn, IC sup."""
    from core.models.promedio import _NOMBRES_MES
    lben      = modelo_params.get("lben_mensual", {})
    ic        = modelo_params.get("ic_mensual",   {})
    depurados = modelo_params.get("datos_depurados", {})
    outl      = modelo_params.get("outliers", {})

    cols = ["Mes", "N datos", "Outliers eliminados",
            "IC inferior", "LBEn (kWh/mes)", "IC superior"]
    filas = []
    for mes in range(1, 13):
        lb_val  = lben.get(mes)
        ic_vals = ic.get(mes, (None, None))
        n_dep   = len(depurados.get(mes, []))
        n_out   = len(outl.get(mes, []))
        filas.append([
            _NOMBRES_MES[mes],
            str(n_dep),
            str(n_out) if n_out > 0 else "—",
            f"{ic_vals[0]:,.2f}" if ic_vals[0] is not None else "—",
            f"{lb_val:,.2f}"     if lb_val    is not None else "Sin datos",
            f"{ic_vals[1]:,.2f}" if ic_vals[1] is not None else "—",
        ])
    return filas, cols


def _construir_tabla_indice_cociente(modelo_params, vars_ind,
                                     fechas, consumo, lb) -> tuple:
    """Tabla cociente: 12 meses con LBEn en kWh/unidad."""
    from core.models.promedio import _NOMBRES_MES
    lben_mensual = modelo_params.get("lben_mensual", {})
    ic_mensual   = modelo_params.get("ic_mensual",   {})
    outliers     = modelo_params.get("outliers", {})
    coc_dep      = modelo_params.get("coc_depurados", {})
    variable     = modelo_params.get("variable",
                   vars_ind[0] if vars_ind else "Variable")

    cols = ["Mes", "N datos", "Outliers eliminados",
            "IC inferior", f"LBEn (kWh/{variable})", "IC superior"]
    filas = []
    for mes in range(1, 13):
        lben_val = lben_mensual.get(mes)
        ic_vals  = ic_mensual.get(mes, (None, None))
        n_dep    = len(coc_dep.get(mes, []))
        n_out    = len(outliers.get(mes, []))
        filas.append([
            _NOMBRES_MES[mes],
            str(n_dep),
            str(n_out) if n_out > 0 else "—",
            f"{ic_vals[0]:,.4f}" if ic_vals[0] is not None else "—",
            f"{lben_val:,.4f}"   if lben_val   is not None else "Sin datos",
            f"{ic_vals[1]:,.4f}" if ic_vals[1] is not None else "—",
        ])
    return filas, cols