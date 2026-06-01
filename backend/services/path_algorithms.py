# -*- coding: utf-8 -*-
"""
path_algorithms.py  –  PERSONA 1 / DANIEL
Algoritmos de búsqueda de rutas sobre el grafo de viajes.

Algoritmos implementados:
    - dijkstra_por_distancia : ruta óptima usando distancia_km como peso.
    - dijkstra_por_costo     : ruta optima usando costo como peso.
    - dijkstra_por_tiempo    : ruta optima usando tiempo como peso.
    - dfs_mayor_destinos     : ruta con mas destinos con restricciones.
"""

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

from ..models import Graph, RouteResult, RouteStep


@dataclass(frozen=True)
class CostOptions:
    aeronaves_permitidas: Optional[Set[str]] = None
    incluir_alojamiento: bool = True
    incluir_alimentacion: bool = True
    incluir_trabajo: bool = True


@dataclass(frozen=True)
class TraversalConstraints:
    presupuesto_total: Optional[float] = None
    tiempo_maximo: Optional[float] = None
    excluir_secundarios: bool = False


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


def _reconstruir_camino_multi(
    pred: Dict[str, Optional[str]],
    inicio_ids: Set[str],
    destino_id: str,
) -> List[str]:
    camino: List[str] = []
    actual: Optional[str] = destino_id
    while actual is not None:
        camino.insert(0, actual)
        actual = pred.get(actual)
    if not camino or camino[0] not in inicio_ids:
        return []
    return camino


def _calcular_costo_estancia(
    destino: Optional["object"],
    estancia_minima: float,
    config: Optional["object"],
    incluir_alojamiento: bool = True,
    incluir_alimentacion: bool = True,
) -> float:
    if destino is None or config is None or estancia_minima <= 0:
        return 0.0

    if not incluir_alojamiento and not incluir_alimentacion:
        return 0.0

    costo = 0.0
    intervalo_aloj = getattr(config, "intervalo_alojamiento", 0.0) or 0.0
    intervalo_alim = getattr(config, "intervalo_alimentacion", 0.0) or 0.0

    if incluir_alojamiento and intervalo_aloj > 0:
        unidades = math.ceil(estancia_minima / intervalo_aloj)
        costo += unidades * float(getattr(destino, "costo_alojamiento", 0.0) or 0.0)
    if incluir_alimentacion and intervalo_alim > 0:
        unidades = math.ceil(estancia_minima / intervalo_alim)
        costo += unidades * float(getattr(destino, "costo_alimentacion", 0.0) or 0.0)

    return costo


def _normalizar_aeronaves(values: Iterable[str]) -> Set[str]:
    return {value.strip().lower() for value in values if value and value.strip()}


def _filtrar_aeronaves(
    aeronaves: List[str],
    permitidas: Optional[Set[str]],
) -> List[str]:
    if not permitidas:
        return aeronaves

    resultado: List[str] = []
    for aeronave in aeronaves:
        if aeronave.strip().lower() in permitidas:
            resultado.append(aeronave)

    return resultado


def _seleccionar_aeronave_mas_barata(
    aeronaves: List[str],
    config: Optional["object"],
    aeronaves_permitidas: Optional[Set[str]] = None,
) -> Tuple[str, Optional[float]]:
    if not aeronaves:
        return ("desconocida", None)

    candidatas = _filtrar_aeronaves(aeronaves, aeronaves_permitidas)
    if not candidatas:
        return ("", None)

    if config is None or not getattr(config, "aeronaves", None):
        return (candidatas[0], None)

    costos: List[Tuple[str, float]] = []
    aeronaves_cfg = getattr(config, "aeronaves", {})
    aeronaves_cfg_ci = {key.lower(): value for key, value in aeronaves_cfg.items()}
    for aeronave in candidatas:
        config_entry = aeronaves_cfg.get(aeronave)
        if config_entry is None:
            config_entry = aeronaves_cfg_ci.get(aeronave.lower())
        if config_entry is None:
            continue
        costos.append((aeronave, float(config_entry.costo_km)))

    if not costos:
        return (candidatas[0], None)

    return min(costos, key=lambda item: item[1])


def _credito_trabajo(destino: Optional["object"], incluir_trabajo: bool) -> float:
    if destino is None or not incluir_trabajo:
        return 0.0

    trabajos = getattr(destino, "trabajos", None) or []
    if not trabajos:
        return 0.0

    ingresos = []
    for trabajo in trabajos:
        tarifa = float(getattr(trabajo, "tarifa_hora", 0.0) or 0.0)
        max_horas = float(getattr(trabajo, "max_horas", 0.0) or 0.0)
        ingresos.append(tarifa * max_horas)

    return max(ingresos) if ingresos else 0.0


