# Documentación de Actualización - Algoritmos Dijkstra

## Resumen de Cambios

Se ha actualizado el frontend y el backend para soportar **tres algoritmos de búsqueda de rutas óptimas** usando Dijkstra:

1. **Distancia Mínima** (`modo: "distancia"`)
2. **Costo Mínimo** (`modo: "costo"`) - Precio mínimo
3. **Tiempo Mínimo** (`modo: "tiempo"`) - ⭐ **NUEVO**

---

## 📦 Backend - Cambios en `/backend`

### 1. **path_algorithms.py**
Se agregaron las siguientes funciones:

#### `_seleccionar_aeronave_mas_rapida()`
- Selecciona la aeronave más rápida según `tiempo_km` de la configuración
- Similar a `_seleccionar_aeronave_mas_barata()` pero optimiza por tiempo

#### `_build_adjacency_por_tiempo()`
- Construye el mapa de adyacencia ponderado por tiempo
- Calcula: `tiempo_total = (distancia_km * tiempo_km) + estancia_minima`
- Retorna tuplas: `(destino_id, tiempo_total, distancia_km, aeronave)`

#### `dijkstra_por_tiempo()`
- **Nuevo algoritmo principal** que implementa Dijkstra por tiempo mínimo
- Parámetros:
  - `graph`: Grafo cargado
  - `inicio_id`, `destino_id`: Nodos origen y destino
  - `opciones`: CostOptions para filtrar aeronaves
  - `inicio_ids`, `destino_ids`: Listas múltiples (opcional)
- Retorna: `RouteResult` con `total_costo` = tiempo total en horas

### 2. **route_optimizer.py**
Se actualizó el registro de algoritmos:

```python
_ALGORITMOS = {
    "distancia": dijkstra_por_distancia,
    "costo": dijkstra_por_costo,
    "tiempo": dijkstra_por_tiempo,  # ⭐ NUEVO
}
```

Se actualizó `optimizar_ruta()` para manejar el nuevo modo:
```python
elif modo_normalizado == "tiempo":
    return algoritmo(
        graph,
        inicio_id,
        destino_id,
        opciones=opciones,
        inicio_ids=inicio_ids,
        destino_ids=destino_ids,
    )
```

---

## 🎨 Frontend - Cambios en `/frontend`

### 1. **index.html**
Se agregó un selector de modo en el formulario "Buscar ruta":

```html
<div class="field">
  <label for="search-mode">Modo de búsqueda</label>
  <select id="search-mode">
    <option value="distancia">Distancia mínima</option>
    <option value="costo" selected>Costo mínimo (precio)</option>
    <option value="tiempo">Tiempo mínimo</option>
  </select>
</div>
```

### 2. **route_search_controller.js**
Se actualizó el controlador para:

- Cachear el elemento `#search-mode` selector
- Leer el valor seleccionado del modo
- Enviar el modo seleccionado en el payload

```javascript
const modo = (this.modeSelect ? this.modeSelect.value : "costo") || "costo";
```

- Mostrar mensaje dinámico según el modo con `_getModoLabel()`

### 3. **test_algorithms.html** ⭐ **NUEVO**
Interfaz de pruebas visual e interactiva para comparar los tres algoritmos:

**Características:**
- 📁 Cargar archivo JSON del grafo
- 🔍 Seleccionar modos a probar (checkboxes)
- 📊 Ejecutar pruebas en paralelo
- 🎨 Resultados lado a lado con estilos diferenciados
- 📈 Comparación de métricas (distancia, costo, tiempo)
- 💾 Respuesta JSON completa visible

**Acceso:**
```
http://localhost:5000/frontend/test_algorithms.html
```

---

## 🧪 Cómo Probar

### Opción 1: Interfaz Principal (index.html)

1. Abre `http://localhost:5000/frontend/`
2. Carga un archivo JSON
3. En el panel "Buscar ruta (Dijkstra)", selecciona el modo:
   - Distancia mínima
   - Costo mínimo
   - Tiempo mínimo
