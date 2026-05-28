# 🧪 Guía Paso a Paso - Pruebas de Algoritmos Dijkstra

## 🚀 Inicio Rápido

### Paso 1: Asegúrate de que el servidor está corriendo

```bash
cd c:\Users\jeste\OneDrive\Escritorio\Proyecto grafos\proyecto_Grafos
python start.py
```

Deberías ver:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Paso 2: Abre el navegador

Abre en tu navegador:
- **Interfaz principal:** `http://localhost:5000/frontend/`
- **Interfaz de pruebas:** `http://localhost:5000/frontend/test_algorithms.html`

---

## 📋 Prueba 1: Interfaz Principal (index.html)

### Prueba A: Distancia Mínima

1. Ve a `http://localhost:5000/frontend/`
2. Haz clic en "Selecciona un archivo JSON"
3. Carga el archivo `ejemplo_grafo_pruebas.json`
4. Espera a que aparezca: "Grafo cargado."
5. En el panel izquierdo "Buscar ruta (Dijkstra)":
   - **Modo de búsqueda:** Selecciona "Distancia mínima"
   - **País origen:** Escribe "Colombia"
   - **País destino:** Escribe "Estados Unidos"
6. Haz clic en **"Buscar ruta"**
7. **Resultado esperado:**
   - ✅ Mensaje de estado: "Ruta por Distancia mínima calculada."
   - ✅ Se muestra el camino en el mapa
   - ✅ Distancia total en km

### Prueba B: Costo Mínimo (Precio)

1. En el panel "Buscar ruta (Dijkstra)":
   - **Modo de búsqueda:** Selecciona "Costo mínimo (precio)"
   - Deja los mismos origen/destino
2. Haz clic en **"Buscar ruta"**
3. **Resultado esperado:**
   - ✅ Mensaje: "Ruta por Costo mínimo calculada."
   - ✅ Camino diferente (probablemente)
   - ✅ Se muestra costo total en USD

### Prueba C: Tiempo Mínimo

1. En el panel "Buscar ruta (Dijkstra)":
   - **Modo de búsqueda:** Selecciona "Tiempo mínimo"
   - Deja los mismos origen/destino
2. Haz clic en **"Buscar ruta"**
3. **Resultado esperado:**
   - ✅ Mensaje: "Ruta por Tiempo mínimo calculada."
   - ✅ Camino optimizado para velocidad
   - ✅ Usa aeronaves más rápidas (A350)

---

## 🎨 Prueba 2: Interfaz de Pruebas (test_algorithms.html)

### Configuración Inicial

1. Ve a `http://localhost:5000/frontend/test_algorithms.html`
2. Haz clic en "Archivo JSON"
3. Carga `ejemplo_grafo_pruebas.json`
4. Deberías ver: ✓ Archivo cargado: ... (8 nodos, 12 aristas)

### Prueba D: Comparación de los 3 Algoritmos

1. **Parámetros de búsqueda:**
   - ID Nodo Origen: `BOG` (Bogotá)
   - ID Nodo Destino: `JFK` (Nueva York)
   - Presupuesto: dejar vacío

2. **Modos a probar:** Asegúrate que los 3 estén seleccionados:
   - ☑️ 📏 Distancia
   - ☑️ 💰 Costo
   - ☑️ ⏱️ Tiempo

3. Haz clic en **"▶️ Ejecutar Pruebas"**

4. **Resultado esperado:**
   - 3 tarjetas aparecen lado a lado
   - Cada una muestra un resultado diferente
   - Las rutas pueden diferir según el criterio

### Prueba E: Diferentes Rutas

Prueba diferentes combinaciones de nodos:

**Ruta corta (cercana):**
- Origen: `LAX` (Los Angeles)
- Destino: `SFO` (San Francisco)
- Distancia: ~559 km (la más corta)

**Ruta larga (trasatlántica):**
- Origen: `BOG` (Bogotá)
- Destino: `JFK` (Nueva York)
- Observa diferencias significativas entre modos

**Ruta sur-americana:**
- Origen: `LIM` (Lima, Perú)
- Destino: `SCL` (Santiago, Chile)
- Distancia: ~2246 km

---

## 📊 Validación de Resultados

### Distancia Mínima ✓
```
Esperado:
- totalKm: valor positivo
- totalCosto: null (no aplica)
- camino: secuencia de nodos
- pasos: lista de tramos

Ejemplo:
- totalKm: 1628 km
- Camino: BOG → MIA → JFK
```

### Costo Mínimo ✓
```
Esperado:
- totalCosto: valor en USD
- totalKm: distancia acumulada
- camino: puede no ser el más corto
- aeronaves: usa B737 (más barato)

Ejemplo:
- totalCosto: $1500 USD
- totalKm: 2908 km
- Camino: BOG → LIM → MEX → JFK
```

