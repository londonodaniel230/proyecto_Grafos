import math
from typing import Dict, List, Optional, Set, Tuple

from ..models import Edge, Graph, Node, RouteResult, RouteStep
from .path_algorithms import CostOptions


def _greedy_route(
    graph: Graph,
    origen_id: str,
    presupuesto: Optional[float] = None,
    tiempo_maximo: Optional[float] = None,
) -> Tuple[List[str], List[Tuple[Edge, str, float, float]], float, float]:
    nodos_por_id = {n.id: n for n in graph.nodos}
    aristas_por_origen: Dict[str, List[Edge]] = {}
    for arista in graph.aristas:
        aristas_por_origen.setdefault(arista.origen, []).append(arista)

    config = graph.configuracion
    aeronaves_cfg = getattr(config, "aeronaves", {}) if config else {}

    camino: List[str] = [origen_id]
    aristas_usadas: List[Tuple[Edge, str, float, float]] = []
    visitados: Set[str] = {origen_id}
    costo_acum = 0.0
    tiempo_acum = 0.0
    aeronaves_usadas: Set[str] = set()
    aeronaves_disponibles = set(aeronaves_cfg.keys())

    while True:
        actual = camino[-1]
        mejor_opcion: Optional[Tuple[Edge, str, float, float]] = None
        mejor_puntaje = -1.0

        for arista in aristas_por_origen.get(actual, []):
            if arista.destino in visitados:
                continue
            for aeronave in (arista.aeronaves or []):
                ac_entry = aeronaves_cfg.get(aeronave)
                if ac_entry is None:
                    continue
                costo_km = float(getattr(ac_entry, "costo_km", 0.0) or 0.0)
                tiempo_km = float(getattr(ac_entry, "tiempo_km", 0.0) or 0.0)

                costo_tramo = float(arista.costo_base) + arista.distancia_km * costo_km
                tiempo_tramo = (arista.distancia_km * tiempo_km) / 60.0 + arista.estancia_minima

                nuevo_costo = costo_acum + costo_tramo
                nuevo_tiempo = tiempo_acum + tiempo_tramo

                if presupuesto is not None and nuevo_costo > presupuesto:
                    continue
                if tiempo_maximo is not None and nuevo_tiempo > tiempo_maximo:
                    continue

                # Prefer: less cost, more diverse aircraft, more destinations
                diversidad = 1.0 if aeronave not in aeronaves_usadas else 0.0
                # Score: higher = better (favors low cost and high diversity)
                score = diversidad * 10.0 - (costo_tramo / 100.0)
                if presupuesto is not None:
                    score = diversidad * 10.0 - (costo_tramo / 100.0)
                else:
                    score = diversidad * 10.0 - (tiempo_tramo / 10.0)

                if mejor_opcion is None or score > mejor_puntaje:
                    mejor_opcion = (arista, aeronave, costo_tramo, tiempo_tramo)
                    mejor_puntaje = score

        if mejor_opcion is None:
            break

        arista, aeronave, costo_tramo, tiempo_tramo = mejor_opcion
        camino.append(arista.destino)
        aristas_usadas.append((arista, aeronave, costo_tramo, tiempo_tramo))
        visitados.add(arista.destino)
        costo_acum += costo_tramo
        tiempo_acum += tiempo_tramo
        aeronaves_usadas.add(aeronave)

    return camino, aristas_usadas, costo_acum, tiempo_acum


def _build_result(
    camino: List[str],
    aristas_usadas: List[Tuple[Edge, str, float, float]],
    aeronaves_cfg: dict,
) -> RouteResult:
    if len(camino) < 2:
        return RouteResult(
            camino=[], pasos=[], total_km=math.inf,
            encontrado=False, error="No se encontraron rutas dentro de las restricciones.",
        )

    pasos: List[RouteStep] = []
    distancia_acum = 0.0
    costo_total = 0.0
    for edge, aeronave, costo_tramo, _ in aristas_usadas:
        distancia_acum += edge.distancia_km
        costo_total += costo_tramo
        pasos.append(RouteStep(
            origen=edge.origen, destino=edge.destino,
            distancia_km=edge.distancia_km,
            distancia_acumulada_km=distancia_acum,
            aeronave=aeronave,
        ))

    return RouteResult(
        camino=camino, pasos=pasos,
        total_km=distancia_acum, encontrado=True,
        total_costo=costo_total,
    )


def planificar_mejor_ruta(
    graph: Graph,
    origen_id: str,
    presupuesto: Optional[float] = None,
    tiempo_maximo: Optional[float] = None,
) -> RouteResult:
    config = graph.configuracion
    aeronaves_cfg = getattr(config, "aeronaves", {}) if config else {}

    camino, aristas_usadas, costo, tiempo = _greedy_route(
        graph, origen_id, presupuesto=presupuesto, tiempo_maximo=tiempo_maximo,
    )

    if len(camino) < 2:
        # Try from each possible first-hop
        nodos_por_id = {n.id: n for n in graph.nodos}
        aristas_por_origen: Dict[str, List[Edge]] = {}
        for arista in graph.aristas:
            aristas_por_origen.setdefault(arista.origen, []).append(arista)

        mejor_resultado: Optional[RouteResult] = None
        mejor_len = 0

        for arista in aristas_por_origen.get(origen_id, []):
            for aeronave in (arista.aeronaves or []):
                ac_entry = aeronaves_cfg.get(aeronave)
                if ac_entry is None:
                    continue
                costo_km = float(getattr(ac_entry, "costo_km", 0.0) or 0.0)
                tiempo_km = float(getattr(ac_entry, "tiempo_km", 0.0) or 0.0)
                ct = float(arista.costo_base) + arista.distancia_km * costo_km
                tt = (arista.distancia_km * tiempo_km) / 60.0 + arista.estancia_minima

                if presupuesto is not None and ct > presupuesto:
                    continue
                if tiempo_maximo is not None and tt > tiempo_maximo:
                    continue

                sub_camino, sub_aristas, sub_costo, sub_tiempo = _greedy_route(
                    graph, arista.destino,
                    presupuesto=presupuesto - ct if presupuesto else None,
                    tiempo_maximo=tiempo_maximo - tt if tiempo_maximo else None,
                )
                full_camino = [origen_id] + sub_camino
                full_aristas = [(arista, aeronave, ct, tt)] + sub_aristas

                if len(full_camino) > mejor_len:
                    mejor_len = len(full_camino)
                    mejor_resultado = _build_result(full_camino, full_aristas, aeronaves_cfg)

        if mejor_resultado:
            return mejor_resultado

    return _build_result(camino, aristas_usadas, aeronaves_cfg)


def planificar_dos_alternativas(
    graph: Graph,
    origen_id: str,
    presupuesto_total: float,
    tiempo_total_horas: float,
) -> Dict[str, RouteResult]:
    resultado_presupuesto = planificar_mejor_ruta(
        graph, origen_id, presupuesto=presupuesto_total
    )
    resultado_tiempo = planificar_mejor_ruta(
        graph, origen_id, tiempo_maximo=tiempo_total_horas
    )
    return {
        "porPresupuesto": resultado_presupuesto,
        "porTiempo": resultado_tiempo,
    }
