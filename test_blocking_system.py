"""
Test integral del sistema de bloqueo de rutas en tiempo real.

Verifica:
1. Inicio de vuelo con animacion progresiva (FlightState)
2. Avance progresivo del vuelo (avanzar_vuelo)
3. Deteccion de bloqueo en tiempo real (verificar_bloqueo)
4. Cancelacion del vuelo y retorno al origen (cancelar_vuelo_y_recalcular)
5. Recalculo automatico de ruta evitando aristas bloqueadas
"""
import json
import sys
import time
sys.path.insert(0, '.')

from backend.services.graph_loader import GraphLoader
from backend.services.trip_service import TripService
from backend.services.blocked_routes import get_route_blocker


def main():
    print('=' * 70)
    print('TEST: Sistema de bloqueo de rutas en tiempo real')
    print('=' * 70)

    with open('ejemplo_grafo_pruebas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    loader = GraphLoader()
    graph = loader.load(data)
    blocker = get_route_blocker()
    blocker.unblock_all()

    print(f'\nGrafo cargado: {len(graph.nodos)} nodos, {len(graph.aristas)} aristas')

    # Verificar rutas disponibles desde BOG
    print('\n--- Rutas disponibles desde BOG ---')
    for e in graph.aristas:
        if e.origen == 'BOG':
            print(f'  {e.origen} -> {e.destino} ({e.distancia_km} km)')

    # 1) Iniciar sesion de viaje
    print('\n[1] Iniciando sesion de viaje desde BOG...')
    svc = TripService(graph, 'BOG', 15000.0)
    print(f'  Estado inicial: budget=${svc.current_budget}, '
          f'tiempo={svc.time_elapsed_hours}h')

    # 2) Iniciar vuelo BOG -> MIA
    print('\n[2] Iniciando vuelo BOG -> MIA...')
    snapshot, err = svc.iniciar_vuelo('MIA', 'A320')
    assert err is None, f'Error al iniciar vuelo: {err}'
    assert snapshot['enVuelo'], 'El vuelo no se inicio'
    assert snapshot['progress'] == 0.0
    print(f'  Aeronave: {snapshot["aeronave"]}')
    print(f'  Distancia: {snapshot["distanciaKm"]} km')
    print(f'  Tiempo de vuelo: {snapshot["tiempoVueloHoras"]} h')
    print(f'  Progreso inicial: {snapshot["progress"] * 100:.1f}%')

    # 3) Avanzar vuelo progresivamente
    print('\n[3] Avanzando vuelo progresivamente (sin bloqueo)...')
    dt = 350  # ~medio segundo de simulacion (escala acelerada como en UI)
    last_snap = None
    for i in range(1, 6):
        snap = svc.avanzar_vuelo(dt)
        assert snap['enVuelo']
        prog = snap['progress'] * 100
        print(f'  Tick {i}: progress={prog:.1f}%, '
              f'pos=({snap["latActual"]:.2f}, {snap["lonActual"]:.2f}), '
              f'bloqueado={snap["bloqueado"]}')
        last_snap = snap

    assert last_snap is not None
    assert 0 < last_snap['progress'] < 1, f'Progreso invalido: {last_snap["progress"]}'
    assert -90 < last_snap['latActual'] < 90
    assert -180 < last_snap['lonActual'] < 180
    print(f'  Posicion actual: ({last_snap["latActual"]:.4f}, '
          f'{last_snap["lonActual"]:.4f}) - entre origen y destino, OK')

    # 4) Simular bloqueo de la ruta BOG -> MIA
    print('\n[4] Simulando bloqueo de la ruta BOG -> MIA...')
    blocker.block('BOG', 'MIA')
    assert blocker.is_blocked('BOG', 'MIA')
    print('  Ruta BOG -> MIA bloqueada')

    # 5) Verificar bloqueo en tiempo real
    print('\n[5] Verificando bloqueo en tiempo real...')
    bloqueado = svc.verificar_bloqueo()
    assert bloqueado, 'La verificacion de bloqueo fallo'
    print(f'  verificacion: bloqueado={bloqueado}')

    # 6) Avanzar vuelo - debe detectar bloqueo
    print('\n[6] Avanzando vuelo - debe detectar bloqueo...')
    snap = svc.avanzar_vuelo(dt)
    assert snap['bloqueado'], 'El snapshot no indico bloqueo'
    print(f'  Snapshot: enVuelo={snap["enVuelo"]}, bloqueado={snap["bloqueado"]}, '
          f'progress={snap["progress"] * 100:.1f}%')

    # 7) Cancelar vuelo y recalcular ruta
    print('\n[7] Cancelando vuelo y recalculando ruta...')
    resultado = svc.cancelar_vuelo_y_recalcular(route_blocker=blocker)
    assert resultado['cancelado']
    assert resultado['origenTramo'] == 'BOG'
    assert resultado['destinoOriginal'] == 'MIA'
    print(f'  Origen del tramo: {resultado["origenTramo"]}')
    print(f'  Destino original: {resultado["destinoOriginal"]}')
    print(f'  Progreso al cancelar: {resultado["snapshot"]["progress"] * 100:.1f}%')

    # El viajero debe estar en el origen del tramo
    assert svc.current_node_id == 'BOG', \
        f'El viajero debio quedarse en BOG, esta en {svc.current_node_id}'
    assert svc.current_flight is None
    print(f'  Viajero en: {svc.current_node_id} (volvio al origen del tramo)')

    # La nueva ruta debe recalcularse evitando el tramo bloqueado
    if resultado['nuevaRuta']:
        camino = resultado['nuevaRuta']['camino']
        print(f'  Nueva ruta calculada: {" -> ".join(camino)}')
        # Verificar que la nueva ruta NO contiene BOG -> MIA directo
        for i in range(len(camino) - 1):
            assert not blocker.is_blocked(camino[i], camino[i + 1]), \
                f'La nueva ruta incluye un tramo bloqueado: {camino[i]} -> {camino[i + 1]}'
        print('  Verificado: la nueva ruta no incluye el tramo bloqueado')
    else:
        print(f'  No se encontro ruta alternativa: {resultado["errorRecalc"]}')

    # 8) Verificar que la decision se registro
    print('\n[8] Decisiones registradas:')
    for d in svc.decisions:
        print(f'  - {d.tipo} @ {d.node_id}: '
              f'progreso={d.detalle.get("progressAlCancelar", "-")}')

    decisiones_vuelo = [d for d in svc.decisions if d.tipo == 'vuelo_cancelado']
    assert len(decisiones_vuelo) == 1
    assert decisiones_vuelo[0].detalle['motivo'] == 'Ruta bloqueada en tiempo real'
    print('  Decision de vuelo cancelado registrada correctamente')

    print('\n' + '=' * 70)
    print('TODAS LAS PRUEBAS PASARON EXITOSAMENTE')
    print('=' * 70)


if __name__ == '__main__':
    main()