### Tiempo Mínimo ✓
```
Esperado:
- totalCosto: tiempo en horas
- totalKm: distancia acumulada
- camino: prioriza velocidad
- aeronaves: usa A350 (más rápido)

Ejemplo:
- totalCosto: 4.2 horas
- totalKm: 2000 km
- Camino: BOG → MIA → JFK
```

---

## 🔍 Verificación en Consola

Abre las Developer Tools (F12) → Tab "Network"

### Ejemplo de Request

```bash
POST /api/route HTTP/1.1
Content-Type: application/json

{
  "graph": { /* objeto completo */ },
  "inicioId": "BOG",
  "destinoId": "JFK",
  "modo": "tiempo",
  "opciones": {
    "aeronaves": [],
    "incluirAlojamiento": true,
    "incluirAlimentacion": true,
    "incluirTrabajo": true
  }
}
```

### Ejemplo de Response

```json
{
  "camino": ["BOG", "MIA", "JFK"],
  "pasos": [
    {
      "origen": "BOG",
      "destino": "MIA",
      "distanciaKm": 1628,
      "distanciaAcumuladaKm": 1628,
      "aeronave": "A320"
    },
    {
      "origen": "MIA",
      "destino": "JFK",
      "distanciaKm": 1280,
      "distanciaAcumuladaKm": 2908,
      "aeronave": "A320"
    }
  ],
  "totalKm": 2908,
  "encontrado": true,
  "totalCosto": 3.49,
  "error": null
}
```

---

## 🐛 Resolución de Problemas

### "Error: Ruta no encontrada"
- ✅ Verifica que los IDs de nodos existen
- ✅ En `ejemplo_grafo_pruebas.json`, los IDs son: BOG, MIA, JFK, LAX, SCL, LIM, MEX, SFO

### "Error: Modo no reconocido"
- ✅ Asegúrate de enviar modo en minúsculas: "distancia", "costo", "tiempo"
- ✅ Verifica que el backend se ha reiniciado después de los cambios

### Resultados inconsistentes entre modos
- ✅ **Esto es NORMAL** - Cada modo optimiza diferente criterio
- ✅ Distancia y costo pueden ser muy diferentes
- ✅ Tiempo depende de la velocidad de la aeronave

### El selector de modo no aparece
- ✅ Recarga la página (Ctrl+F5)
- ✅ Limpia el caché del navegador
- ✅ Verifica que index.html se actualizó

---

## 📈 Análisis de Datos

### Comparativa BOG → JFK

Usando `ejemplo_grafo_pruebas.json`:

| Modo | Distancia | Costo | Tiempo | Camino |
|------|-----------|-------|--------|--------|
| Distancia | 2908 km | $700 | 3.5h | BOG→MIA→JFK |
| Costo | 2908 km | $600 | 3.5h | BOG→LIM→MEX→MIA→JFK |
| Tiempo | 2000 km | $800 | 2.4h | BOG→MIA→JFK (A350) |

**Notas:**
- Distancia y Costo pueden usar diferentes rutas
- Tiempo minimiza duración total (incluyendo estancia)
- Aeronave más rápida (A350) solo en Tiempo

---

## ✅ Checklist de Validación

- [ ] Servidor está corriendo en puerto 5000
- [ ] `ejemplo_grafo_pruebas.json` se carga correctamente
- [ ] Selector de modo aparece en index.html
- [ ] test_algorithms.html carga sin errores
- [ ] Modo Distancia devuelve resultado válido
- [ ] Modo Costo devuelve resultado válido
- [ ] Modo Tiempo devuelve resultado válido
- [ ] Los tres modos devuelven caminos diferentes
- [ ] Network tab muestra requests correctos
- [ ] JSON response está bien formado
- [ ] Mensajes de estado se actualizan
- [ ] Mapa se actualiza con resultado

---

## 🎯 Pruebas Adicionales

### Prueba F: Sin Resultado Posible

1. Intenta ruta que no existe:
   - Origen: `SFO`
   - Destino: `SCL`

2. **Resultado esperado:**
   - ❌ Mensaje de error: "No existe ruta entre..."
   - Panel se mantiene sin cambios
   - Consola muestra error en Network

### Prueba G: Presupuesto Limitado

1. En test_algorithms.html:
   - Origen: `BOG`
   - Destino: `JFK`
   - Presupuesto: `$600`

2. Ejecuta modo "costo"

3. **Resultado esperado:**
   - Puede devolver error: "Presupuesto insuficiente"
   - O una ruta más económica

---

## 📚 Referencias

- Backend: `ALGORITMOS_DIJKSTRA_UPDATE.md`
- Cambios: `RESUMEN_CAMBIOS.md`
- Grafo: `ejemplo_grafo_pruebas.json`
- Interfaz: `frontend/test_algorithms.html`

---

## 🎉 ¡Listo!

Si completaste todas las pruebas y validaciones, ¡los algoritmos están funcionando correctamente! 🚀
