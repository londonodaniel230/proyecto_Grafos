# -*- coding: utf-8 -*-
"""
path_algorithms.py  –  PERSONA 1 / DANIEL
Algoritmos de búsqueda de rutas sobre el grafo de viajes.

Algoritmo implementado:
    - dijkstra_por_distancia : ruta óptima usando distancia_km como peso.
"""

import math
from typing import Dict, List, Optional, Tuple

from ..models import Graph, RouteResult, RouteStep


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _build_adjacency(graph: Graph) -> Dict[str, List[Tuple[str, float, str]]]:
    """
    Construye un mapa de adyacencia a partir del modelo Graph.

    Retorna:
        {
            origen_id: [(destino_id, distancia_km, aeronave_principal), ...]
        }
    """
    adj: Dict[str, List[Tuple[str, float, str]]] = {
        nodo.id: [] for nodo in graph.nodos
    }

    for arista in graph.aristas:
        peso = arista.distancia_km
        aeronave = arista.aeronaves[0] if arista.aeronaves else "desconocida"
        if arista.origen in adj:
            adj[arista.origen].append((arista.destino, peso, aeronave))

    return adj


def _reconstruir_camino(
    pred: Dict[str, Optional[str]],
    inicio_id: str,
    destino_id: str,
) -> List[str]:
    """Reconstruye la lista de IDs desde inicio hasta destino usando pred."""
    camino: List[str] = []
    actual: Optional[str] = destino_id
    while actual is not None:
        camino.insert(0, actual)
        actual = pred.get(actual)
    # Verificar que el camino realmente arranca en inicio
    if not camino or camino[0] != inicio_id:
        return []
    return camino


# ---------------------------------------------------------------------------
# Dijkstra por distancia  (responsabilidad de DANIEL)
# ---------------------------------------------------------------------------

def dijkstra_por_distancia(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
) -> "RouteResult":
    """
    Calcula la ruta de menor distancia (en km) entre dos nodos usando
    el algoritmo de Dijkstra.

    Parámetros
    ----------
    graph       : Graph  – grafo cargado con nodos y aristas.
    inicio_id   : str    – identificador del nodo origen.
    destino_id  : str    – identificador del nodo destino.

    Retorna
    -------
    RouteResult con:
        - camino   : lista de IDs en orden de visita.
        - pasos    : lista de RouteStep con detalle de cada tramo.
        - total_km : distancia acumulada total.
        - encontrado : True si existe ruta, False si no.

    Complejidad: O(V²) con búsqueda lineal del mínimo (suficiente para
    grafos de tamaño moderado; se puede mejorar con heapq si es necesario).
    """
    # ------------------------------------------------------------------ setup
    todos_ids = [nodo.id for nodo in graph.nodos]

    if inicio_id not in todos_ids:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=f"Nodo origen '{inicio_id}' no existe en el grafo.",
        )
    if destino_id not in todos_ids:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=f"Nodo destino '{destino_id}' no existe en el grafo.",
        )

    adj = _build_adjacency(graph)

    # Tablas de Dijkstra
    dist: Dict[str, float] = {v: math.inf for v in todos_ids}
    pred: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    pred_aeronave: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    dist[inicio_id] = 0.0

    no_visitados: set = set(todos_ids)

    # --------------------------------------------------------------- iteración
    while no_visitados:
        # Seleccionar el nodo no visitado con menor distancia conocida
        u = min(no_visitados, key=lambda v: dist[v])

        if dist[u] == math.inf:
            # Nodos restantes son inalcanzables
            break

        no_visitados.remove(u)

        if u == destino_id:
            # Destino alcanzado; no es necesario continuar
            break

        # Relajación de aristas salientes
        for (vecino, peso_km, aeronave) in adj.get(u, []):
            if vecino not in no_visitados:
                continue
            nueva_dist = dist[u] + peso_km
            if nueva_dist < dist[vecino]:
                dist[vecino] = nueva_dist
                pred[vecino] = u
                pred_aeronave[vecino] = aeronave

    # ------------------------------------------- reconstrucción del resultado
    if dist[destino_id] == math.inf:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=f"No existe ruta entre '{inicio_id}' y '{destino_id}'.",
        )

    camino = _reconstruir_camino(pred, inicio_id, destino_id)

    # Construir pasos detallados tramo a tramo
    pasos: List[RouteStep] = []
    distancia_acum = 0.0
    for i in range(len(camino) - 1):
        origen = camino[i]
        destino = camino[i + 1]
        # Buscar el peso real de esta arista
        tramo_km = next(
            (w for (d, w, _) in adj.get(origen, []) if d == destino),
            0.0,
        )
        aeronave = pred_aeronave.get(destino)
        distancia_acum += tramo_km
        pasos.append(
            RouteStep(
                origen=origen,
                destino=destino,
                distancia_km=tramo_km,
                distancia_acumulada_km=distancia_acum,
                aeronave=aeronave,
            )
        )

    return RouteResult(
        camino=camino,
        pasos=pasos,
        total_km=dist[destino_id],
        encontrado=True,
        error=None,
    )