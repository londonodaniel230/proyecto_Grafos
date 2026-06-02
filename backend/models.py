# -*- coding: utf-8 -*-
"""
models.py
Modelos de datos del backend.

Clases originales (sin cambios):
    Activity, Job, Node, Edge, AircraftConfig, GlobalConfig, Graph

Clases añadidas por PERSONA 1 – Algoritmos y lógica de rutas:
    RouteStep   – detalle de un tramo individual dentro de una ruta.
    RouteResult – resultado completo devuelto por los algoritmos de ruta.

Clases añadidas para 2.3 – Planificación avanzada con gestión dinámica:
    TripDecision – una decisión tomada en un paso del viaje interactivo.
    StepOptions  – opciones disponibles al viajero en un paso concreto.
    TripState    – estado completo del viaje interactivo.
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ===========================================================================
# Modelos originales (NO MODIFICAR)
# ===========================================================================

@dataclass(frozen=True)
class Activity:
    nombre: str
    tipo: str
    duracion_min: int
    costo_usd: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "nombre": self.nombre,
            "tipo": self.tipo,
            "duracionMin": self.duracion_min,
            "costoUSD": self.costo_usd,
        }


@dataclass(frozen=True)
class Job:
    nombre: str
    tarifa_hora: float
    max_horas: int

    def to_dict(self) -> Dict[str, object]:
        return {
            "nombre": self.nombre,
            "tarifaHora": self.tarifa_hora,
            "maxHoras": self.max_horas,
        }


@dataclass(frozen=True)
class Node:
    id: str
    nombre: str
    ciudad: str
    pais: str
    zona_horaria: str
    es_hub: bool
    costo_alojamiento: float
    costo_alimentacion: float
    actividades: List[Activity]
    trabajos: List[Job]
    lat: Optional[float] = None
    lon: Optional[float] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "id": self.id,
            "nombre": self.nombre,
            "ciudad": self.ciudad,
            "pais": self.pais,
            "zonaHoraria": self.zona_horaria,
            "esHub": self.es_hub,
            "costoAlojamiento": self.costo_alojamiento,
            "costoAlimentacion": self.costo_alimentacion,
            "actividades": [actividad.to_dict() for actividad in self.actividades],
            "trabajos": [trabajo.to_dict() for trabajo in self.trabajos],
        }

        if self.lat is not None:
            payload["lat"] = self.lat
        if self.lon is not None:
            payload["lon"] = self.lon

        return payload


@dataclass(frozen=True)
class Edge:
    origen: str
    destino: str
    distancia_km: float
    aeronaves: List[str]
    costo_base: float
    estancia_minima: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "origen": self.origen,
            "destino": self.destino,
            "distanciaKm": self.distancia_km,
            "aeronaves": self.aeronaves,
            "costoBase": self.costo_base,
            "estanciaMinima": self.estancia_minima,
        }


@dataclass(frozen=True)
class AircraftConfig:
    costo_km: float
    tiempo_km: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "costoKm": self.costo_km,
            "tiempoKm": self.tiempo_km,
        }


@dataclass(frozen=True)
class GlobalConfig:
    aeronaves: Dict[str, AircraftConfig]
    presupuesto_minimo_porc: float
    intervalo_alojamiento: float
    intervalo_alimentacion: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "aeronaves": {
                key: value.to_dict() for key, value in self.aeronaves.items()
            },
            "presupuestoMinimoPorc": self.presupuesto_minimo_porc,
            "intervaloAlojamiento": self.intervalo_alojamiento,
            "intervaloAlimentacion": self.intervalo_alimentacion,
        }


@dataclass(frozen=True)
class Graph:
    nodos: List[Node]
    aristas: List[Edge]
    configuracion: Optional[GlobalConfig]

    def to_dict(self) -> Dict[str, object]:
        return {
            "nodos": [nodo.to_dict() for nodo in self.nodos],
            "aristas": [arista.to_dict() for arista in self.aristas],
            "configuracion": self.configuracion.to_dict() if self.configuracion else None,
        }


# ===========================================================================
# Nuevos modelos – PERSONA 1 / Algoritmos y lógica de rutas
# ===========================================================================

@dataclass
class RouteStep:
    """
    Representa un tramo individual dentro de una ruta calculada.

    Atributos
    ---------
    origen                : ID del nodo de salida del tramo.
    destino               : ID del nodo de llegada del tramo.
    distancia_km          : distancia de este tramo en kilómetros.
    distancia_acumulada_km: distancia total recorrida hasta llegar a ``destino``.
    aeronave              : tipo de aeronave disponible para el tramo (puede
                            ser None si la arista no especifica ninguna).
    """

    origen: str
    destino: str
    distancia_km: float
    distancia_acumulada_km: float
    aeronave: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "origen": self.origen,
            "destino": self.destino,
            "distanciaKm": self.distancia_km,
            "distanciaAcumuladaKm": self.distancia_acumulada_km,
            "aeronave": self.aeronave,
        }


@dataclass
class RouteResult:
    """
    Resultado completo devuelto por cualquier algoritmo de ruta.

    Atributos
    ---------
    camino      : lista de IDs de nodos en orden de visita
                  (vacía si no se encontró ruta).
    pasos       : lista de RouteStep con el detalle de cada tramo.
    total_km    : distancia total de la ruta en km
                  (math.inf si no se encontró ruta).
    total_costo : costo total de la ruta (USD) si aplica.
    encontrado  : True si existe una ruta válida, False en caso contrario.
    error       : mensaje descriptivo cuando ``encontrado`` es False.
    """

    camino: List[str]
    pasos: List[RouteStep]
    total_km: float
    encontrado: bool
    total_costo: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        total_km = self.total_km if not math.isinf(self.total_km) else None
        total_costo = None
        if self.total_costo is not None and not math.isinf(self.total_costo):
            total_costo = self.total_costo

        return {
            "camino": self.camino,
            "pasos": [paso.to_dict() for paso in self.pasos],
            "totalKm": total_km,
            "totalCosto": total_costo,
            "encontrado": self.encontrado,
            "error": self.error,
        }


# ===========================================================================
# Modelos PLANIFICACION AVANZADA – 2.3
# ===========================================================================

@dataclass
class TripDecision:
    """Registro de una decisión tomada durante el viaje interactivo."""

    tipo: str  # "vuelo", "alojamiento", "alimentacion", "actividad", "trabajo", "tiempo_libre", "fin"
    node_id: str
    detalle: Dict[str, Any]
    costo: float
    ingreso: float
    tiempo_invertido_horas: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tipo": self.tipo,
            "nodeId": self.node_id,
            "detalle": self.detalle,
            "costo": self.costo,
            "ingreso": self.ingreso,
            "tiempoInvertidoHoras": self.tiempo_invertido_horas,
        }


@dataclass
class StepOptions:
    """Opciones disponibles al viajero en un paso concreto del viaje."""

    # Información del paso actual
    node_id: str
    node_nombre: str
    node_ciudad: str
    node_pais: str

    # Estado actual del viaje
    presupuesto_actual: float
    presupuesto_inicial: float
    tiempo_transcurrido_horas: float
    total_gastado: float
    total_ganado: float
    destinos_visitados: List[str]
    puede_trabajar: bool  # True si presupuesto < 35% del inicial

    # Requerimientos obligatorios
    necesita_alojamiento: bool
    necesita_alimentacion: bool
    costo_alojamiento: float
    costo_alimentacion: float

    # Actividades opcionales disponibles en este nodo
    actividades_opcionales: List[Activity]

    # Trabajos disponibles en este nodo
    trabajos_disponibles: List[Job]

    # Vuelos disponibles desde este nodo
    vuelos_disponibles: List[Dict[str, Any]]

    # Viaje completado?
    viaje_completado: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodeId": self.node_id,
            "nodeNombre": self.node_nombre,
            "nodeCiudad": self.node_ciudad,
            "nodePais": self.node_pais,
            "presupuestoActual": self.presupuesto_actual,
            "presupuestoInicial": self.presupuesto_inicial,
            "tiempoTranscurridoHoras": self.tiempo_transcurrido_horas,
            "totalGastado": self.total_gastado,
            "totalGanado": self.total_ganado,
            "destinosVisitados": self.destinos_visitados,
            "puedeTrabajar": self.puede_trabajar,
            "necesitaAlojamiento": self.necesita_alojamiento,
            "necesitaAlimentacion": self.necesita_alimentacion,
            "costoAlojamiento": self.costo_alojamiento,
            "costoAlimentacion": self.costo_alimentacion,
            "actividadesOpcionales": [a.to_dict() for a in self.actividades_opcionales],
            "trabajosDisponibles": [j.to_dict() for j in self.trabajos_disponibles],
            "vuelosDisponibles": self.vuelos_disponibles,
            "viajeCompletado": self.viaje_completado,
        }


@dataclass
class TripReport:
    """Reporte final del viaje interactivo."""

    camino: List[str]
    decisiones: List[TripDecision]
    total_gastado: float
    total_ganado: float
    presupuesto_final: float
    tiempo_total_horas: float
    destinos_visitados: int
    vuelos_realizados: int
    actividades_realizadas: int
    trabajos_realizados: int
    alojamientos_pagados: int
    alimentos_consumidos: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camino": self.camino,
            "decisiones": [d.to_dict() for d in self.decisiones],
            "totalGastado": round(self.total_gastado, 2),
            "totalGanado": round(self.total_ganado, 2),
            "presupuestoFinal": round(self.presupuesto_final, 2),
            "tiempoTotalHoras": round(self.tiempo_total_horas, 2),
            "destinosVisitados": self.destinos_visitados,
            "vuelosRealizados": self.vuelos_realizados,
            "actividadesRealizadas": self.actividades_realizadas,
            "trabajosRealizados": self.trabajos_realizados,
            "alojamientosPagados": self.alojamientos_pagados,
            "alimentosConsumidos": self.alimentos_consumidos,
        }