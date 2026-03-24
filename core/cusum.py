"""
core/cusum.py
=============
CUSUM — VERSIÓN BASE (pendiente de fórmulas definitivas)

TODO: Reemplazar los cálculos marcados con # ← FÓRMULA con la lógica real.
"""

from typing import List


def calcular_cusum(desviaciones_absolutas: List[float]) -> List[float]:
    """
    Recibe: lista de desviaciones por período = consumo_real - linea_base
    Devuelve: lista con el valor acumulado hasta cada período

    Ejemplo:
      desviaciones = [-1000, -800,  +300, -1200]
      cusum        = [-1000, -1800, -1500, -2700]

    Interpretación:
      Valor negativo y bajando  → ahorro sostenido
      Valor positivo y subiendo → incremento sostenido
      Cambio brusco de dirección → posible evento o cambio de proceso

    ══════════════════════════════════════════════════════════════════════════
    AQUÍ VA TU FÓRMULA DE CUSUM
    Datos disponibles:
      desviaciones_absolutas → lista de floats (un valor por período)

    Debes producir:
      lista de n floats (el acumulado hasta cada período)

    PLACEHOLDER actual (acumulación simple):
    ══════════════════════════════════════════════════════════════════════════
    """
    cusum      = []
    acumulado  = 0.0
    for d in desviaciones_absolutas:
        acumulado += d          # ← FÓRMULA: reemplaza con tu lógica de acumulación
        cusum.append(round(acumulado, 4))
    return cusum

