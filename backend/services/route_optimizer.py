# -*- coding: utf-8 -*-
"""
route_optimizer.py  –  PERSONA 1
Capa de servicio que expone la optimización de rutas al resto del backend.

Actúa como fachada sobre path_algorithms: valida entradas, selecciona el
algoritmo correcto y devuelve un RouteResult uniforme.

Modos soportados actualmente:
    "distancia"  →  dijkstra_por_distancia   (responsabilidad DANIEL)
"""

from ..models import Graph, RouteResult
from .path_algorithms import dijkstra_por_distancia


# Registro de algoritmos disponibles por modo
_ALGORITMOS = {
    "distancia": dijkstra_por_distancia,
}


def optimizar_ruta(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
    modo: str = "distancia",
) -> RouteResult:
    """
    Calcula la ruta óptima entre dos nodos según el modo indicado.

    Parámetros
    ----------
    graph      : Graph  – grafo validado (devuelto por GraphLoader).
    inicio_id  : str    – ID del nodo origen.
    destino_id : str    – ID del nodo destino.
    modo       : str    – criterio de optimización.
                         Valores aceptados: "distancia"
                         (extensible: "costo", "tiempo", …).

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
    return algoritmo(graph, inicio_id, destino_id)


def modos_disponibles() -> list:
    """Retorna la lista de modos de optimización registrados."""
    return sorted(_ALGORITMOS.keys())