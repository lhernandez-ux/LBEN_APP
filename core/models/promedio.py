"""
core/models/promedio.py
=======================
Modelo de Valor Absoluto de Energía
Resolución UPME 16 de 2024 — Numeral 7.5.1

Lógica según la resolución:
  1. Normalizar consumos a 30 días (si el df tiene columna de días de facturación)
  2. Agrupar los datos por MES del año (enero, febrero, ..., diciembre)
  3. Para cada mes: calcular promedio de todos los años disponibles
  4. Verificar con intervalo de confianza ±10%
     - Si hay < 10 datos por mes → IC = promedio ± 10%
     - Si hay >= 10 datos por mes → IC = promedio ± 2*DesvEst
  5. Eliminar valores fuera del IC y recalcular el promedio
  6. Resultado: 12 valores de línea base (uno por mes del año)
  7. Para el período de reporte: asignar a cada mes real su LBEn mensual
"""

import re
import numpy as np
from core.models.base import ModeloBase


# ── Mapa de abreviaturas de mes a número ──────────────────────────────────────
_MESES_ABREV = {
    "ene": 1, "jan": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4, "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8, "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12, "dec": 12,
}

_NOMBRES_MES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo",  6: "Junio",   7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _extraer_numero_mes(fecha) -> int:
    """
    Convierte una etiqueta de fecha a número de mes (1-12).
    Acepta: 'ene-2022', 'enero-2022', datetime, date, '2022-01-01', etc.
    Devuelve 0 si no puede determinar el mes.
    """
    # Si es un objeto date / datetime de Python o pandas
    if hasattr(fecha, "month"):
        return int(fecha.month)

    s = str(fecha).strip().lower()

    # Formato 'ene-2022' o 'enero-2022'
    m = re.match(r"^([a-záéíóúñ]+)[-/\s](\d{4})$", s)
    if m:
        abrev = m.group(1)[:3]
        return _MESES_ABREV.get(abrev, 0)

    # Formato 'YYYY-MM-DD' o 'DD/MM/YYYY'
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/]\d{1,2}$", s)
    if m:
        return int(m.group(2))
    m = re.match(r"^(\d{1,2})[/](\d{1,2})[/](\d{4})$", s)
    if m:
        return int(m.group(2))

    return 0