def _build_adjacency_por_costo(
    graph: Graph,
    opciones: Optional[CostOptions] = None,
) -> Dict[str, List[Tuple[str, float, float, str]]]:
    """
    Construye un mapa de adyacencia con pesos por costo.

    Retorna:
        {
            origen_id: [(destino_id, costo_total, distancia_km, aeronave), ...]
        }
    """
    adj: Dict[str, List[Tuple[str, float, float, str]]] = {
        nodo.id: [] for nodo in graph.nodos
    }

    nodo_por_id = {nodo.id: nodo for nodo in graph.nodos}
    config = graph.configuracion
    opciones = opciones or CostOptions()
    permitidas = opciones.aeronaves_permitidas

    for arista in graph.aristas:
        aeronave, costo_km = _seleccionar_aeronave_mas_barata(
            arista.aeronaves, config, permitidas
        )
        if not aeronave:
            continue
        costo_distancia = arista.distancia_km * (costo_km or 0.0)
        destino = nodo_por_id.get(arista.destino)
        costo_estancia = _calcular_costo_estancia(
            destino,
            arista.estancia_minima,
            config,
            incluir_alojamiento=opciones.incluir_alojamiento,
            incluir_alimentacion=opciones.incluir_alimentacion,
        )
        credito_trabajo = _credito_trabajo(destino, opciones.incluir_trabajo)
        costo_total = float(arista.costo_base) + costo_distancia + costo_estancia
        costo_total = max(costo_total - credito_trabajo, 0.0)

        if arista.origen in adj:
            adj[arista.origen].append(
                (arista.destino, costo_total, arista.distancia_km, aeronave)
            )

    return adj


def _presupuesto_disponible(
    presupuesto_total: Optional[float],
    config: Optional["object"],
) -> Optional[float]:
    if presupuesto_total is None:
        return None
    if presupuesto_total <= 0:
        return 0.0

    porcentaje = 0.0
    if config is not None:
        porcentaje = float(getattr(config, "presupuesto_minimo_porc", 0.0) or 0.0)
    reserva = presupuesto_total * (porcentaje / 100.0)
    return max(presupuesto_total - reserva, 0.0)


def _nodos_permitidos(
    graph: Graph,
    excluir_secundarios: bool,
    inicio_set: Set[str],
    destino_set: Set[str],
) -> Set[str]:
    if not excluir_secundarios:
        return {nodo.id for nodo in graph.nodos}

    permitidos = {nodo.id for nodo in graph.nodos if nodo.es_hub}
    permitidos.update(inicio_set)
    permitidos.update(destino_set)
    return permitidos


def _build_adjacency_con_pesos(
    graph: Graph,
    opciones: Optional[CostOptions],
    nodos_permitidos: Set[str],
) -> Dict[str, List[Tuple[str, float, float, float, str]]]:
    """
    Construye un mapa de adyacencia con costo y tiempo por aeronave.

    Retorna:
        {
            origen_id: [(destino_id, costo_total, tiempo_total, distancia_km, aeronave), ...]
        }
    """
    adj: Dict[str, List[Tuple[str, float, float, float, str]]] = {
        nodo_id: [] for nodo_id in nodos_permitidos
    }

    opciones = opciones or CostOptions()
    config = graph.configuracion
    nodo_por_id = {nodo.id: nodo for nodo in graph.nodos}
    permitidas = opciones.aeronaves_permitidas

    aeronaves_cfg = getattr(config, "aeronaves", {}) if config else {}
    aeronaves_cfg_ci = {key.lower(): value for key, value in aeronaves_cfg.items()}

    for arista in graph.aristas:
        if arista.origen not in nodos_permitidos or arista.destino not in nodos_permitidos:
            continue

        destino = nodo_por_id.get(arista.destino)
        aeronaves = arista.aeronaves or ["desconocida"]

        for aeronave in aeronaves:
            if permitidas and aeronave.strip().lower() not in permitidas:
                continue

            config_entry = aeronaves_cfg.get(aeronave)
            if config_entry is None:
                config_entry = aeronaves_cfg_ci.get(aeronave.lower())

            costo_km = float(getattr(config_entry, "costo_km", 0.0) or 0.0)
            tiempo_km = float(getattr(config_entry, "tiempo_km", 0.0) or 0.0)

            costo_distancia = arista.distancia_km * costo_km
            costo_estancia = _calcular_costo_estancia(
                destino,
                arista.estancia_minima,
                config,
                incluir_alojamiento=opciones.incluir_alojamiento,
                incluir_alimentacion=opciones.incluir_alimentacion,
            )
            credito_trabajo = _credito_trabajo(destino, opciones.incluir_trabajo)
            costo_total = float(arista.costo_base) + costo_distancia + costo_estancia
            costo_total = max(costo_total - credito_trabajo, 0.0)

            tiempo_total = arista.distancia_km * tiempo_km + arista.estancia_minima

            adj[arista.origen].append(
                (
                    arista.destino,
                    costo_total,
                    tiempo_total,
                    arista.distancia_km,
                    aeronave,
                )
            )

    return adj


