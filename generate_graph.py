"""
Generates the example graph JSON with 30+ airports.
Run: python generate_graph.py > grafo_30_aeropuertos.json
"""
import json, math

AIRCRAFT_TYPES = {
    "Avion Comercial": {"costoKm": 0.18, "tiempoKm": 0.12},
    "Avion Regional": {"costoKm": 0.25, "tiempoKm": 0.7},
    "Helice": {"costoKm": 1.1, "tiempoKm": 2.5},
}

AIRPORTS = [
    # id, nombre, ciudad, pais, zonaHoraria, esHub, costoAloj, costoAlim, lat, lon
    ("BOG", "El Dorado", "Bogota", "Colombia", "America/Bogota", True, 80, 15, 4.7022, -74.1469),
    ("MDE", "Jose Maria Cordova", "Medellin", "Colombia", "America/Bogota", False, 65, 12, 6.1678, -75.4268),
    ("BAQ", "Ernesto Cortissoz", "Barranquilla", "Colombia", "America/Bogota", False, 50, 10, 10.8896, -74.7808),
    ("CTG", "Rafael Nunez", "Cartagena", "Colombia", "America/Bogota", False, 70, 14, 10.4425, -75.5130),
    ("LIM", "Jorge Chavez", "Lima", "Peru", "America/Lima", True, 90, 16, -12.0219, -77.1085),
    ("CUZ", "Alejandro Velasco Astete", "Cusco", "Peru", "America/Lima", False, 50, 10, -13.5358, -71.9386),
    ("SCL", "Arturo Merino Benitez", "Santiago", "Chile", "America/Santiago", True, 100, 18, -33.3928, -70.7942),
    ("EZE", "Ministro Pistarini", "Buenos Aires", "Argentina", "America/Argentina/Buenos_Aires", True, 110, 20, -34.8222, -58.5358),
    ("AEP", "Aeroparque", "Buenos Aires", "Argentina", "America/Argentina/Buenos_Aires", False, 85, 16, -34.5625, -58.4156),
    ("COR", "Ingeniero Aeronautico Taravella", "Cordoba", "Argentina", "America/Argentina/Cordoba", False, 60, 12, -31.3236, -64.2080),
    ("GRU", "Guarulhos", "Sao Paulo", "Brasil", "America/Sao_Paulo", True, 120, 22, -23.4356, -46.4731),
    ("GIG", "Galeao", "Rio de Janeiro", "Brasil", "America/Sao_Paulo", True, 130, 24, -22.8092, -43.2506),
    ("BSB", "Presidente Juscelino Kubitschek", "Brasilia", "Brasil", "America/Sao_Paulo", False, 95, 18, -15.8711, -47.9186),
    ("POA", "Salgado Filho", "Porto Alegre", "Brasil", "America/Sao_Paulo", False, 70, 14, -29.9944, -51.1714),
    ("MAO", "Eduardo Gomes", "Manaus", "Brasil", "America/Manaus", False, 80, 15, -3.0389, -60.0506),
    ("UIO", "Mariscal Sucre", "Quito", "Ecuador", "America/Guayaquil", False, 75, 14, -0.1292, -78.3575),
    ("GYE", "Jose Joaquin de Olmedo", "Guayaquil", "Ecuador", "America/Guayaquil", False, 65, 12, -2.1575, -79.8836),
    ("CCS", "Simon Bolivar", "Caracas", "Venezuela", "America/Caracas", True, 85, 16, 10.6012, -66.9917),
    ("VVI", "Viru Viru", "Santa Cruz", "Bolivia", "America/La_Paz", False, 55, 11, -17.6421, -63.1353),
    ("LPB", "El Alto", "La Paz", "Bolivia", "America/La_Paz", False, 50, 10, -16.5133, -68.1923),
    ("MVD", "Carrasco", "Montevideo", "Uruguay", "America/Montevideo", False, 85, 16, -34.7886, -56.2528),
    ("MEX", "Benito Juarez", "Ciudad de Mexico", "Mexico", "America/Mexico_City", True, 95, 17, 19.4326, -99.0072),
    ("CUN", "Cancun", "Cancun", "Mexico", "America/Cancun", True, 110, 20, 21.0365, -86.8771),
    ("GDL", "Miguel Hidalgo", "Guadalajara", "Mexico", "America/Mexico_City", False, 75, 14, 20.5218, -103.3112),
    ("MIA", "Miami International", "Miami", "Estados Unidos", "America/New_York", True, 120, 20, 25.7959, -80.2870),
    ("JFK", "John F. Kennedy", "Nueva York", "Estados Unidos", "America/New_York", True, 150, 25, 40.6413, -73.7781),
    ("LAX", "Los Angeles", "Los Angeles", "Estados Unidos", "America/Los_Angeles", True, 130, 22, 33.9425, -118.4081),
    ("SFO", "San Francisco", "San Francisco", "Estados Unidos", "America/Los_Angeles", False, 140, 24, 37.6213, -122.3790),
    ("IAD", "Washington Dulles", "Washington DC", "Estados Unidos", "America/New_York", False, 130, 22, 38.9531, -77.4565),
    ("ORD", "O'Hare", "Chicago", "Estados Unidos", "America/Chicago", True, 140, 23, 41.9742, -87.9073),
    ("HAV", "Jose Marti", "La Habana", "Cuba", "America/Havana", False, 70, 14, 22.9892, -82.4091),
    ("SDQ", "Las Americas", "Santo Domingo", "Republica Dominicana", "America/Santo_Domingo", False, 85, 16, 18.4297, -69.6689),
    ("SJU", "Luis Munoz Marin", "San Juan", "Puerto Rico", "America/Puerto_Rico", False, 90, 17, 18.4394, -66.0018),
    ("PTY", "Tocumen", "Ciudad de Panama", "Panama", "America/Panama", True, 95, 17, 9.0712, -79.3835),
    ("SJO", "Juan Santamaria", "San Jose", "Costa Rica", "America/Costa_Rica", False, 75, 14, 9.9939, -84.2088),
    ("SAL", "El Salvador", "San Salvador", "El Salvador", "America/El_Salvador", False, 60, 12, 13.4408, -89.0557),
    ("GUA", "La Aurora", "Guatemala", "Guatemala", "America/Guatemala", False, 65, 13, 14.5833, -90.5275),
    ("MAD", "Adolfo Suarez Barajas", "Madrid", "Espana", "Europe/Madrid", True, 160, 28, 40.4725, -3.5607),
    ("CDG", "Charles de Gaulle", "Paris", "Francia", "Europe/Paris", True, 180, 30, 49.0097, 2.5478),
]

