"""
core/models/cociente.py
=======================
Modelo de Cociente — Resolución UPME 16 de 2024, Numeral 7.5.2

Metodología:
  1. Para cada período i: Cociente_i = kWh_i / Variable_i
  2. Agrupar cocientes por mes del año (ene, feb, ..., dic)
  3. Para cada mes: calcular promedio del cociente → LBEn_mes (kWh/unidad)
  4. Intervalo de confianza:
       - n < 10 datos: ±10% del promedio (Ec. 7)
       - n ≥ 10 datos: promedio ± 2*DesvEst (Ec. 4 y 5)
  5. Eliminar cocientes fuera del IC → recalcular promedio → LBEn final
  6. LBEn por período = LBEn_mes × Variable_período

La comparación en reporte se hace sobre el cociente real vs LBEn_mes.
ññññ
"""

import numpy as np
from core.models.base import ModeloBase
from core.models.promedio import _extraer_numero_mes, _NOMBRES_MES


class ModeloCociente(ModeloBase):

    def ajustar(self):
        df, y, fechas = self._extraer_vectores()

        if not self.vars_independientes:
            raise ValueError("El modelo de cociente requiere al menos una variable independiente.")
        col_x = self.vars_independientes[0]
        if col_x not in df.columns:
            raise ValueError(f"Columna '{col_x}' no encontrada en los datos.")

        x = df[col_x].astype(float).tolist()
        n = len(y)

        # ── PASO 1: Calcular cociente por período ─────────────────────────────
        # Cociente_i = kWh_i / Variable_i
        cocientes = []
        for yi, xi in zip(y, x):
            if xi != 0:
                cocientes.append(yi / xi)
            else:
                cocientes.append(None)  # Variable = 0, no se puede calcular

        # ── PASO 2: Agrupar cocientes por mes del año ─────────────────────────
        cocientes_por_mes = {m: [] for m in range(1, 13)}
        x_por_mes         = {m: [] for m in range(1, 13)}
        indices_por_mes   = {m: [] for m in range(1, 13)}
        años_por_mes      = {m: [] for m in range(1, 13)}

        for i, (coc, xi, fecha) in enumerate(zip(cocientes, x, fechas)):
            num_mes = _extraer_numero_mes(fecha)
            if num_mes == 0 or coc is None:
                continue
            # Extraer año real
            año_val = None
            if hasattr(fecha, "year"):
                año_val = int(fecha.year)
            else:
                import re as _re
                m_yr = _re.search(r"(\d{4})", str(fecha))
                if m_yr:
                    año_val = int(m_yr.group(1))
            cocientes_por_mes[num_mes].append(float(coc))
            x_por_mes[num_mes].append(float(xi))
            indices_por_mes[num_mes].append(i)
            años_por_mes[num_mes].append(año_val)

        # ── PASO 3-5: Para cada mes: promedio → IC → depurar → LBEn ──────────
        lben_mensual    = {}   # {mes: promedio_cociente_depurado}  (kWh/unidad)
        ic_mensual      = {}   # {mes: (ic_inf, ic_sup)}
        coc_depurados   = {}   # {mes: [cocientes dentro del IC]}
        outliers        = {}   # {mes: [cocientes eliminados]}
        advertencias    = []

        for mes in range(1, 13):
            valores = cocientes_por_mes[mes]

            if len(valores) == 0:
                advertencias.append(f"{_NOMBRES_MES[mes]}: sin datos históricos.")
                lben_mensual[mes] = None
                ic_mensual[mes]   = (None, None)
                coc_depurados[mes] = []
                outliers[mes]      = []
                continue

            if len(valores) < 3:
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: solo {len(valores)} dato(s). "
                    f"Se recomienda mínimo 3."
                )

            # Promedio inicial del cociente
            prom_inicial = float(np.mean(valores))

            # Intervalo de confianza (Ec. 7 resolución UPME)
            if len(valores) < 10:
                # ±10% del promedio
                ic_inf = prom_inicial * 0.9
                ic_sup = prom_inicial * 1.1
            else:
                # ±2 * DesvEst poblacional (Ec. 4 y 5)
                desv_est = float(np.sqrt(
                    sum((v - prom_inicial) ** 2 for v in valores) / len(valores)
                ))
                ic_inf = prom_inicial - 2 * desv_est
                ic_sup = prom_inicial + 2 * desv_est

            ic_mensual[mes] = (round(ic_inf, 6), round(ic_sup, 6))

            # Depuración: eliminar fuera del IC
            dentro = [v for v in valores if ic_inf <= v <= ic_sup]
            fuera  = [v for v in valores if v < ic_inf or v > ic_sup]

            coc_depurados[mes] = dentro
            outliers[mes]      = fuera

            if fuera:
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: {len(fuera)} cociente(s) eliminado(s) "
                    f"fuera del IC [{ic_inf:.4f} – {ic_sup:.4f}]: "
                    f"{[round(v, 4) for v in fuera]}"
                )

            if len(dentro) == 0:
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: todos los cocientes fuera del IC. "
                    f"Se usa el promedio inicial."
                )
                lben_mensual[mes] = round(prom_inicial, 6)
            else:
                lben_mensual[mes] = round(float(np.mean(dentro)), 6)

        # ── PASO 6: Construir vectores de salida ──────────────────────────────
        # LBEn por período = LBEn_mes (cociente) × Variable_período
        linea_base = []
        ic_sup_vec = []
        ic_inf_vec = []

        # Cociente global de fallback (promedio de todos los LBEn mensuales)
        lben_vals_validos = [v for v in lben_mensual.values() if v is not None]
        coc_global = float(np.mean(lben_vals_validos)) if lben_vals_validos else 1.0

        for fecha, xi in zip(fechas, x):
            num_mes   = _extraer_numero_mes(fecha)
            coc_mes   = lben_mensual.get(num_mes)
            if coc_mes is None:
                coc_mes = coc_global

            ic_m = ic_mensual.get(num_mes, (None, None))
            ic_inf_m = ic_m[0] if ic_m[0] is not None else coc_mes * 0.9
            ic_sup_m = ic_m[1] if ic_m[1] is not None else coc_mes * 1.1

            # LBEn en kWh = cociente × variable
            lb_periodo    = coc_mes   * xi
            ic_sup_periodo = ic_sup_m * xi
            ic_inf_periodo = ic_inf_m * xi

            linea_base.append(lb_periodo)
            ic_sup_vec.append(ic_sup_periodo)
            ic_inf_vec.append(ic_inf_periodo)

        # SEM para IC en reporte (basado en dispersión de cocientes históricos)
        todos_cocientes = []
        for m in range(1, 13):
            todos_cocientes.extend(coc_depurados[m])
        sem_cociente = float(np.std(todos_cocientes, ddof=1)) if len(todos_cocientes) > 1 else 0.0

        self.consumo_real = y
        self.linea_base   = linea_base
        self.ic_superior  = ic_sup_vec
        self.ic_inferior  = ic_inf_vec
        self.fechas       = fechas
        self.advertencias = advertencias

        self.params = {
            "lben_mensual":    lben_mensual,    # {mes: cociente_depurado kWh/unidad}
            "ic_mensual":      ic_mensual,
            "coc_depurados":   coc_depurados,
            "outliers":        outliers,
            "variable":        col_x,
            "advertencias":    advertencias,
            "sem":             round(sem_cociente, 6),
            "n_total":         n,
            # Índice global (promedio de los 12 LBEn mensuales) — fallback
            "indice":          round(coc_global, 6),
            "años_por_mes":    años_por_mes,
        }

        self.coeficientes = {
            f"LBEn {_NOMBRES_MES[m]} ({col_x})": round(v, 4)
            for m, v in lben_mensual.items() if v is not None
        }
