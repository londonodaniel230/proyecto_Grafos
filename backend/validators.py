from typing import Any, Dict, List, Optional

from .errors import ValidationError
from .models import Activity, AircraftConfig, Edge, GlobalConfig, Graph, Job, Node

DEFAULT_PRESUPUESTO_MINIMO_PORC = 35.0
DEFAULT_INTERVALO_ALOJAMIENTO = 20.0
DEFAULT_INTERVALO_ALIMENTACION = 8.0

# Valores predeterminados para los tres tipos de aeronave del requerimiento 2.3
# Avión Comercial: 0.18 USD/km, 0.12 min/km
# Avión Regional:  0.25 USD/km, 0.7  min/km
# Hélice:          1.1  USD/km, 2.5  min/km
DEFAULT_AIRCRAFT: dict = {
    "Avión Comercial": AircraftConfig(costo_km=0.18, tiempo_km=0.12),
    "Avión Regional": AircraftConfig(costo_km=0.25, tiempo_km=0.7),
    "Hélice": AircraftConfig(costo_km=1.1, tiempo_km=2.5),
}


class ValidationContext:
    def __init__(self) -> None:
        self.errors: List[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    def raise_if_errors(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


def ensure_object(
    value: Any, path: str, ctx: ValidationContext
) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        ctx.add(f"{path} must be an object.")
        return None
    return value


def ensure_array(value: Any, path: str, ctx: ValidationContext) -> Optional[List[Any]]:
    if not isinstance(value, list):
        ctx.add(f"{path} must be an array.")
        return None
    return value


def ensure_str(value: Any, path: str, ctx: ValidationContext) -> Optional[str]:
    if not isinstance(value, str):
        ctx.add(f"{path} must be a string.")
        return None
    return value


def ensure_bool(value: Any, path: str, ctx: ValidationContext) -> Optional[bool]:
    if not isinstance(value, bool):
        ctx.add(f"{path} must be a boolean.")
        return None
    return value


def ensure_number(value: Any, path: str, ctx: ValidationContext) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        ctx.add(f"{path} must be a number.")
        return None
    return float(value)


def ensure_int(value: Any, path: str, ctx: ValidationContext) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        ctx.add(f"{path} must be an integer.")
        return None
    if int(value) != value:
        ctx.add(f"{path} must be an integer.")
        return None
    return int(value)


def parse_string_list(raw: Any, path: str, ctx: ValidationContext) -> List[str]:
    items = ensure_array(raw, path, ctx)
    if items is None:
        return []
    values: List[str] = []
    for idx, item in enumerate(items):
        if isinstance(item, str):
            values.append(item)
        else:
            ctx.add(f"{path}[{idx}] must be a string.")
    return values


def parse_activity(raw: Any, path: str, ctx: ValidationContext) -> Optional[Activity]:
    obj = ensure_object(raw, path, ctx)
    if obj is None:
        return None

    nombre = ensure_str(obj.get("nombre"), f"{path}.nombre", ctx)
    tipo = ensure_str(obj.get("tipo"), f"{path}.tipo", ctx)
    duracion = ensure_int(obj.get("duracionMin"), f"{path}.duracionMin", ctx)
    costo = ensure_number(obj.get("costoUSD"), f"{path}.costoUSD", ctx)

    if None in (nombre, tipo, duracion, costo):
        return None

    return Activity(
        nombre=nombre,
        tipo=tipo,
        duracion_min=duracion,
        costo_usd=costo,
    )


def parse_activity_list(raw: Any, path: str, ctx: ValidationContext) -> List[Activity]:
    items = ensure_array(raw, path, ctx)
    if items is None:
        return []

    actividades: List[Activity] = []
    for idx, item in enumerate(items):
        actividad = parse_activity(item, f"{path}[{idx}]", ctx)
        if actividad:
            actividades.append(actividad)
    return actividades


def parse_job(raw: Any, path: str, ctx: ValidationContext) -> Optional[Job]:
    obj = ensure_object(raw, path, ctx)
    if obj is None:
        return None

    nombre = ensure_str(obj.get("nombre"), f"{path}.nombre", ctx)
    tarifa = ensure_number(obj.get("tarifaHora"), f"{path}.tarifaHora", ctx)
    max_horas = ensure_int(obj.get("maxHoras"), f"{path}.maxHoras", ctx)

    if None in (nombre, tarifa, max_horas):
        return None

    return Job(nombre=nombre, tarifa_hora=tarifa, max_horas=max_horas)


def parse_job_list(raw: Any, path: str, ctx: ValidationContext) -> List[Job]:
    items = ensure_array(raw, path, ctx)
    if items is None:
        return []

    trabajos: List[Job] = []
    for idx, item in enumerate(items):
        trabajo = parse_job(item, f"{path}[{idx}]", ctx)
        if trabajo:
            trabajos.append(trabajo)
    return trabajos


def parse_node(raw: Any, index: int, ctx: ValidationContext) -> Optional[Node]:
    path = f"nodos[{index}]"
    obj = ensure_object(raw, path, ctx)
    if obj is None:
        return None

    node_id = ensure_str(obj.get("id"), f"{path}.id", ctx)
    nombre = ensure_str(obj.get("nombre"), f"{path}.nombre", ctx)
    ciudad = ensure_str(obj.get("ciudad"), f"{path}.ciudad", ctx)
    pais = ensure_str(obj.get("pais"), f"{path}.pais", ctx)
    zona = ensure_str(obj.get("zonaHoraria"), f"{path}.zonaHoraria", ctx)
    es_hub = ensure_bool(obj.get("esHub"), f"{path}.esHub", ctx)
    costo_aloj = ensure_number(
        obj.get("costoAlojamiento"), f"{path}.costoAlojamiento", ctx
    )
    costo_alim = ensure_number(
        obj.get("costoAlimentacion"), f"{path}.costoAlimentacion", ctx
    )
    actividades = parse_activity_list(obj.get("actividades"), f"{path}.actividades", ctx)
    trabajos = parse_job_list(obj.get("trabajos"), f"{path}.trabajos", ctx)
    lat = ensure_number(obj.get("lat"), f"{path}.lat", ctx) if "lat" in obj else None
    lon = ensure_number(obj.get("lon"), f"{path}.lon", ctx) if "lon" in obj else None

    if None in (node_id, nombre, ciudad, pais, zona, es_hub, costo_aloj, costo_alim):
        return None

    return Node(
        id=node_id,
        nombre=nombre,
        ciudad=ciudad,
        pais=pais,
        zona_horaria=zona,
        es_hub=es_hub,
        costo_alojamiento=costo_aloj,
        costo_alimentacion=costo_alim,
        actividades=actividades,
        trabajos=trabajos,
        lat=lat,
        lon=lon,
    )


def parse_edge(raw: Any, index: int, ctx: ValidationContext) -> Optional[Edge]:
    path = f"aristas[{index}]"
    obj = ensure_object(raw, path, ctx)
    if obj is None:
        return None

    origen = ensure_str(obj.get("origen"), f"{path}.origen", ctx)
    destino = ensure_str(obj.get("destino"), f"{path}.destino", ctx)
    distancia = ensure_number(obj.get("distanciaKm"), f"{path}.distanciaKm", ctx)
    aeronaves = parse_string_list(obj.get("aeronaves"), f"{path}.aeronaves", ctx)
    costo_base = ensure_number(obj.get("costoBase"), f"{path}.costoBase", ctx)
    estancia_min = ensure_number(obj.get("estanciaMinima"), f"{path}.estanciaMinima", ctx)

    if None in (origen, destino, distancia, costo_base, estancia_min):
        return None

    return Edge(
        origen=origen,
        destino=destino,
        distancia_km=distancia,
        aeronaves=aeronaves,
        costo_base=costo_base,
        estancia_minima=estancia_min,
    )


def read_optional_number(
    obj: Dict[str, Any], key: str, path: str, ctx: ValidationContext, default: float
) -> float:
    if key not in obj:
        return default
    value = ensure_number(obj.get(key), f"{path}.{key}", ctx)
    return default if value is None else value


def parse_aircraft_config(raw: Any, ctx: ValidationContext) -> Dict[str, AircraftConfig]:
    aeronaves: Dict[str, AircraftConfig] = {}

    if raw is not None:
        obj = ensure_object(raw, "configuracion.aeronaves", ctx)
        if obj is not None:
            for key, value in obj.items():
                if not isinstance(key, str):
                    ctx.add("configuracion.aeronaves keys must be strings.")
                    continue

                entry = ensure_object(value, f"configuracion.aeronaves.{key}", ctx)
                if entry is None:
                    continue

                costo_km = ensure_number(
                    entry.get("costoKm"), f"configuracion.aeronaves.{key}.costoKm", ctx
                )
                tiempo_km = ensure_number(
                    entry.get("tiempoKm"), f"configuracion.aeronaves.{key}.tiempoKm", ctx
                )

                if None in (costo_km, tiempo_km):
                    continue

                aeronaves[key] = AircraftConfig(costo_km=costo_km, tiempo_km=tiempo_km)

    # Añadir aeronaves por defecto si no están definidas
    for nombre, config in DEFAULT_AIRCRAFT.items():
        if nombre not in aeronaves:
            aeronaves[nombre] = config

    return aeronaves


def _make_default_config() -> GlobalConfig:
    return GlobalConfig(
        aeronaves=dict(DEFAULT_AIRCRAFT),
        presupuesto_minimo_porc=DEFAULT_PRESUPUESTO_MINIMO_PORC,
        intervalo_alojamiento=DEFAULT_INTERVALO_ALOJAMIENTO,
        intervalo_alimentacion=DEFAULT_INTERVALO_ALIMENTACION,
    )


def parse_config(raw: Any, ctx: ValidationContext) -> GlobalConfig:
    if raw is None:
        return _make_default_config()

    obj = ensure_object(raw, "configuracion", ctx)
    if obj is None:
        return _make_default_config()

    aeronaves = parse_aircraft_config(obj.get("aeronaves"), ctx)
    presupuesto = read_optional_number(
        obj,
        "presupuestoMinimoPorc",
        "configuracion",
        ctx,
        DEFAULT_PRESUPUESTO_MINIMO_PORC,
    )
    intervalo_alojamiento = read_optional_number(
        obj,
        "intervaloAlojamiento",
        "configuracion",
        ctx,
        DEFAULT_INTERVALO_ALOJAMIENTO,
    )
    intervalo_alimentacion = read_optional_number(
        obj,
        "intervaloAlimentacion",
        "configuracion",
        ctx,
        DEFAULT_INTERVALO_ALIMENTACION,
    )

    return GlobalConfig(
        aeronaves=aeronaves,
        presupuesto_minimo_porc=presupuesto,
        intervalo_alojamiento=intervalo_alojamiento,
        intervalo_alimentacion=intervalo_alimentacion,
    )


def find_duplicates(values: List[str]) -> List[str]:
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return sorted(duplicates)


class GraphValidator:
    def validate(self, data: Dict[str, Any]) -> Graph:
        ctx = ValidationContext()

        if not isinstance(data, dict):
            raise ValidationError(["Root must be an object."])

        nodes_raw = data.get("nodos")
        edges_raw = data.get("aristas")

        if nodes_raw is None:
            ctx.add("Missing 'nodos' array.")
        if edges_raw is None:
            ctx.add("Missing 'aristas' array.")

        nodes_list = ensure_array(nodes_raw, "nodos", ctx) if nodes_raw is not None else []
        edges_list = ensure_array(edges_raw, "aristas", ctx) if edges_raw is not None else []

        nodes: List[Node] = []
        for idx, raw_node in enumerate(nodes_list or []):
            node = parse_node(raw_node, idx, ctx)
            if node:
                nodes.append(node)

        edge_entries: List[tuple[int, Edge]] = []
        for idx, raw_edge in enumerate(edges_list or []):
            edge = parse_edge(raw_edge, idx, ctx)
            if edge:
                edge_entries.append((idx, edge))

        config = parse_config(data.get("configuracion"), ctx)

        node_ids = [node.id for node in nodes]
        duplicates = find_duplicates(node_ids)
        for duplicate in duplicates:
            ctx.add(f"Duplicate node id: {duplicate}")

        node_id_set = set(node_ids)
        for idx, edge in edge_entries:
            if edge.origen not in node_id_set:
                ctx.add(
                    f"aristas[{idx}].origen '{edge.origen}' not found in nodos."
                )
            if edge.destino not in node_id_set:
                ctx.add(
                    f"aristas[{idx}].destino '{edge.destino}' not found in nodos."
                )

        ctx.raise_if_errors()

        return Graph(
            nodos=nodes,
            aristas=[edge for _, edge in edge_entries],
            configuracion=config,
        )