# Distance calculation (haversine)
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Build routes between nearby airports (connecting the graph)
# Key connections: hubs connect to nearby cities and to other hubs
ROUTES = [
    # Colombia
    ("BOG", "MDE"), ("BOG", "BAQ"), ("BOG", "CTG"), ("BOG", "UIO"), ("BOG", "GYE"), ("BOG", "CCS"),
    ("MDE", "CTG"), ("MDE", "BAQ"), ("CTG", "BAQ"),
    # Peru
    ("LIM", "CUZ"), ("LIM", "UIO"), ("LIM", "GYE"), ("LIM", "VVI"), ("LIM", "SCL"),
    ("BOG", "LIM"), ("LIM", "MEX"), ("LIM", "PTY"),
    # Chile / Argentina
    ("SCL", "EZE"), ("SCL", "COR"), ("SCL", "MVD"), ("SCL", "POA"),
    ("EZE", "AEP"), ("EZE", "COR"), ("EZE", "MVD"), ("EZE", "POA"), ("EZE", "GRU"),
    ("AEP", "COR"), ("AEP", "MVD"),
    # Brasil
    ("GRU", "GIG"), ("GRU", "BSB"), ("GRU", "POA"), ("GRU", "MAO"), ("GRU", "SCL"), ("GRU", "EZE"),
    ("GIG", "BSB"), ("GIG", "GRU"), ("GIG", "POA"), ("GIG", "MVD"),
    ("BSB", "MAO"), ("BSB", "VVI"), ("BSB", "GRU"), ("BSB", "GIG"),
    ("MAO", "CCS"), ("MAO", "PTY"), ("MAO", "VVI"),
    # Bolivia
    ("VVI", "LPB"), ("VVI", "SCL"), ("VVI", "BSB"), ("VVI", "LIM"),
    ("LPB", "VVI"), ("LPB", "LIM"),
    # Ecuador / Venezuela
    ("UIO", "GYE"), ("UIO", "PTY"), ("UIO", "BOG"),
    ("GYE", "UIO"), ("GYE", "LIM"),
    ("CCS", "PTY"), ("CCS", "MIA"), ("CCS", "SDQ"), ("CCS", "SJU"),
    # Central America / Mexico
    ("MEX", "CUN"), ("MEX", "GDL"), ("MEX", "MIA"), ("MEX", "PTY"), ("MEX", "LAX"), ("MEX", "SFO"),
    ("CUN", "MIA"), ("CUN", "HAV"), ("CUN", "MEX"), ("CUN", "PTY"),
    ("GDL", "MEX"), ("GDL", "LAX"), ("GDL", "SFO"),
    ("PTY", "SJO"), ("PTY", "MIA"), ("PTY", "BOG"), ("PTY", "MEX"), ("PTY", "CCS"), ("PTY", "SDQ"),
    ("SJO", "PTY"), ("SJO", "MIA"), ("SJO", "SAL"), ("SJO", "GUA"),
    ("SAL", "GUA"), ("SAL", "MIA"), ("SAL", "MEX"),
    ("GUA", "MEX"), ("GUA", "MIA"), ("GUA", "SAL"),
    # Caribbean
    ("HAV", "MIA"), ("HAV", "CUN"), ("HAV", "SDQ"), ("HAV", "SJU"), ("HAV", "PTY"),
    ("SDQ", "SJU"), ("SDQ", "MIA"), ("SDQ", "PTY"), ("SDQ", "CCS"),
    ("SJU", "MIA"), ("SJU", "SDQ"), ("SJU", "CCS"), ("SJU", "JFK"),
    # USA
    ("MIA", "JFK"), ("MIA", "LAX"), ("MIA", "SFO"), ("MIA", "IAD"), ("MIA", "ORD"), ("MIA", "MEX"),
    ("MIA", "CUN"), ("MIA", "PTY"), ("MIA", "BOG"), ("MIA", "CCS"),
    ("JFK", "IAD"), ("JFK", "ORD"), ("JFK", "MIA"), ("JFK", "LAX"), ("JFK", "SFO"), ("JFK", "MAD"), ("JFK", "CDG"),
    ("LAX", "SFO"), ("LAX", "ORD"), ("LAX", "MEX"), ("LAX", "GDL"),
    ("SFO", "LAX"), ("SFO", "ORD"), ("SFO", "MEX"),
    ("IAD", "JFK"), ("IAD", "ORD"), ("IAD", "MIA"), ("IAD", "MAD"),
    ("ORD", "JFK"), ("ORD", "LAX"), ("ORD", "SFO"), ("ORD", "IAD"), ("ORD", "MEX"),
    # Europe
    ("MAD", "CDG"), ("MAD", "JFK"), ("MAD", "IAD"), ("MAD", "GRU"), ("MAD", "EZE"),
    ("CDG", "MAD"), ("CDG", "JFK"), ("CDG", "IAD"), ("CDG", "GRU"),
]

