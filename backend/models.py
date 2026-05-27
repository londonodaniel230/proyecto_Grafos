from dataclasses import dataclass
from typing import Dict, List, Optional


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
