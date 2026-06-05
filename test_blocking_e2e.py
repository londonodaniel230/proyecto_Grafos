"""
Test end-to-end del sistema de bloqueo de rutas via API.

Simula:
1. Cargar el grafo
2. Iniciar sesion de viaje
3. Iniciar un vuelo
4. Avanzar el vuelo varias veces
5. Bloquear la ruta via API
6. Verificar que el servidor detecta el bloqueo
7. Cancelar el vuelo
8. Verificar que la nueva ruta evita el tramo bloqueado
"""
import json
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, '.')

API = 'http://127.0.0.1:5000/api'


def call(method, path, body=None, expect=200):
    url = f'{API}{path}'
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = json.loads(r.read().decode('utf-8'))
            return payload
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8') if e.fp else ''
        print(f'HTTP {e.code} en {method} {path}: {body_text}')
        raise


def main():
    print('=' * 70)
    print('TEST E2E: Sistema de bloqueo de rutas via API')
    print('=' * 70)

    with open('ejemplo_grafo_pruebas.json', 'r', encoding='utf-8') as f:
        graph = json.load(f)

    # 1) Limpiar bloqueos previos
    print('\n[1] Limpiando bloqueos previos...')
    blocked = call('GET', '/route/blocked')
    for b in blocked.get('blocked', []):
        call('POST', '/route/unblock', body={
            'graph': graph,
            'origen': b['origen'],
            'destino': b['destino'],
        })
    print('  OK')

    # 2) Iniciar sesion de viaje
    print('\n[2] Iniciando sesion de viaje...')
    r = call('POST', '/trip/start', body={
        'graph': graph,
        'originId': 'BOG',
        'initialBudget': 15000,
    })
    sid = r['sessionId']
    print(f'  SessionId: {sid}')
    print(f'  Nodo actual: {r["step"]["nodeId"]} ({r["step"]["nodeNombre"]})')
    print(f'  Presupuesto: ${r["step"]["presupuestoActual"]}')

    # 3) Iniciar vuelo
    print('\n[3] Iniciando vuelo BOG -> MIA...')
    r = call('POST', '/trip/act', body={
        'sessionId': sid,
        'action': 'iniciar_vuelo',
        'destinationId': 'MIA',
        'aircraftName': 'A320',
    })
    snap = r['snapshot']
    assert snap['enVuelo']
    print(f'  Progreso inicial: {snap["progress"] * 100:.1f}%')
    print(f'  Tiempo de vuelo: {snap["tiempoVueloHoras"]} h')
    print(f'  Distancia: {snap["distanciaKm"]} km')
    print(f'  Bloqueado: {snap["bloqueado"]}')

    # 4) Avanzar vuelo varias veces
    print('\n[4] Avanzando vuelo progresivamente (sin bloqueo)...')
    for i in range(1, 5):
        r = call('POST', '/trip/act', body={
            'sessionId': sid,
            'action': 'avanzar_vuelo',
            'dtSegundos': 350,
        })
        snap = r['snapshot']
        print(f'  Tick {i}: progress={snap["progress"] * 100:.1f}%, '
              f'pos=({snap["latActual"]:.2f}, {snap["lonActual"]:.2f}), '
              f'bloqueado={snap["bloqueado"]}')

    # 5) Bloquear la ruta via API
    print('\n[5] Bloqueando ruta BOG -> MIA via API...')
    r = call('POST', '/route/block', body={
        'graph': graph,
        'origen': 'BOG',
        'destino': 'MIA',
    })
    print(f'  Estado: {r["status"]}')
    print(f'  Rutas bloqueadas: {r["blocked"]}')
    assert any(b['origen'] == 'BOG' and b['destino'] == 'MIA'
               for b in r['blocked'])

    # 6) Verificar bloqueo via API
    print('\n[6] Verificando bloqueo via API...')
    r = call('POST', '/trip/act', body={
        'sessionId': sid,
        'action': 'verificar_bloqueo',
    })
    print(f'  Bloqueado: {r["bloqueado"]}')
    assert r['bloqueado'], 'El servidor no detecto el bloqueo'

    # 7) Avanzar vuelo - debe detectar bloqueo
    print('\n[7] Avanzando vuelo - debe detectar bloqueo...')
    r = call('POST', '/trip/act', body={
        'sessionId': sid,
        'action': 'avanzar_vuelo',
        'dtSegundos': 350,
    })
    snap = r['snapshot']
    assert snap['bloqueado']
    print(f'  Progreso al detectar: {snap["progress"] * 100:.1f}%')
    print(f'  Bloqueado: {snap["bloqueado"]}')

    # 8) Cancelar vuelo y recalcular
    print('\n[8] Cancelando vuelo y recalculando ruta...')
    r = call('POST', '/trip/act', body={
        'sessionId': sid,
        'action': 'cancelar_vuelo',
    })
    print(f'  Cancelado: {r["cancelado"]}')
    print(f'  Origen del tramo: {r["origenTramo"]}')
    print(f'  Destino original: {r["destinoOriginal"]}')
    if r.get('nuevaRuta'):
        camino = r['nuevaRuta']['camino']
        print(f'  Nueva ruta: {" -> ".join(camino)}')
        # Verificar que no incluye el tramo bloqueado
        for i in range(len(camino) - 1):
            assert not (camino[i] == 'BOG' and camino[i + 1] == 'MIA'), \
                'La nueva ruta incluye el tramo bloqueado'
        print('  Verificado: la nueva ruta NO incluye BOG -> MIA')
    else:
        print(f'  No se encontro ruta alternativa: {r.get("errorRecalc")}')

    # 9) El step debe estar en el origen del tramo
    step = r['step']
    print(f'  Step actual: nodo={step["nodeId"]}, budget=${step["presupuestoActual"]}')
    assert step['nodeId'] == 'BOG'
    print('  Verificado: el viajero volvio al origen del tramo')

    # 10) El nuevo step debe mostrar opciones
    print('\n[9] Opciones disponibles en el origen del tramo:')
    vuelos = step.get('vuelosDisponibles', [])
    print(f'  Vuelos disponibles: {len(vuelos)}')
    for v in vuelos:
        # Verificar que ninguna opcion es BOG -> MIA
        for a in v.get('aeronaves', []):
            if v['destinoId'] == 'MIA':
                print(f'  -> {v["destinoNombre"]} via {a["nombre"]} '
                      f'(${a["costoTotal"]}, {a["tiempoVueloHoras"]}h)')

    print('\n' + '=' * 70)
    print('TEST E2E COMPLETADO EXITOSAMENTE')
    print('=' * 70)


if __name__ == '__main__':
    main()