def build_graph():
    # Build config
    config = {
        "aeronaves": {k: dict(v) for k, v in AIRCRAFT_TYPES.items()},
        "presupuestoMinimoPorc": 35,
        "intervaloAlojamiento": 20,
        "intervaloAlimentacion": 8,
    }

    # Build nodes
    nodos = []
    airport_ids = set()
    for a in AIRPORTS:
        airport_ids.add(a[0])
        nodo = {
            "id": a[0],
            "nombre": a[1],
            "ciudad": a[2],
            "pais": a[3],
            "zonaHoraria": a[4],
            "esHub": a[5],
            "costoAlojamiento": a[6],
            "costoAlimentacion": a[7],
            "actividades": [
                {"nombre": f"Tour por {a[2]}", "tipo": "opcional", "duracionMin": 120, "costoUSD": round(a[6] * 0.3)},
                {"nombre": f"Museo de {a[2]}", "tipo": "opcional", "duracionMin": 90, "costoUSD": round(a[6] * 0.2)},
            ] if a[5] else [
                {"nombre": f"Visita guiada {a[2]}", "tipo": "opcional", "duracionMin": 60, "costoUSD": round(a[6] * 0.2)},
            ],
            "trabajos": [
                {"nombre": "Cargador de equipaje", "tarifaHora": round(a[6] * 0.15), "maxHoras": 6},
                {"nombre": "Asistente de rampa", "tarifaHora": round(a[6] * 0.18), "maxHoras": 8},
            ] if a[5] else [
                {"nombre": "Limpieza", "tarifaHora": round(a[6] * 0.12), "maxHoras": 6},
            ],
            "lat": a[8],
            "lon": a[9],
        }
        nodos.append(nodo)

    # Build edges with distances
    seen = set()
    aristas = []
    for orig_id, dest_id in ROUTES:
        edge_key = f"{orig_id}-{dest_id}"
        if edge_key in seen:
            continue
        seen.add(edge_key)

        orig = next(a for a in nodos if a["id"] == orig_id)
        dest = next(a for a in nodos if a["id"] == dest_id)
        dist = round(haversine_km(orig["lat"], orig["lon"], dest["lat"], dest["lon"]))

        # Always use commercial as base, add regional for short routes, helice for very short
        aircraft = ["Avion Comercial"]
        if dist < 2000:
            aircraft.append("Avion Regional")
        if dist < 800:
            aircraft.append("Helice")

        # Some routes subsidized
        costo_base = 0.0 if dist < 400 else round(dist * 0.15)

        arista = {
            "origen": orig_id,
            "destino": dest_id,
            "distanciaKm": dist,
            "aeronaves": aircraft,
            "costoBase": costo_base,
            "estanciaMinima": round(max(0.5, dist / 800), 1),
        }
        aristas.append(arista)

    return json.dumps({
        "configuracion": config,
        "nodos": nodos,
        "aristas": aristas,
    }, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    graph_json = build_graph()
    # Verify
    data = json.loads(graph_json)
    print(f"// Generated graph with {len(data['nodos'])} nodes and {len(data['aristas'])} edges", file=__import__('sys').stderr)
    print(graph_json)
