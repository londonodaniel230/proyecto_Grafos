import json
import sys
sys.path.insert(0, '.')
from backend.services.graph_loader import GraphLoader
from backend.services.trip_service import TripService

with open('ejemplo_grafo_pruebas.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

loader = GraphLoader()
graph = loader.load(data)

svc = TripService(graph, 'BOG', 1000)
step = svc.get_step_options()

print('=== Step Options ===')
print(f'Node: {step.node_id} - {step.node_nombre}')
print(f'Budget: ${step.presupuesto_actual}')
print(f'Time: {step.tiempo_transcurrido_horas}h')
print(f'Needs lodging: {step.necesita_alojamiento}')
print(f'Needs food: {step.necesita_alimentacion}')
print(f'Can work: {step.puede_trabajar}')
print(f'Optional activities: {len(step.actividades_opcionales)}')
for a in step.actividades_opcionales:
    print(f'  - {a.nombre}: ${a.costo_usd}, {a.duracion_min}min')
print(f'Jobs: {len(step.trabajos_disponibles)}')
for j in step.trabajos_disponibles:
    print(f'  - {j.nombre}: ${j.tarifa_hora}/h, max {j.max_horas}h')
print(f'Flights: {len(step.vuelos_disponibles)}')
for v in step.vuelos_disponibles:
    print(f'  -> {v["destinoNombre"]} ({v["distanciaKm"]}km)')
    for a in v['aeronaves']:
        print(f'     {a["nombre"]}: ${a["costoTotal"]}, {a["tiempoVueloHoras"]}h')

step2, err = svc.realizar_actividad(0)
print(f'\nActivity result: err={err}, budget={step2.presupuesto_actual}')

step3, err = svc.realizar_vuelo('MIA', 'A320')
print(f'Flight result: err={err}, budget={step3.presupuesto_actual}, node={step3.node_id}')

report = svc.finalizar_viaje()
rd = report.to_dict()
print(f'\nReport: destinos={rd["destinosVisitados"]}, gastado=${rd["totalGastado"]}, ganado=${rd["totalGanado"]}')
print(f'Decisiones: {len(rd["decisiones"])}')
for d in rd['decisiones']:
    print(f'  {d["tipo"]} @ {d["nodeId"]}: costo=${d["costo"]}, ingreso=${d["ingreso"]}')

print('\nAll tests passed!')