def _cumple_restricciones(
    costo_total: float,
    tiempo_total: float,
    presupuesto_max: Optional[float],
    tiempo_maximo: Optional[float],
) -> bool:
    if presupuesto_max is not None and costo_total > presupuesto_max:
        return False
    if tiempo_maximo is not None and tiempo_total > tiempo_maximo:
        return False
    return True


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


# ---------------------------------------------------------------------------
# Dijkstra por costo  (responsabilidad TAiKK)
# ---------------------------------------------------------------------------

def dijkstra_por_costo(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
    presupuesto_total: Optional[float] = None,
    opciones: Optional[CostOptions] = None,
    inicio_ids: Optional[List[str]] = None,
    destino_ids: Optional[List[str]] = None,
) -> "RouteResult":
    """
    Calcula la ruta de menor costo (USD) entre dos nodos usando Dijkstra.

    El costo considera:
        - costo_base de la arista.
        - distancia_km * costo_km segun la aeronave mas barata disponible.
        - costo de estancia minima (alojamiento + alimentacion) en destino.

    Si se provee presupuesto_total, se valida que el costo total no supere
    el presupuesto disponible (respetando presupuesto_minimo_porc).
    """
    # ------------------------------------------------------------------ setup
    todos_ids = [nodo.id for nodo in graph.nodos]
    inicio_ids = [item for item in (inicio_ids or []) if item]
    destino_ids = [item for item in (destino_ids or []) if item]

    if not inicio_ids:
        inicio_ids = [inicio_id]
    if not destino_ids:
        destino_ids = [destino_id]

    inicio_set = set(inicio_ids)
    destino_set = set(destino_ids)

    faltantes_inicio = [item for item in inicio_set if item not in todos_ids]
    if faltantes_inicio:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos origen no existen en el grafo: "
                + ", ".join(sorted(faltantes_inicio))
            ),
        )
    faltantes_destino = [item for item in destino_set if item not in todos_ids]
    if faltantes_destino:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos destino no existen en el grafo: "
                + ", ".join(sorted(faltantes_destino))
            ),
        )

    adj = _build_adjacency_por_costo(graph, opciones)

    # Tablas de Dijkstra (costos)
    dist: Dict[str, float] = {v: math.inf for v in todos_ids}
    pred: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    pred_aeronave: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    for inicio in inicio_set:
        dist[inicio] = 0.0

    no_visitados: set = set(todos_ids)

    # --------------------------------------------------------------- iteracion
    destino_encontrado: Optional[str] = None
    while no_visitados:
        u = min(no_visitados, key=lambda v: dist[v])

        if dist[u] == math.inf:
            break

        no_visitados.remove(u)

        if u in destino_set:
            destino_encontrado = u
            break

        for (vecino, costo_tramo, _, aeronave) in adj.get(u, []):
            if vecino not in no_visitados:
                continue
            nueva_dist = dist[u] + costo_tramo
            if nueva_dist < dist[vecino]:
                dist[vecino] = nueva_dist
                pred[vecino] = u
                pred_aeronave[vecino] = aeronave

    if destino_encontrado is None or dist[destino_encontrado] == math.inf:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error="No existe ruta entre los nodos seleccionados.",
        )

    camino = _reconstruir_camino_multi(pred, inicio_set, destino_encontrado)

    pasos: List[RouteStep] = []
    distancia_acum = 0.0
    costo_acum = 0.0
    for i in range(len(camino) - 1):
        origen = camino[i]
        destino = camino[i + 1]

        tramo = next(
            (item for item in adj.get(origen, []) if item[0] == destino),
            None,
        )
        if tramo is None:
            costo_tramo = 0.0
            tramo_km = 0.0
            aeronave = pred_aeronave.get(destino)
        else:
            _, costo_tramo, tramo_km, aeronave = tramo

        distancia_acum += tramo_km
        costo_acum += costo_tramo
        pasos.append(
            RouteStep(
                origen=origen,
                destino=destino,
                distancia_km=tramo_km,
                distancia_acumulada_km=distancia_acum,
                aeronave=aeronave,
            )
        )

    limite = _presupuesto_disponible(presupuesto_total, graph.configuracion)
    if limite is not None and costo_acum > limite:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error="Presupuesto insuficiente para la ruta.",
        )

    return RouteResult(
        camino=camino,
        pasos=pasos,
        total_km=distancia_acum,
        encontrado=True,
        error=None,
        total_costo=costo_acum,
    )


