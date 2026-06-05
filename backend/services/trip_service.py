# -*- coding: utf-8 -*-
"""
trip_service.py  –  Planificación interactiva paso a paso (requerimiento 2.3)

Gestiona un viaje interactivo en el que el viajero decide en cada paso:
  - Actividades opcionales (tours, museos, etc.)
  - Trabajos temporales (cuando el presupuesto cae por debajo del 35%)
  - Aeronave para cada tramo
  - Cuándo alojarse y alimentarse (requerimientos obligatorios)

Cada decisión queda registrada y al final se genera un reporte completo.
"""

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from ..models import (
    Activity,
    Edge,
    Graph,
    Job,
    Node,
    RouteResult,
    StepOptions,
    TripDecision,
    TripReport,
)

# Umbral para poder trabajar: 35 % del presupuesto inicial
TRABAJO_UMBRAL_PORC = 35.0


class FlightState:
    """Estado del vuelo en curso (movimiento progresivo)."""

    def __init__(
        self,
        edge: Edge,
        aircraft_name: str,
        tiempo_vuelo_h: float,
        estancia_h: float,
        costo_total: float,
        costo_vuelo: float,
    ) -> None:
        self.edge = edge
        self.origen_id = edge.origen
        self.destino_id = edge.destino
        self.aircraft_name = aircraft_name
        self.tiempo_vuelo_h = tiempo_vuelo_h
        self.estancia_h = estancia_h
        self.costo_total = costo_total
        self.costo_vuelo = costo_vuelo
        self.progress = 0.0
        self.elapsed_h = 0.0
        self.cancelled = False
        self.completed = False


