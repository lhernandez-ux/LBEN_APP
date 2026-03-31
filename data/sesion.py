"""
data/sesion.py — Estado compartido entre todas las páginas.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class Sesion:
    nombre_proyecto: str = ""
    unidad_energia:  str = "kWh"

    modelo_id:            str  = ""
    col_consumo:          str  = "Consumo_kWh"
    vars_independientes:  list = field(default_factory=list)
    nivel_confianza:      int  = 95
    
    # Frecuencia de los datos (solo para regresión lineal)
    frecuencia_datos:     str  = "mensual"  # "mensual", "diario", "horario"

    # Período histórico (entrena el modelo)
    periodo_historico: str = ""

    # Período de reporte (se compara contra la línea base)
    periodo_reporte: str = ""
    tiene_reporte:   bool = False   # False = solo histórico, sin reporte

    # DataFrames separados
    df_historico: Optional[pd.DataFrame] = None
    df_reporte:   Optional[pd.DataFrame] = None

    # Ruta del Excel base (para guardar/abrir proyectos)
    ruta_excel: str = ""

    # Resultado calculado
    resultado: Optional[dict] = None