# ---------------------------------------------------------------------------
# Dijkstra por tiempo (responsabilidad PERSONA 1)
# ---------------------------------------------------------------------------

def _seleccionar_aeronave_mas_rapida(
    aeronaves: List[str],
    config: Optional["object"],
    aeronaves_permitidas: Optional[Set[str]] = None,
) -> Tuple[str, Optional[float]]:
    """
    Selecciona la aeronave más rápida (menor tiempo_km) de la lista.
    Si hay múltiples opciones, elige la más rápida según la configuración.
    """
    if not aeronaves:
        return ("desconocida", None)

    candidatas = _filtrar_aeronaves(aeronaves, aeronaves_permitidas)
    if not candidatas:
        return ("", None)

    if config is None or not getattr(config, "aeronaves", None):
        return (candidatas[0], None)

    tiempos: List[Tuple[str, float]] = []
    aeronaves_cfg = getattr(config, "aeronaves", {})
    aeronaves_cfg_ci = {key.lower(): value for key, value in aeronaves_cfg.items()}
    for aeronave in candidatas:
        config_entry = aeronaves_cfg.get(aeronave)
        if config_entry is None:
            config_entry = aeronaves_cfg_ci.get(aeronave.lower())
        if config_entry is None:
            continue
        tiempos.append((aeronave, float(config_entry.tiempo_km)))

    if not tiempos:
        return (candidatas[0], None)

    return min(tiempos, key=lambda item: item[1])


def _build_adjacency_por_tiempo(
    graph: Graph,
    opciones: Optional[CostOptions] = None,
) -> Dict[str, List[Tuple[str, float, float, str]]]:
    """
    Construye un mapa de adyacencia con pesos por tiempo.

    Retorna:
        {
            origen_id: [(destino_id, tiempo_total, distancia_km, aeronave), ...]
        }
    """
    adj: Dict[str, List[Tuple[str, float, float, str]]] = {
        nodo.id: [] for nodo in graph.nodos
    }

    config = graph.configuracion
    opciones = opciones or CostOptions()
    permitidas = opciones.aeronaves_permitidas

    for arista in graph.aristas:
        aeronave, tiempo_km = _seleccionar_aeronave_mas_rapida(
            arista.aeronaves, config, permitidas
        )
        if not aeronave:
            continue
        # Tiempo total = tiempo de vuelo + estancia mínima
        tiempo_vuelo = arista.distancia_km * (tiempo_km or 0.0)
        tiempo_total = tiempo_vuelo + arista.estancia_minima

        if arista.origen in adj:
            adj[arista.origen].append(
                (arista.destino, tiempo_total, arista.distancia_km, aeronave)
            )

    return adj


