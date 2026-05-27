from flask import Blueprint, jsonify, request

from .errors import ValidationError
from .services.geocoding import geocode_country
from .services.graph_loader import GraphLoader

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
