from flask import Blueprint, jsonify, request

from .errors import ValidationError
from .services.geocoding import geocode_country
from .services.graph_loader import GraphLoader
from .services.path_algorithms import CostOptions, TraversalConstraints
from .services.route_optimizer import optimizar_ruta
from .services.trip_service import TripService

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@api_bp.post("/graph")
def upload_graph():
    loader = GraphLoader()
    try:
        payload = _get_payload()
        graph = loader.load(payload)
        return jsonify(graph.to_dict())
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400


@api_bp.post("/route")
def optimize_route():
    loader = GraphLoader()
    try:
        payload = _get_payload()
        if not isinstance(payload, dict):
            raise ValidationError(["JSON body must be an object."])

        graph_payload = payload.get("graph")
        if graph_payload is None:
            raise ValidationError(["Missing graph payload."])

        graph = loader.load(graph_payload)

        inicio_ids = payload.get("inicioIds") or payload.get("inicio_ids")
        destino_ids = payload.get("destinoIds") or payload.get("destino_ids")

        inicio_id = (payload.get("inicioId") or payload.get("inicio_id") or "").strip()
        destino_id = (payload.get("destinoId") or payload.get("destino_id") or "").strip()

        if inicio_ids is not None and not isinstance(inicio_ids, list):
            raise ValidationError(["inicioIds must be an array."])
        if destino_ids is not None and not isinstance(destino_ids, list):
            raise ValidationError(["destinoIds must be an array."])

        if inicio_ids:
            inicio_ids = [str(item).strip() for item in inicio_ids if str(item).strip()]
        if destino_ids:
            destino_ids = [str(item).strip() for item in destino_ids if str(item).strip()]

        if inicio_ids or destino_ids:
            if not inicio_ids or not destino_ids:
                raise ValidationError([
                    "inicioIds and destinoIds are required when using arrays."
                ])
            inicio_id = inicio_ids[0]
            destino_id = destino_ids[0]
        elif not inicio_id or not destino_id:
            raise ValidationError(["inicioId and destinoId are required."])

        modo = (payload.get("modo") or "distancia").strip().lower()
        presupuesto_total = payload.get("presupuestoTotal")
        if presupuesto_total is not None:
            presupuesto_total = float(presupuesto_total)

        tiempo_maximo = payload.get("tiempoMaximo")
        if tiempo_maximo is not None:
            tiempo_maximo = float(tiempo_maximo)

        excluir_secundarios = bool(payload.get("excluirSecundarios", False))

        opciones_raw = payload.get("opciones") or {}
        aeronaves_raw = opciones_raw.get("aeronaves") or []
        aeronaves = None
        if isinstance(aeronaves_raw, list):
            aeronaves = {str(item).strip().lower() for item in aeronaves_raw if str(item).strip()}

        opciones = CostOptions(
            aeronaves_permitidas=aeronaves,
            incluir_alojamiento=bool(opciones_raw.get("incluirAlojamiento", True)),
            incluir_alimentacion=bool(opciones_raw.get("incluirAlimentacion", True)),
            incluir_trabajo=bool(opciones_raw.get("incluirTrabajo", True)),
        )

        restricciones = TraversalConstraints(
            presupuesto_total=presupuesto_total,
            tiempo_maximo=tiempo_maximo,
            excluir_secundarios=excluir_secundarios,
        )

        resultado = optimizar_ruta(
            graph,
            inicio_id,
            destino_id,
            modo=modo,
            presupuesto_total=presupuesto_total,
            opciones=opciones,
            inicio_ids=inicio_ids,
            destino_ids=destino_ids,
            restricciones=restricciones,
        )
        return jsonify(resultado.to_dict())
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400
    except ValueError:
        return jsonify({"errors": ["Invalid numeric values."]}), 400


@api_bp.get("/geocode")
def geocode():
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"errors": ["Missing query parameter."]}), 400

    try:
        results = geocode_country(query)
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400

    if not results:
        return jsonify({"errors": ["No geocoding results."]}), 404

    return jsonify({"results": results})


# ---------------------------------------------------------------------------
# Endpoints para Planificación avanzada con gestión dinámica (2.3)
# ---------------------------------------------------------------------------

# Almacén en memoria de sesiones de viaje
_trip_sessions: dict = {}