def dijkstra_por_tiempo(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
    opciones: Optional[CostOptions] = None,
    inicio_ids: Optional[List[str]] = None,
    destino_ids: Optional[List[str]] = None,
) -> "RouteResult":
    """
    Calcula la ruta de menor tiempo (horas) entre dos nodos usando Dijkstra.

    El tiempo considera:
        - distancia_km * tiempo_km segun la aeronave mas rapida disponible.
        - estancia_minima del tramo.

    Parámetros
    ----------
    graph       : Graph  – grafo cargado con nodos y aristas.
    inicio_id   : str    – identificador del nodo origen.
    destino_id  : str    – identificador del nodo destino.
    opciones    : CostOptions | None – opciones de filtrado (aeronaves).
    inicio_ids  : list | None – lista de IDs de origen (opcional).
    destino_ids : list | None – lista de IDs de destino (opcional).

    Retorna
    -------
    RouteResult con:
        - camino   : lista de IDs en orden de visita.
        - pasos    : lista de RouteStep con detalle de cada tramo.
        - total_km : distancia acumulada total.
        - encontrado : True si existe ruta, False si no.
    """
    # ------------------------------------------------------------------ setup
    todos_ids = [nodo.id for nodo in graph.nodos]
    inicio_ids = [item for item in (inicio_ids or []) if item]
    destino_ids = [item for item in (destino_ids or []) if item]

    if not inicio_ids:
        inicio_ids = [inicio_id]
    if not destino_ids:
        destino_ids = [destino_id]

    inicio_set = set(inicio_ids)
    destino_set = set(destino_ids)

    faltantes_inicio = [item for item in inicio_set if item not in todos_ids]
    if faltantes_inicio:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos origen no existen en el grafo: "
                + ", ".join(sorted(faltantes_inicio))
            ),
        )
    faltantes_destino = [item for item in destino_set if item not in todos_ids]
    if faltantes_destino:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos destino no existen en el grafo: "
                + ", ".join(sorted(faltantes_destino))
            ),
        )

    adj = _build_adjacency_por_tiempo(graph, opciones)

    # Tablas de Dijkstra (tiempos)
    dist: Dict[str, float] = {v: math.inf for v in todos_ids}
    pred: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    pred_aeronave: Dict[str, Optional[str]] = {v: None for v in todos_ids}
    for inicio in inicio_set:
        dist[inicio] = 0.0

    no_visitados: set = set(todos_ids)

    # --------------------------------------------------------------- iteracion
    destino_encontrado: Optional[str] = None
    while no_visitados:
        u = min(no_visitados, key=lambda v: dist[v])

        if dist[u] == math.inf:
            break

        no_visitados.remove(u)

        if u in destino_set:
            destino_encontrado = u
            break

        for (vecino, tiempo_tramo, _, aeronave) in adj.get(u, []):
            if vecino not in no_visitados:
                continue
            nueva_dist = dist[u] + tiempo_tramo
            if nueva_dist < dist[vecino]:
                dist[vecino] = nueva_dist
                pred[vecino] = u
                pred_aeronave[vecino] = aeronave

    if destino_encontrado is None or dist[destino_encontrado] == math.inf:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error="No existe ruta entre los nodos seleccionados.",
        )

    camino = _reconstruir_camino_multi(pred, inicio_set, destino_encontrado)

    pasos: List[RouteStep] = []
    distancia_acum = 0.0
    for i in range(len(camino) - 1):
        origen = camino[i]
        destino = camino[i + 1]

        tramo = next(
            (item for item in adj.get(origen, []) if item[0] == destino),
            None,
        )
        if tramo is None:
            tramo_km = 0.0
            aeronave = pred_aeronave.get(destino)
        else:
            _, _, tramo_km, aeronave = tramo

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
        total_km=distancia_acum,
        encontrado=True,
        error=None,
        total_costo=dist[destino_encontrado],  # Reutilizamos para guardar el tiempo total
    )


# ---------------------------------------------------------------------------
# DFS mayor cantidad de destinos (con restricciones)
# ---------------------------------------------------------------------------

