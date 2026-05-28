# -*- coding: utf-8 -*-
"""
route_optimizer.py  –  PERSONA 1
Capa de servicio que expone la optimización de rutas al resto del backend.

Actúa como fachada sobre path_algorithms: valida entradas, selecciona el
algoritmo correcto y devuelve un RouteResult uniforme.

Modos soportados actualmente:
    "distancia"  →  dijkstra_por_distancia   (responsabilidad DANIEL)
    "costo"      →  dijkstra_por_costo       (responsabilidad TAiKK)
"""

from typing import Optional

from ..models import Graph, RouteResult
from .path_algorithms import CostOptions, dijkstra_por_costo, dijkstra_por_distancia, dijkstra_por_tiempo


# Registro de algoritmos disponibles por modo
_ALGORITMOS = {
    "distancia": dijkstra_por_distancia,
    "costo": dijkstra_por_costo,
    "tiempo": dijkstra_por_tiempo,
}


def optimizar_ruta(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
    modo: str = "distancia",
    presupuesto_total: Optional[float] = None,
    opciones: Optional[CostOptions] = None,
    inicio_ids: Optional[list] = None,
    destino_ids: Optional[list] = None,
) -> RouteResult:
    """
    Calcula la ruta óptima entre dos nodos según el modo indicado.

    Parámetros
    ----------
    graph      : Graph  – grafo validado (devuelto por GraphLoader).
    inicio_id  : str    – ID del nodo origen.
    destino_id : str    – ID del nodo destino.
    modo       : str    – criterio de optimización.
                         Valores aceptados: "distancia", "costo", "tiempo"
                         (extensible: …).
    presupuesto_total : float | None – presupuesto maximo (USD) para el modo
                         "costo". Si es None, no se valida presupuesto.
    opciones  : CostOptions | None – opciones de costo (aeronaves, alimentacion,
                alojamiento, trabajo).
    inicio_ids : list | None – lista de IDs de origen (opcional).
    destino_ids: list | None – lista de IDs de destino (opcional).

    Retorna
    -------
    RouteResult – siempre se devuelve un objeto; si hay error, el campo
    ``encontrado`` será False y ``error`` contendrá la descripción.
    """
    modo_normalizado = modo.strip().lower()

    if modo_normalizado not in _ALGORITMOS:
        modos_disponibles = ", ".join(sorted(_ALGORITMOS.keys()))
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=float("inf"),
            encontrado=False,
            error=(
                f"Modo '{modo}' no reconocido. "
                f"Modos disponibles: {modos_disponibles}."
            ),
        )

    algoritmo = _ALGORITMOS[modo_normalizado]
    if modo_normalizado == "costo":
        return algoritmo(
            graph,
            inicio_id,
            destino_id,
            presupuesto_total=presupuesto_total,
            opciones=opciones,
            inicio_ids=inicio_ids,
            destino_ids=destino_ids,
        )
    elif modo_normalizado == "tiempo":
        return algoritmo(
            graph,
            inicio_id,
            destino_id,
            opciones=opciones,
            inicio_ids=inicio_ids,
            destino_ids=destino_ids,
        )
    return algoritmo(graph, inicio_id, destino_id)


def modos_disponibles() -> list:
    """Retorna la lista de modos de optimización registrados."""
    return sorted(_ALGORITMOS.keys())