4. Ingresa los países origen y destino
5. Haz clic en "Buscar ruta"

### Opción 2: Interfaz de Pruebas (test_algorithms.html)

1. Abre `http://localhost:5000/frontend/test_algorithms.html`
2. Carga un archivo JSON
3. Ingresa los IDs de nodos (ej: `node1`, `node5`)
4. Selecciona los modos a probar
5. Haz clic en "Ejecutar Pruebas"
6. **Compara los resultados lado a lado** en tarjetas de colores:
   - 🟨 Amarillo: Distancia
   - 🟩 Verde: Costo
   - 🟦 Azul: Tiempo

---

## 📊 Formato de Respuesta

Todos los modos retornan un `RouteResult` con esta estructura:

```json
{
  "camino": ["node1", "node3", "node5"],
  "pasos": [
    {
      "origen": "node1",
      "destino": "node3",
      "distanciaKm": 150.5,
      "distanciaAcumuladaKm": 150.5,
      "aeronave": "A320"
    },
    {
      "origen": "node3",
      "destino": "node5",
      "distanciaKm": 200.0,
      "distanciaAcumuladaKm": 350.5,
      "aeronave": "B737"
    }
  ],
  "totalKm": 350.5,
  "encontrado": true,
  "totalCosto": 5.2,
  "error": null
}
```

**Interpretación de `totalCosto` según modo:**
- **distancia**: No incluye (es null)
- **costo**: Costo total en USD
- **tiempo**: Tiempo total en horas

---

## 🔧 Requisitos del Grafo

El archivo JSON debe incluir la configuración de aeronaves con `tiempo_km`:

```json
{
  "configuracion": {
    "aeronaves": {
      "A320": {
        "costoKm": 5.5,
        "tiempoKm": 0.0012
      },
      "B737": {
        "costoKm": 4.8,
        "tiempoKm": 0.0014
      }
    },
    "presupuestoMinimoPorc": 10,
    "intervaloAlojamiento": 24,
    "intervaloAlimentacion": 8
  },
  "nodos": [...],
  "aristas": [...]
}
```

---

## 📋 Endpoint API

**POST** `/api/route`

**Payload:**
```json
{
  "graph": { /* objeto Graph completo */ },
  "inicioId": "node1",
  "destinoId": "node5",
  "modo": "distancia|costo|tiempo",
  "presupuestoTotal": 5000,
  "opciones": {
    "aeronaves": ["A320"],
    "incluirAlojamiento": true,
    "incluirAlimentacion": true,
    "incluirTrabajo": true
  }
}
```

---

## 📌 Notas Importantes

1. **Modo "tiempo"**: Reutiliza el campo `total_costo` en `RouteResult` para almacenar el tiempo total en horas
2. **Aeronaves**: Se elige la más rápida (menor `tiempo_km`) para cada modo
3. **Estancia mínima**: Se suma al tiempo total en modo "tiempo"
4. **Compatibilidad**: Los cambios son **retrocompatibles** - código existente sigue funcionando
5. **Test HTML**: La interfaz de pruebas NO requiere modificar el servidor

---

## 🚀 Próximos Pasos

- [ ] Agregar visualización de tiempos en mapas (tiempo estimado por tramo)
- [ ] Implementar modo "equilibrio" (peso ponderado de múltiples criterios)
- [ ] Agregar caché de resultados
- [ ] Tests unitarios para los nuevos algoritmos
- [ ] Validación exhaustiva con datos de prueba

---

## ✅ Validación

Para validar que todo funciona:

1. Abre la consola del navegador (F12)
2. Ve a "Network" tab
3. Ejecuta una búsqueda en cada modo
4. Verifica que la respuesta contiene:
   - `"encontrado": true`
   - `"totalKm"`: valor numérico > 0
   - `"totalCosto"`: valor numérico (costo/tiempo según modo)
   - `"pasos"`: array no vacío
   - `"camino"`: array con al menos 2 nodos
