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
    StepOptions,
    TripDecision,
    TripReport,
)

# Umbral para poder trabajar: 35 % del presupuesto inicial
TRABAJO_UMBRAL_PORC = 35.0


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

    def realizar_vuelo(
        self, destination_id: str, aircraft_name: str
    ) -> Tuple[StepOptions, Optional[str]]:
        """Realiza un vuelo desde el nodo actual al destino indicado."""
        node = self._current_node()

        # Encontrar la arista
        edge = None
        for e in self.graph.aristas:
            if e.origen == node.id and e.destino == destination_id:
                edge = e
                break

        if edge is None:
            return self.get_step_options(), "No existe ruta entre estos aeropuertos."

        # Obtener configuración de la aeronave
        ac_config = self.aircraft_config.get(aircraft_name)
        if ac_config is None:
            return self.get_step_options(), f"Aeronave '{aircraft_name}' no configurada."

        costo_km = float(ac_config.costo_km)
        tiempo_km = float(ac_config.tiempo_km)

        # Calcular costo y tiempo
        costo_vuelo = edge.distancia_km * costo_km
        costo_total = float(edge.costo_base) + costo_vuelo
        tiempo_vuelo_h = (edge.distancia_km * tiempo_km) / 60.0  # convertir min a horas

        # Validar presupuesto
        if costo_total > self.current_budget:
            return self.get_step_options(), "Presupuesto insuficiente para este vuelo."

        # Validar subsidio (costo_base == 0) no más del 20% de distancia total
        if float(edge.costo_base) == 0.0 or costo_vuelo == 0.0:
            subsidio_limite = self._subsidized_distance_limit()
            if edge.distancia_km > subsidio_limite:
                return (
                    self.get_step_options(),
                    f"Ruta subsidiada supera el 20% de distancia ({subsidio_limite:.0f} km máximo).",
                )

        # Aplicar costos
        self.current_budget -= costo_total
        self.total_spent += costo_total

        # Avanzar tiempo (vuelo + estancia mínima en destino)
        self.time_elapsed_hours += tiempo_vuelo_h + float(edge.estancia_minima)

        # Verificar alimentación durante el vuelo
        self._check_food_during_flight(tiempo_vuelo_h)

        # Actualizar nodo actual
        self.current_node_id = destination_id
        if destination_id not in self.visited_nodes:
            self.visited_nodes.append(destination_id)

        dest_node = self.nodes_by_id.get(destination_id)
        dest_nombre = dest_node.nombre if dest_node else destination_id

        self.decisions.append(TripDecision(
            tipo="vuelo",
            node_id=destination_id,
            detalle={
                "origen": node.id,
                "aeronave": aircraft_name,
                "distanciaKm": edge.distancia_km,
                "costoVuelo": round(costo_vuelo, 2),
                "costoBase": float(edge.costo_base),
                "tiempoVueloHoras": round(tiempo_vuelo_h, 2),
            },
            costo=costo_total,
            ingreso=0.0,
            tiempo_invertido_horas=tiempo_vuelo_h,
        ))

        return self.get_step_options(), None

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
        """Verifica si durante una estancia se necesita alimentación."""
        if self.food_interval <= 0:
            return
        # Simular en pasos de 1 hora si se cruza el umbral
        for _ in range(int(duration_hours)):
            if self._needs_food():
                # Se registra pero no se cobra automáticamente; el sistema
                # le recordará al viajero en el siguiente paso
                pass

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
                tiempo_vuelo_h = (edge.distancia_km * tiempo_km) / 60.0

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

    def _subsidized_distance_limit(self) -> float:
        """Calcula el 20% de la distancia total recorrida para rutas subsidiadas."""
        total_distance = sum(
            d.detalle.get("distanciaKm", 0)
            for d in self.decisions
            if d.tipo == "vuelo"
        )
        return total_distance * 0.20