class TripService:
    """Servicio que gestiona una sesión de viaje interactivo paso a paso."""

    def __init__(self, graph: Graph, origin_id: str, initial_budget: float) -> None:
        self.graph = graph
        self.nodes_by_id: Dict[str, Node] = {n.id: n for n in graph.nodos}
        self.config = graph.configuracion

        self.origin_id = origin_id
        self.current_node_id = origin_id
        self.visited_nodes: List[str] = [origin_id]

        self.initial_budget = initial_budget
        self.current_budget = initial_budget
        self.total_spent = 0.0
        self.total_earned = 0.0

        self.time_elapsed_hours = 0.0
        self.last_lodging_time = 0.0
        self.last_food_time = 0.0
        self.last_food_node_id = origin_id

        self.decisions: List[TripDecision] = []
        self.completed = False

        self.current_flight: Optional[FlightState] = None
        self.destination_target_id: Optional[str] = None

        self._init_config_values()

    def _init_config_values(self) -> None:
        cfg = self.config
        self.lodging_interval = float(getattr(cfg, "intervalo_alojamiento", 20.0) or 20.0)
        self.food_interval = float(getattr(cfg, "intervalo_alimentacion", 8.0) or 8.0)
        self.aircraft_config = getattr(cfg, "aeronaves", {}) or {}

    # ------------------------------------------------------------------
    # Acceso público al estado
    # ------------------------------------------------------------------

    def get_step_options(self) -> StepOptions:
        """Retorna las opciones disponibles para el paso actual."""
        node = self._current_node()

        necesita_aloj = self._needs_lodging()
        necesita_alim = self._needs_food()

        # Trabajos disponibles solo si el presupuesto es bajo
        puede_trabajar = (
            self.current_budget < self.initial_budget * TRABAJO_UMBRAL_PORC / 100.0
        )

        # Actividades opcionales en este nodo (solo las de tipo != "obligatoria")
        actividades = [
            a
            for a in (node.actividades or [])
            if a.tipo.strip().lower() != "obligatoria"
        ]

        # Trabajos disponibles
        trabajos = node.trabajos or []

        # Vuelos disponibles
        vuelos = self._available_flights()

        return StepOptions(
            node_id=node.id,
            node_nombre=node.nombre,
            node_ciudad=node.ciudad,
            node_pais=node.pais,
            presupuesto_actual=self.current_budget,
            presupuesto_inicial=self.initial_budget,
            tiempo_transcurrido_horas=self.time_elapsed_hours,
            total_gastado=self.total_spent,
            total_ganado=self.total_earned,
            destinos_visitados=list(self.visited_nodes),
            puede_trabajar=puede_trabajar,
            necesita_alojamiento=necesita_aloj,
            necesita_alimentacion=necesita_alim,
            costo_alojamiento=float(node.costo_alojamiento or 0),
            costo_alimentacion=float(node.costo_alimentacion or 0),
            actividades_opcionales=actividades,
            trabajos_disponibles=trabajos,
            vuelos_disponibles=vuelos,
            viaje_completado=self.completed,
        )

    # ------------------------------------------------------------------
    # Acciones del viajero
    # ------------------------------------------------------------------

    def realizar_actividad(
        self, activity_index: int
    ) -> Tuple[StepOptions, Optional[str]]:
        """Realiza una actividad opcional del nodo actual."""
        node = self._current_node()
        actividades = [a for a in (node.actividades or []) if a.tipo.strip().lower() != "obligatoria"]

        if activity_index < 0 or activity_index >= len(actividades):
            return self.get_step_options(), "Índice de actividad inválido."

        actividad = actividades[activity_index]
        costo = float(actividad.costo_usd or 0)
        duracion_h = float(actividad.duracion_min or 0) / 60.0

        if costo > self.current_budget:
            return self.get_step_options(), "Presupuesto insuficiente para esta actividad."

        self.current_budget -= costo
        self.total_spent += costo
        self.time_elapsed_hours += duracion_h
        self._check_food_during_stay(duracion_h)

        self.decisions.append(TripDecision(
            tipo="actividad",
            node_id=node.id,
            detalle={"nombre": actividad.nombre, "tipo": actividad.tipo},
            costo=costo,
            ingreso=0.0,
            tiempo_invertido_horas=duracion_h,
        ))

        return self.get_step_options(), None

    def realizar_trabajo(
        self, job_index: int, hours: float
    ) -> Tuple[StepOptions, Optional[str]]:
        """Realiza un trabajo temporal en el nodo actual."""
        node = self._current_node()
        trabajos = node.trabajos or []

        if job_index < 0 or job_index >= len(trabajos):
            return self.get_step_options(), "Índice de trabajo inválido."

        trabajo = trabajos[job_index]
        max_horas = int(trabajo.max_horas or 0)

        if hours <= 0:
            return self.get_step_options(), "Las horas deben ser mayores a cero."
        if hours > max_horas:
            return (
                self.get_step_options(),
                f"Máximo permitido para {trabajo.nombre}: {max_horas} horas.",
            )

        ingreso = float(trabajo.tarifa_hora or 0) * hours
        self.current_budget += ingreso
        self.total_earned += ingreso
        self.time_elapsed_hours += hours
        self._check_food_during_stay(hours)

        self.decisions.append(TripDecision(
            tipo="trabajo",
            node_id=node.id,
            detalle={
                "nombre": trabajo.nombre,
                "tarifaHora": trabajo.tarifa_hora,
                "horasTrabajadas": hours,
            },
            costo=0.0,
            ingreso=ingreso,
            tiempo_invertido_horas=hours,
        ))

        return self.get_step_options(), None

    def realizar_alojamiento(self) -> Tuple[StepOptions, Optional[str]]:
        """Paga el alojamiento obligatorio."""
        node = self._current_node()
        costo = float(node.costo_alojamiento or 0)

        if costo > self.current_budget:
            return self.get_step_options(), "Presupuesto insuficiente para el alojamiento."

        self.current_budget -= costo
        self.total_spent += costo
        self.last_lodging_time = self.time_elapsed_hours
        # El alojamiento ocupa 8 horas (una noche)
        duracion = 8.0
        self.time_elapsed_hours += duracion
        self._check_food_during_stay(duracion)

        self.decisions.append(TripDecision(
            tipo="alojamiento",
            node_id=node.id,
            detalle={"costo": costo, "duracionHoras": duracion},
            costo=costo,
            ingreso=0.0,
            tiempo_invertido_horas=duracion,
        ))

        return self.get_step_options(), None

    def realizar_alimentacion(self) -> Tuple[StepOptions, Optional[str]]:
        """Paga la alimentación obligatoria."""
        # Si estamos en un nodo, usamos su costo; si estamos en vuelo, del último nodo
        node = self._current_node()
        costo = float(node.costo_alimentacion or 0)

        if costo > self.current_budget:
            return self.get_step_options(), "Presupuesto insuficiente para la alimentación."

        self.current_budget -= costo
        self.total_spent += costo
        self.last_food_time = self.time_elapsed_hours
        self.last_food_node_id = node.id
        # La alimentación ocupa 1 hora
        duracion = 1.0
        self.time_elapsed_hours += duracion

        self.decisions.append(TripDecision(
            tipo="alimentacion",
            node_id=node.id,
            detalle={"costo": costo, "duracionHoras": duracion},
            costo=costo,
            ingreso=0.0,
            tiempo_invertido_horas=duracion,
        ))

        return self.get_step_options(), None

    def iniciar_vuelo(
        self, destination_id: str, aircraft_name: str
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Inicia un vuelo progresivo desde el nodo actual al destino indicado.

        No teletransporta al viajero: crea un FlightState que se actualiza
        mediante ``avanzar_vuelo``. Devuelve información de la posición
        inicial y los datos de la animación.
        """
        if self.current_flight is not None:
            return self._flight_snapshot(), "Ya hay un vuelo en curso."

        node = self._current_node()

        edge = None
        for e in self.graph.aristas:
            if e.origen == node.id and e.destino == destination_id:
                edge = e
                break

        if edge is None:
            return {
                "enVuelo": False,
                "nodeId": node.id,
            }, "No existe ruta entre estos aeropuertos."

        ac_config = self.aircraft_config.get(aircraft_name)
        if ac_config is None:
            return {
                "enVuelo": False,
                "nodeId": node.id,
            }, f"Aeronave '{aircraft_name}' no configurada."

        costo_km = float(ac_config.costo_km)
        tiempo_km = float(ac_config.tiempo_km)

        costo_vuelo = edge.distancia_km * costo_km
        costo_total = float(edge.costo_base) + costo_vuelo
        tiempo_vuelo_h = edge.distancia_km * tiempo_km

        if costo_total > self.current_budget:
            return {
                "enVuelo": False,
                "nodeId": node.id,
            }, "Presupuesto insuficiente para este vuelo."

        if float(edge.costo_base) == 0.0 or costo_vuelo == 0.0:
            subsidio_limite = self._subsidized_distance_limit(edge.distancia_km)
            if edge.distancia_km > subsidio_limite:
                return {
                    "enVuelo": False,
                    "nodeId": node.id,
                }, (
                    f"Ruta subsidiada supera el 20% de distancia "
                    f"({subsidio_limite:.0f} km máximo)."
                )

        # Descontar costo y registrar inicio
        self.current_budget -= costo_total
        self.total_spent += costo_total

        self.current_flight = FlightState(
            edge=edge,
            aircraft_name=aircraft_name,
            tiempo_vuelo_h=tiempo_vuelo_h,
            estancia_h=float(edge.estancia_minima),
            costo_total=costo_total,
            costo_vuelo=costo_vuelo,
        )
        self.destination_target_id = destination_id

        return self._flight_snapshot(), None

    def realizar_vuelo(
        self, destination_id: str, aircraft_name: str
    ) -> Tuple[StepOptions, Optional[str]]:
        """Compatibilidad: inicia el vuelo y lo completa de inmediato."""
        snapshot, error = self.iniciar_vuelo(destination_id, aircraft_name)
        if error:
            return self.get_step_options(), error

        # Completar inmediatamente (modo síncrono, para tests / uso sin UI)
        node = self._current_node()
        flight = self.current_flight
        if flight is None:
            return self.get_step_options(), "Vuelo no disponible."

        flight.elapsed_h = flight.tiempo_vuelo_h
        flight.progress = 1.0
        self._finalizar_vuelo(snapshot_origen_id=node.id)
        return self.get_step_options(), None

    def avanzar_vuelo(self, dt_segundos: float) -> Dict[str, Any]:
        """
        Avanza la simulación del vuelo en curso en ``dt_segundos`` segundos.

        Devuelve un snapshot con el progreso, posición interpolada y estado
        del vuelo (``enVuelo``, ``completado``, ``bloqueado``).
        """
        if self.current_flight is None:
            return {
                "enVuelo": False,
                "completado": False,
                "bloqueado": False,
                "nodeId": self.current_node_id,
                "progress": 0.0,
            }

        flight = self.current_flight
        if flight.completed or flight.cancelled:
            return self._flight_snapshot()

        total_time = flight.tiempo_vuelo_h * 3600.0
        if total_time <= 0:
            flight.progress = 1.0
            flight.elapsed_h = flight.tiempo_vuelo_h
        else:
            flight.elapsed_h = min(
                flight.tiempo_vuelo_h,
                flight.elapsed_h + dt_segundos / 3600.0,
            )
            flight.progress = flight.elapsed_h / flight.tiempo_vuelo_h

        if flight.progress >= 1.0:
            self._finalizar_vuelo(snapshot_origen_id=None)

        return self._flight_snapshot()

    def verificar_bloqueo(self, route_blocker=None) -> bool:
        """Retorna True si el segmento actual está bloqueado en tiempo real."""
        if self.current_flight is None:
            return False
        if route_blocker is None:
            from .blocked_routes import get_route_blocker
            route_blocker = get_route_blocker()
        return route_blocker.is_blocked(
            self.current_flight.origen_id,
            self.current_flight.destino_id,
        )

    def cancelar_vuelo_y_recalcular(
        self, route_blocker=None
    ) -> Dict[str, Any]:
        """
        Cancela el vuelo en curso, devuelve al viajero al origen del tramo
        y recalcula una nueva ruta hasta el destino original, evitando el
        tramo bloqueado.

        Retorna un diccionario con:
            - cancelado: True
            - nuevaRuta: RouteResult.to_dict() o None si no hay ruta
            - snapshot: snapshot final del vuelo cancelado
        """
        if self.current_flight is None:
            return {
                "cancelado": False,
                "error": "No hay vuelo en curso.",
            }

        flight = self.current_flight
        flight.cancelled = True
        origen_tramo = flight.origen_id
        destino_original = self.destination_target_id or flight.destino_id

        # El viajero se queda en el origen del tramo cancelado
        self.current_node_id = origen_tramo
        self.current_flight = None

        # Intentar recalcular una ruta alternativa
        nueva_ruta: Optional[RouteResult] = None
        error_recalc: Optional[str] = None
        try:
            from .route_optimizer import optimizar_ruta

            blocked = route_blocker.get_blocked() if route_blocker else []
            nueva_ruta = optimizar_ruta(
                self.graph,
                origen_tramo,
                destino_original,
                modo="distancia",
                rutas_bloqueadas=blocked,
            )
            if not nueva_ruta.encontrado:
                error_recalc = nueva_ruta.error
        except Exception as exc:  # noqa: BLE001
            error_recalc = str(exc)

        # Registrar la cancelación como decisión
        self.decisions.append(TripDecision(
            tipo="vuelo_cancelado",
            node_id=origen_tramo,
            detalle={
                "origen": origen_tramo,
                "destinoOriginal": destino_original,
                "aeronave": flight.aircraft_name,
                "distanciaKm": flight.edge.distancia_km,
                "progressAlCancelar": round(flight.progress, 3),
                "motivo": "Ruta bloqueada en tiempo real",
            },
            costo=0.0,
            ingreso=0.0,
            tiempo_invertido_horas=0.0,
        ))

        return {
            "cancelado": True,
            "origenTramo": origen_tramo,
            "destinoOriginal": destino_original,
            "nuevaRuta": nueva_ruta.to_dict() if nueva_ruta and nueva_ruta.encontrado else None,
            "errorRecalc": error_recalc,
            "snapshot": {
                "origenId": origen_tramo,
                "destinoId": flight.destino_id,
                "progress": flight.progress,
                "completado": False,
                "bloqueado": True,
                "enVuelo": False,
            },
        }

    def _finalizar_vuelo(self, snapshot_origen_id: Optional[str]) -> None:
        """Marca el vuelo como completado y aplica tiempos/costos al estado."""
        if self.current_flight is None:
            return

        flight = self.current_flight
        flight.completed = True
        flight.progress = 1.0

        # Aplicar tiempo total (vuelo + estancia mínima)
        self.time_elapsed_hours += flight.tiempo_vuelo_h + flight.estancia_h

        # Alimentación durante el vuelo
        self._check_food_during_flight(flight.tiempo_vuelo_h)

        # Mover al destino
        self.current_node_id = flight.destino_id
        if flight.destino_id not in self.visited_nodes:
            self.visited_nodes.append(flight.destino_id)

        self.decisions.append(TripDecision(
            tipo="vuelo",
            node_id=flight.destino_id,
            detalle={
                "origen": flight.origen_id,
                "aeronave": flight.aircraft_name,
                "distanciaKm": flight.edge.distancia_km,
                "costoVuelo": round(flight.costo_vuelo, 2),
                "costoBase": float(flight.edge.costo_base),
                "tiempoVueloHoras": round(flight.tiempo_vuelo_h, 2),
            },
            costo=flight.costo_total,
            ingreso=0.0,
            tiempo_invertido_horas=flight.tiempo_vuelo_h,
        ))

        self.current_flight = None
        self.destination_target_id = None

    def _flight_snapshot(self) -> Dict[str, Any]:
        """Devuelve un snapshot de la posición actual del vuelo en curso."""
        if self.current_flight is None:
            return {
                "enVuelo": False,
                "completado": False,
                "bloqueado": False,
                "nodeId": self.current_node_id,
                "progress": 0.0,
            }

        flight = self.current_flight
        origen = self.nodes_by_id.get(flight.origen_id)
        destino = self.nodes_by_id.get(flight.destino_id)
        if not origen or not destino:
            return {
                "enVuelo": False,
                "completado": False,
                "nodeId": self.current_node_id,
                "progress": 0.0,
            }

        lat_o = float(origen.lat or 0.0)
        lon_o = float(origen.lon or 0.0)
        lat_d = float(destino.lat or 0.0)
        lon_d = float(destino.lon or 0.0)

        cur_lat = lat_o + (lat_d - lat_o) * flight.progress
        cur_lon = lon_o + (lon_d - lon_o) * flight.progress

        return {
            "enVuelo": True,
            "completado": flight.completed,
            "bloqueado": self.verificar_bloqueo(),
            "progress": flight.progress,
            "origenId": flight.origen_id,
            "destinoId": flight.destino_id,
            "origenNombre": origen.nombre,
            "destinoNombre": destino.nombre,
            "latOrigen": lat_o,
            "lonOrigen": lon_o,
            "latDestino": lat_d,
            "lonDestino": lon_d,
            "latActual": cur_lat,
            "lonActual": cur_lon,
            "distanciaKm": flight.edge.distancia_km,
            "aeronave": flight.aircraft_name,
            "tiempoVueloHoras": round(flight.tiempo_vuelo_h, 3),
            "estanciaHoras": round(flight.estancia_h, 3),
            "costoTotal": round(flight.costo_total, 2),
            "nodeId": self.current_node_id,
        }

    def finalizar_viaje(self) -> TripReport:
        """Finaliza el viaje y genera el reporte."""
        self.completed = True

        # Contar decisiones
        vuelos = 0
        actividades = 0
        trabajos = 0
        alojamientos = 0
        alimentos = 0

        for d in self.decisions:
            if d.tipo == "vuelo":
                vuelos += 1
            elif d.tipo == "actividad":
                actividades += 1
            elif d.tipo == "trabajo":
                trabajos += 1
            elif d.tipo == "alojamiento":
                alojamientos += 1
            elif d.tipo == "alimentacion":
                alimentos += 1

        return TripReport(
            camino=list(self.visited_nodes),
            decisiones=list(self.decisions),
            total_gastado=self.total_spent,
            total_ganado=self.total_earned,
            presupuesto_final=self.current_budget,
            tiempo_total_horas=self.time_elapsed_hours,
            destinos_visitados=len(self.visited_nodes),
            vuelos_realizados=vuelos,
            actividades_realizadas=actividades,
            trabajos_realizados=trabajos,
            alojamientos_pagados=alojamientos,
            alimentos_consumidos=alimentos,
        )

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _current_node(self) -> Node:
        return self.nodes_by_id.get(self.current_node_id, self.graph.nodos[0])

    def _needs_lodging(self) -> bool:
        if self.lodging_interval <= 0:
            return False
        return (self.time_elapsed_hours - self.last_lodging_time) >= self.lodging_interval

    def _needs_food(self) -> bool:
        if self.food_interval <= 0:
            return False
        return (self.time_elapsed_hours - self.last_food_time) >= self.food_interval

    def _check_food_during_stay(self, duration_hours: float) -> None:
        """Verifica si durante una estancia se necesita alimentación y cobra automáticamente."""
        if self.food_interval <= 0:
            return
        for _ in range(int(duration_hours)):
            if self._needs_food():
                node = self._current_node()
                costo = float(node.costo_alimentacion or 0)
                if costo <= self.current_budget:
                    self.current_budget -= costo
                    self.total_spent += costo
                    self.last_food_time = self.time_elapsed_hours
                    self.decisions.append(TripDecision(
                        tipo="alimentacion",
                        node_id=node.id,
                        detalle={
                            "costo": costo,
                            "duracionHoras": 1.0,
                            "automatico": True,
                            "motivo": "Durante estancia",
                        },
                        costo=costo,
                        ingreso=0.0,
                        tiempo_invertido_horas=1.0,
                    ))

    def _check_food_during_flight(self, flight_hours: float) -> None:
        """Si durante el vuelo se cumplen 8h de alimentación, se cobra del último nodo."""
        if self.food_interval <= 0:
            return
        hours_until_food = self.food_interval - (
            self.time_elapsed_hours - self.last_food_time - flight_hours
        )
        if hours_until_food <= 0:
            # Debe alimentarse; usamos el costo del último nodo visitado
            node = self._current_node()
            costo = float(node.costo_alimentacion or 0)
            if costo <= self.current_budget:
                self.current_budget -= costo
                self.total_spent += costo
                self.last_food_time = self.time_elapsed_hours - flight_hours
                self.decisions.append(TripDecision(
                    tipo="alimentacion",
                    node_id=node.id,
                    detalle={
                        "costo": costo,
                        "duracionHoras": 1.0,
                        "automatico": True,
                        "motivo": "Durante vuelo",
                    },
                    costo=costo,
                    ingreso=0.0,
                    tiempo_invertido_horas=1.0,
                ))

    def _available_flights(self) -> List[Dict[str, Any]]:
        """Retorna los vuelos disponibles desde el nodo actual."""
        node = self._current_node()
        flights: List[Dict[str, Any]] = []

        for edge in self.graph.aristas:
            if edge.origen != node.id:
                continue

            dest_node = self.nodes_by_id.get(edge.destino)
            if dest_node is None:
                continue

            # Aeronaves disponibles para esta ruta con costos y tiempos
            aeronaves_opciones = []
            for aeronave_name in (edge.aeronaves or []):
                ac_config = self.aircraft_config.get(aeronave_name)
                if ac_config is None:
                    continue

                costo_km = float(ac_config.costo_km)
                tiempo_km = float(ac_config.tiempo_km)
                costo_vuelo = edge.distancia_km * costo_km
                costo_total = float(edge.costo_base) + costo_vuelo
                tiempo_vuelo_h = edge.distancia_km * tiempo_km

                # Marcar si es subsidiada
                es_subsidiada = float(edge.costo_base) == 0.0 or costo_vuelo == 0.0

                aeronaves_opciones.append({
                    "nombre": aeronave_name,
                    "costoKm": costo_km,
                    "tiempoKm": tiempo_km,
                    "costoVuelo": round(costo_vuelo, 2),
                    "costoTotal": round(costo_total, 2),
                    "tiempoVueloHoras": round(tiempo_vuelo_h, 2),
                    "esSubsidiada": es_subsidiada,
                })

            flights.append({
                "destinoId": edge.destino,
                "destinoNombre": dest_node.nombre,
                "destinoCiudad": dest_node.ciudad,
                "distanciaKm": edge.distancia_km,
                "costoBase": float(edge.costo_base),
                "estanciaMinima": float(edge.estancia_minima),
                "aeronaves": aeronaves_opciones,
            })

        return flights

    def _subsidized_distance_limit(self, candidate_distance: float = 0) -> float:
        """Calcula el 20% de la distancia total esperada para rutas subsidiadas."""
        total_distance = sum(
            d.detalle.get("distanciaKm", 0)
            for d in self.decisions
            if d.tipo == "vuelo"
        )
        expected_total = total_distance + candidate_distance
        if expected_total <= 0:
            return 0.0
        return expected_total * 0.20