class ModeloPromedio(ModeloBase):
    """
    Implementa el Modelo de Valor Absoluto de Energía según UPME Resolución 16/2024.

    Atributos adicionales expuestos después de ajustar():
        lben_mensual   : dict  {1: valor, 2: valor, ..., 12: valor}
                         Los 12 valores de LBEn, uno por mes del año.
        ic_mensual     : dict  {1: (inf, sup), ..., 12: (inf, sup)}
        datos_por_mes  : dict  {1: [v1, v2, v3], ..., 12: [...]}
                         Los datos históricos agrupados por mes (antes de depurar).
        datos_depurados: dict  {1: [v1, v2], ..., 12: [...]}
                         Los datos que quedaron DENTRO del IC (usados para la LBEn).
        outliers       : dict  {1: [v_eliminado], ..., 12: [...]}
                         Valores eliminados por estar fuera del ±10% / ±2σ.
        advertencias   : list  Mensajes informativos (meses con pocos datos, etc.)
    """

    def ajustar(self):
        df, y, fechas = self._extraer_vectores()
        n = len(y)

        # ── PASO 1: Agrupar consumos por mes del año ──────────────────────────
        # Crea un diccionario: {1: [v_ene_año1, v_ene_año2, ...], 2: [...], ...}
        datos_por_mes: dict = {m: [] for m in range(1, 13)}
        indices_por_mes: dict = {m: [] for m in range(1, 13)}   # índices en y/fechas
        años_por_mes: dict = {m: [] for m in range(1, 13)}      # año real de cada valor

        for i, (consumo, fecha) in enumerate(zip(y, fechas)):
            num_mes = _extraer_numero_mes(fecha)
            if num_mes == 0:
                continue
            # Extraer año real de la fecha
            año_val = None
            if hasattr(fecha, "year"):
                año_val = int(fecha.year)
            else:
                import re as _re
                s = str(fecha).strip()
                m_yr = _re.search(r"(\d{4})", s)
                if m_yr:
                    año_val = int(m_yr.group(1))
            datos_por_mes[num_mes].append(float(consumo))
            indices_por_mes[num_mes].append(i)
            años_por_mes[num_mes].append(año_val)

        # ── PASO 2: Para cada mes, calcular promedio → IC → depurar → LBEn ───
        lben_mensual   = {}   # {mes: promedio_depurado}
        ic_mensual     = {}   # {mes: (ic_inf, ic_sup)}
        datos_depurados = {}  # {mes: [valores_dentro_del_IC]}
        outliers        = {}  # {mes: [valores_eliminados]}
        advertencias    = []

        for mes in range(1, 13):
            valores = datos_por_mes[mes]

            if len(valores) == 0:
                # No hay datos para este mes
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: sin datos históricos."
                )
                lben_mensual[mes]    = None
                ic_mensual[mes]      = (None, None)
                datos_depurados[mes] = []
                outliers[mes]        = []
                continue

            if len(valores) < 3:
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: solo {len(valores)} dato(s). "
                    f"Se recomienda mínimo 3 para mayor confiabilidad."
                )

            # Paso 2a: promedio inicial (antes de depurar)
            promedio_inicial = float(np.mean(valores))

            # Paso 2b: definir intervalo de confianza
            # Resolución: si n < 10 → ±10% del promedio (ecuación 3)
            #             si n >= 10 → promedio ± 2*DesvEst (ecuación 4)
            if len(valores) < 10:
                # Ecuación 3: IC = [promedio*0.9 , promedio*1.1]
                ic_inf = promedio_inicial * 0.9
                ic_sup = promedio_inicial * 1.1
            else:
                # Ecuación 4 y 5: IC = promedio ± 2 * DesvEst (poblacional, N)
                desv_est = float(np.sqrt(
                    sum((x - promedio_inicial) ** 2 for x in valores) / len(valores)
                ))
                ic_inf = promedio_inicial - 2 * desv_est
                ic_sup = promedio_inicial + 2 * desv_est

            ic_mensual[mes] = (round(ic_inf, 4), round(ic_sup, 4))

            # Paso 2c: depurar — eliminar valores fuera del IC
            dentro  = [v for v in valores if ic_inf <= v <= ic_sup]
            fuera   = [v for v in valores if v < ic_inf or v > ic_sup]

            datos_depurados[mes] = dentro
            outliers[mes]        = fuera

            if fuera:
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: {len(fuera)} valor(es) eliminado(s) "
                    f"por estar fuera del intervalo de confianza "
                    f"[{ic_inf:,.1f} – {ic_sup:,.1f}]: "
                    f"{[round(v, 1) for v in fuera]}"
                )

            # Paso 2d: LBEn = promedio de los valores que quedaron dentro
            if len(dentro) == 0:
                # Caso extremo: todos los valores son outliers → usar promedio inicial
                advertencias.append(
                    f"{_NOMBRES_MES[mes]}: todos los valores quedaron fuera del IC. "
                    f"Se usa el promedio inicial como referencia."
                )
                lben_mensual[mes] = round(promedio_inicial, 4)
            else:
                lben_mensual[mes] = round(float(np.mean(dentro)), 4)

        # ── PASO 3: Construir los vectores de salida (un valor por período) ───
        # Para cada período histórico asignamos la LBEn del mes que le corresponde.
        linea_base = []
        ic_sup_vec = []
        ic_inf_vec = []

        for i, fecha in enumerate(fechas):
            num_mes = _extraer_numero_mes(fecha)

            lb_mes  = lben_mensual.get(num_mes)
            ic_m    = ic_mensual.get(num_mes, (None, None))

            if lb_mes is None:
                # Si no hay LBEn para ese mes, usar promedio global como fallback
                lb_mes = float(np.mean([v for v in lben_mensual.values() if v is not None] or [0]))

            ic_inf_m = ic_m[0] if ic_m[0] is not None else lb_mes * 0.9
            ic_sup_m = ic_m[1] if ic_m[1] is not None else lb_mes * 1.1

            linea_base.append(lb_mes)
            ic_inf_vec.append(ic_inf_m)
            ic_sup_vec.append(ic_sup_m)

        # ── PASO 4: Guardar todo ──────────────────────────────────────────────
        self.consumo_real  = y
        self.linea_base    = linea_base
        self.ic_superior   = ic_sup_vec
        self.ic_inferior   = ic_inf_vec
        self.fechas        = fechas

        # Atributos adicionales específicos de este modelo
        self.lben_mensual    = lben_mensual
        self.ic_mensual      = ic_mensual
        self.datos_por_mes   = datos_por_mes
        self.datos_depurados = datos_depurados
        self.outliers        = outliers
        self.advertencias    = advertencias

        # Parámetros exportados al calculador
        self.params = {
            # Los 12 valores de LBEn — usados en _predecir_reporte()
            "lben_mensual":    lben_mensual,
            "ic_mensual":      ic_mensual,
            "datos_por_mes":   datos_por_mes,
            "datos_depurados": datos_depurados,
            "outliers":        outliers,
            "advertencias":    advertencias,
            "n_total":         n,
            "años_por_mes":    años_por_mes,
            # Promedio general para mostrar en la ecuación del gráfico
            "media": round(
                float(np.mean([v for v in lben_mensual.values() if v is not None])),
                4
            ),
            "sem": round(
                float(np.std(
                    [v for v in lben_mensual.values() if v is not None], ddof=1
                )) if sum(1 for v in lben_mensual.values() if v is not None) > 1 else 0,
                4
            ),
        }

        # Para el gráfico de dispersión
        self.coeficientes = {
            f"LBEn {_NOMBRES_MES[m]}": round(v, 2)
            for m, v in lben_mensual.items() if v is not None
        }