@api_bp.post("/trip/start")
def trip_start():
    """
    Inicia un nuevo viaje interactivo.

    Body JSON:
        graph (dict): Grafo cargado y validado.
        originId (str): ID del aeropuerto de origen.
        initialBudget (float): Presupuesto inicial en USD.
    """
    loader = GraphLoader()
    try:
        payload = _get_payload()
        if not isinstance(payload, dict):
            raise ValidationError(["JSON body must be an object."])

        graph_payload = payload.get("graph")
        if graph_payload is None:
            raise ValidationError(["Missing graph payload."])

        graph = loader.load(graph_payload)

        origin_id = (payload.get("originId") or payload.get("origin_id") or "").strip()
        if not origin_id:
            raise ValidationError(["originId is required."])

        initial_budget = payload.get("initialBudget")
        if initial_budget is None:
            raise ValidationError(["initialBudget is required."])
        initial_budget = float(initial_budget)
        if initial_budget <= 0:
            raise ValidationError(["initialBudget must be positive."])

        # Verificar que el nodo existe
        node_ids = {n.id for n in graph.nodos}
        if origin_id not in node_ids:
            raise ValidationError([f"Origin node '{origin_id}' not found."])

        service = TripService(graph, origin_id, initial_budget)
        session_id = str(id(service))
        _trip_sessions[session_id] = service

        step = service.get_step_options()
        return jsonify({
            "sessionId": session_id,
            "step": step.to_dict(),
        })
    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400
    except (ValueError, TypeError):
        return jsonify({"errors": ["Invalid numeric values."]}), 400


@api_bp.post("/trip/act")
def trip_act():
    """
    Ejecuta una acción del viajero y retorna el nuevo estado.

    Body JSON:
        sessionId (str): ID de sesión devuelto por /trip/start.
        action (str): Tipo de acción:
            - "actividad"     → requiere activityIndex
            - "trabajo"       → requiere jobIndex, hours
            - "alojamiento"
            - "alimentacion"
            - "vuelo"         → requiere destinationId, aircraftName
            - "finalizar"
    """
    try:
        payload = _get_payload()
        if not isinstance(payload, dict):
            raise ValidationError(["JSON body must be an object."])

        session_id = payload.get("sessionId")
        service: TripService = _trip_sessions.get(session_id)
        if service is None:
            raise ValidationError(["Invalid or expired session."])

        action = (payload.get("action") or "").strip().lower()

        error = None
        step = None
        report = None

        if action == "actividad":
            idx = payload.get("activityIndex")
            if idx is None or not isinstance(idx, (int, float)):
                step, error = service.get_step_options(), "activityIndex required."
            else:
                step, error = service.realizar_actividad(int(idx))

        elif action == "trabajo":
            idx = payload.get("jobIndex")
            hours = payload.get("hours")
            if idx is None or hours is None:
                step, error = (
                    service.get_step_options(),
                    "jobIndex and hours required.",
                )
            else:
                step, error = service.realizar_trabajo(int(idx), float(hours))

        elif action == "alojamiento":
            step, error = service.realizar_alojamiento()

        elif action == "alimentacion":
            step, error = service.realizar_alimentacion()

        elif action == "vuelo":
            dest_id = payload.get("destinationId") or payload.get("destination_id")
            aircraft = payload.get("aircraftName") or payload.get("aircraft_name")
            if not dest_id or not aircraft:
                step, error = (
                    service.get_step_options(),
                    "destinationId and aircraftName required.",
                )
            else:
                step, error = service.realizar_vuelo(str(dest_id), str(aircraft))

        elif action == "finalizar":
            report = service.finalizar_viaje()
            _trip_sessions.pop(session_id, None)
            return jsonify({"report": report.to_dict()})

        else:
            error = f"Unknown action '{action}'."

        result = {
            "step": step.to_dict() if step else service.get_step_options().to_dict(),
        }
        if error:
            result["error"] = error

        return jsonify(result)

    except ValidationError as exc:
        return jsonify({"errors": exc.errors}), 400
    except (ValueError, TypeError) as exc:
        return jsonify({"errors": [str(exc)]}), 400


def _get_payload():
    if "file" in request.files:
        file = request.files["file"]
        if file.filename == "":
            raise ValidationError(["Empty file name."])
        return file.read()

    if request.is_json:
        payload = request.get_json(silent=True)
        if payload is None:
            raise ValidationError(["Invalid JSON body."])
        return payload

    raise ValidationError(["Provide a JSON file or JSON body."])