def dfs_mayor_destinos(
    graph: Graph,
    inicio_id: str,
    destino_id: str,
    opciones: Optional[CostOptions] = None,
    restricciones: Optional[TraversalConstraints] = None,
    inicio_ids: Optional[List[str]] = None,
    destino_ids: Optional[List[str]] = None,
) -> "RouteResult":
    """
    Encuentra una ruta con la mayor cantidad de destinos respetando restricciones.

    Reglas:
        - Si existe ruta directa valida, se retorna esa ruta.
        - Si no, se exploran rutas con DFS sin repetir nodos.

    Restricciones soportadas:
        - presupuesto_total
        - tiempo_maximo
        - excluir_secundarios
        - aeronaves_permitidas (desde opciones)
    """
    restricciones = restricciones or TraversalConstraints()
    opciones = opciones or CostOptions()

    todos_ids = [nodo.id for nodo in graph.nodos]
    inicio_ids = [item for item in (inicio_ids or []) if item]
    destino_ids = [item for item in (destino_ids or []) if item]

    if not inicio_ids:
        inicio_ids = [inicio_id]
    if not destino_ids:
        destino_ids = [destino_id]

    inicio_set = set(inicio_ids)
    destino_set = set(destino_ids)

    faltantes_inicio = [item for item in inicio_set if item not in todos_ids]
    if faltantes_inicio:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos origen no existen en el grafo: "
                + ", ".join(sorted(faltantes_inicio))
            ),
        )

    faltantes_destino = [item for item in destino_set if item not in todos_ids]
    if faltantes_destino:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error=(
                "Nodos destino no existen en el grafo: "
                + ", ".join(sorted(faltantes_destino))
            ),
        )

    nodos_permitidos = _nodos_permitidos(
        graph,
        restricciones.excluir_secundarios,
        inicio_set,
        destino_set,
    )

    adj = _build_adjacency_con_pesos(graph, opciones, nodos_permitidos)

    presupuesto_max = _presupuesto_disponible(
        restricciones.presupuesto_total,
        graph.configuracion,
    )
    tiempo_maximo = restricciones.tiempo_maximo

    mejor_camino: List[str] = []
    mejor_aristas: List[Tuple[str, float, float, float, str]] = []
    mejor_costo = math.inf
    mejor_tiempo = math.inf
    mejor_km = 0.0

    # Ruta directa si existe y cumple restricciones
    mejor_directa = None
    for inicio in inicio_set:
        for edge in adj.get(inicio, []):
            destino, costo, tiempo, distancia_km, aeronave = edge
            if destino not in destino_set:
                continue
            if not _cumple_restricciones(costo, tiempo, presupuesto_max, tiempo_maximo):
                continue
            if mejor_directa is None or costo < mejor_directa[1]:
                mejor_directa = (destino, costo, tiempo, distancia_km, aeronave, inicio)

    if mejor_directa is not None:
        destino, costo, _, distancia_km, aeronave, inicio = mejor_directa
        pasos = [
            RouteStep(
                origen=inicio,
                destino=destino,
                distancia_km=distancia_km,
                distancia_acumulada_km=distancia_km,
                aeronave=aeronave,
            )
        ]
        return RouteResult(
            camino=[inicio, destino],
            pasos=pasos,
            total_km=distancia_km,
            encontrado=True,
            error=None,
            total_costo=costo,
        )

    # DFS para maximizar destinos
    stack: List[Tuple[str, List[str], List[Tuple[str, float, float, float, str]], Set[str], float, float, float]] = []
    for inicio in inicio_set:
        if inicio in nodos_permitidos:
            stack.append((inicio, [inicio], [], {inicio}, 0.0, 0.0, 0.0))

    while stack:
        actual, camino, aristas_camino, visitados, costo_acum, tiempo_acum, km_acum = stack.pop()

        if actual in destino_set:
            es_mejor = False
            if len(camino) > len(mejor_camino):
                es_mejor = True
            elif len(camino) == len(mejor_camino):
                if costo_acum < mejor_costo:
                    es_mejor = True
                elif costo_acum == mejor_costo and tiempo_acum < mejor_tiempo:
                    es_mejor = True

            if es_mejor:
                mejor_camino = list(camino)
                mejor_aristas = list(aristas_camino)
                mejor_costo = costo_acum
                mejor_tiempo = tiempo_acum
                mejor_km = km_acum

        for edge in adj.get(actual, []):
            vecino, costo, tiempo, distancia_km, _ = edge
            if vecino in visitados:
                continue

            nuevo_costo = costo_acum + costo
            nuevo_tiempo = tiempo_acum + tiempo
            if not _cumple_restricciones(
                nuevo_costo,
                nuevo_tiempo,
                presupuesto_max,
                tiempo_maximo,
            ):
                continue

            nuevo_visitados = set(visitados)
            nuevo_visitados.add(vecino)
            stack.append(
                (
                    vecino,
                    camino + [vecino],
                    aristas_camino + [edge],
                    nuevo_visitados,
                    nuevo_costo,
                    nuevo_tiempo,
                    km_acum + distancia_km,
                )
            )

    if not mejor_camino:
        return RouteResult(
            camino=[],
            pasos=[],
            total_km=math.inf,
            encontrado=False,
            error="No existe ruta que cumpla las restricciones.",
        )

    pasos: List[RouteStep] = []
    distancia_acum = 0.0
    for index, edge in enumerate(mejor_aristas):
        destino, _, _, distancia_km, aeronave = edge
        origen = mejor_camino[index]
        distancia_acum += distancia_km
        pasos.append(
            RouteStep(
                origen=origen,
                destino=destino,
                distancia_km=distancia_km,
                distancia_acumulada_km=distancia_acum,
                aeronave=aeronave,
            )
        )

    return RouteResult(
        camino=mejor_camino,
        pasos=pasos,
        total_km=mejor_km,
        encontrado=True,
        error=None,
        total_costo=mejor_costo,
    )