# 🧭 Proyecto Grafos - Algoritmos Dijkstra Actualizados

## 📋 Descripción General

Aplicación web interactiva para visualizar y analizar grafos de rutas aéreas. Implementa **tres algoritmos de Dijkstra** para encontrar rutas óptimas según diferentes criterios:

- 📏 **Distancia Mínima**
- 💰 **Costo Mínimo** (Precio)
- ⏱️ **Tiempo Mínimo** ⭐ **NUEVO**

---

## 🚀 Inicio Rápido

### Requisitos
- Python 3.8+
- Flask
- Navegador web moderno

### Instalación

```bash
# Clona o abre el proyecto
cd proyecto_Grafos

# (Opcional) Crea un entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instala dependencias (si es necesario)
pip install flask

# Inicia el servidor
python start.py
```

### Acceso

- **Principal:** http://localhost:5000/frontend/
- **Pruebas:** http://localhost:5000/frontend/test_algorithms.html

---

## 📁 Estructura del Proyecto

```
proyecto_Grafos/
├── backend/
│   ├── app_factory.py           # Creador de aplicación Flask
│   ├── errors.py                # Manejo de errores
│   ├── models.py                # Modelos de datos (Graph, Node, Edge, etc.)
│   ├── routes.py                # Rutas API
│   ├── validators.py            # Validadores
│   └── services/
│       ├── geocoding.py         # Servicio de geocodificación
│       ├── graph_loader.py      # Cargador de grafo
│       ├── path_algorithms.py   # ⭐ Algoritmos Dijkstra (ACTUALIZADO)
│       └── route_optimizer.py   # ⭐ Optimizador de rutas (ACTUALIZADO)
├── frontend/
│   ├── index.html               # ⭐ Interfaz principal (ACTUALIZADA)
│   ├── test_algorithms.html     # ⭐ Interfaz de pruebas (NUEVA)
│   ├── css/
│   │   └── styles.css           # Estilos
│   └── js/
│       ├── app.js               # Inicialización
│       ├── api_client.js        # Cliente API
│       ├── graph_layout.js      # Layout del grafo
│       ├── graph_renderer.js    # Renderer del grafo
│       ├── graph_store.js       # Almacenamiento de grafo
│       ├── map_renderer.js      # Renderer de mapa (Leaflet)
│       ├── controllers/
│       │   ├── route_form_controller.js     # Controlador de formulario
│       │   └── route_search_controller.js   # ⭐ Controlador búsqueda (ACTUALIZADO)
│       ├── services/
│       │   ├── geocode_service.js
│       │   └── node_factory.js
│       └── ui/
│           └── status_panel.js
├── start.py                     # Entrada principal
├── ejemplo_grafo_pruebas.json  # ⭐ Grafo de ejemplo (NUEVO)
├── ALGORITMOS_DIJKSTRA_UPDATE.md   # ⭐ Documentación técnica (NUEVO)
├── RESUMEN_CAMBIOS.md              # ⭐ Resumen de cambios (NUEVO)
└── GUIA_PRUEBAS_PASO_A_PASO.md     # ⭐ Guía de pruebas (NUEVO)
```

---

## 🎯 Cambios Principales

### ✅ Backend (Python)

#### `services/path_algorithms.py`
- ✅ Nueva función `_seleccionar_aeronave_mas_rapida()`
- ✅ Nueva función `_build_adjacency_por_tiempo()`
- ✅ **Nuevo algoritmo: `dijkstra_por_tiempo()`**

#### `services/route_optimizer.py`
- ✅ Registrado modo "tiempo" en algoritmos
- ✅ Actualizada lógica de `optimizar_ruta()`

### ✅ Frontend (JavaScript/HTML)

#### `index.html`
- ✅ Agregado selector de modo (Distancia/Costo/Tiempo)
- ✅ Actualizado título del panel

#### `route_search_controller.js`
- ✅ Soporte para lectura de modo dinámico
- ✅ Mensajes de estado según modo seleccionado

#### `test_algorithms.html` ⭐ NUEVO
- ✅ Interfaz dedicada para pruebas comparativas
- ✅ Resultados lado a lado
- ✅ Selección flexible de modos
- ✅ Respuesta JSON en vivo

---

## 📊 API Endpoints

### POST `/api/graph`
Carga un grafo desde un archivo JSON.

**Respuesta:** Objeto Graph validado

### POST `/api/route`
Calcula ruta óptima según el modo.

**Parámetros:**
```json
{
  "graph": { /* objeto Graph */ },
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

**Respuesta:**
```json
{
  "camino": ["node1", "node3", "node5"],
  "pasos": [...],
  "totalKm": 350.5,
  "totalCosto": 5.2,
  "encontrado": true,
  "error": null
}
```

---

## 🧪 Pruebas

### Opción 1: Interfaz Principal
```
http://localhost:5000/frontend/
```
- Carga JSON
- Selecciona modo (Distancia/Costo/Tiempo)
- Ingresa origen y destino
- Haz clic "Buscar ruta"

### Opción 2: Interfaz de Pruebas
```
http://localhost:5000/frontend/test_algorithms.html
```
- Carga JSON
- Selecciona modos
- Ejecuta pruebas
- Compara resultados lado a lado

### Datos de Ejemplo
Usa `ejemplo_grafo_pruebas.json`:
- 8 nodos (ciudades)
- 12 aristas (rutas)
- 3 aeronaves con precios y tiempos

---

## 📚 Documentación Adicional

| Archivo | Contenido |
|---------|-----------|
| `ALGORITMOS_DIJKSTRA_UPDATE.md` | Detalles técnicos completos |
| `RESUMEN_CAMBIOS.md` | Resumen ejecutivo de cambios |
| `GUIA_PRUEBAS_PASO_A_PASO.md` | Instrucciones de prueba |
| `ejemplo_grafo_pruebas.json` | Datos de ejemplo |

---

## 🔧 Algoritmos

### Dijkstra por Distancia
```python
dijkstra_por_distancia(graph, inicio_id, destino_id)
```
- **Peso:** distancia_km
- **Objetivo:** Minimizar distancia total
- **Retorna:** totalKm (distancia)

### Dijkstra por Costo
```python
dijkstra_por_costo(graph, inicio_id, destino_id, 
                   presupuesto_total, opciones, ...)
```
- **Peso:** costo_base + (distancia × costo_km) + costo_estancia
- **Objetivo:** Minimizar costo (USD)
- **Retorna:** totalCosto (USD)

### Dijkstra por Tiempo ⭐ NUEVO
```python
dijkstra_por_tiempo(graph, inicio_id, destino_id, opciones, ...)
```
- **Peso:** (distancia × tiempo_km) + estancia_minima
- **Objetivo:** Minimizar tiempo total
- **Retorna:** totalCosto (tiempo en horas)

---

## 🎯 Casos de Uso

### 1. Viaje más corto
```javascript
modo: "distancia"
```
↓ Resultado: Camino con menor distancia

### 2. Viaje más económico
```javascript
modo: "costo",
presupuestoTotal: 5000
```
↓ Resultado: Ruta bajo presupuesto

### 3. Viaje más rápido
```javascript
modo: "tiempo"
```
↓ Resultado: Ruta con menor tiempo total

---

## 🌟 Características

- ✅ 3 algoritmos de Dijkstra implementados
- ✅ Interfaz web moderna y responsive
- ✅ Visualización de grafo en mapa (Leaflet)
- ✅ Comparación de resultados
- ✅ Validación de entrada robusta
- ✅ Manejo de errores completo
- ✅ Documentación completa
- ✅ Ejemplos de datos

---

## 🔐 Validación

El proyecto valida:
- ✅ Nodos origen/destino existen
- ✅ Formato JSON válido
- ✅ Modo de optimización reconocido
- ✅ Presupuesto (si aplica)
- ✅ Aeronaves permitidas
- ✅ Rutas posibles existen

---

## 📊 Compatibilidad

| Componente | Requisito |
|-----------|-----------|
| Python | 3.8+ |
| Flask | 1.0+ |
| Navegador | ES6+ (Chrome, Firefox, Safari, Edge) |
| Leaflet | 1.9.4 |

---

## 🐛 Resolución de Problemas

### El servidor no inicia
```bash
# Verifica Python
python --version

# Reinstala dependencias
pip install flask --upgrade
```

### El selector de modo no aparece
```bash
# Recarga la página
Ctrl + F5  # Windows/Linux
Cmd + Shift + R  # Mac

# Limpia caché
# Abre DevTools → Application → Clear site data
```

### "Ruta no encontrada"
- Verifica que los nodos existen en el grafo
- Comprueba la conectividad del grafo
- Revisa en Network tab si hay errores

---

## 📈 Mejoras Futuras

- [ ] Modo "equilibrio" (múltiples criterios)
- [ ] Algoritmo A* para optimización adicional
- [ ] Caché de resultados
- [ ] Tests unitarios
- [ ] Visualización de tiempos en mapa
- [ ] Exportar resultados (CSV, PDF)
- [ ] Soporte para múltiples orígenes/destinos

---

## 📝 Licencia

Este proyecto es educativo.

---

## 👨‍💻 Autor

Equipo de desarrollo - Proyecto Grafos 2024

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisa `GUIA_PRUEBAS_PASO_A_PASO.md`
2. Revisa `ALGORITMOS_DIJKSTRA_UPDATE.md`
3. Abre Developer Tools (F12) y revisa Network/Console

---

## ✅ Estado

- ✅ Backend: Completo y funcional
- ✅ Frontend: Actualizado
- ✅ Pruebas: Interfaz dedicada
- ✅ Documentación: Completa
- ✅ Ejemplos: Incluidos
- ✅ Listo para producción

**¡Disfruta explorando diferentes rutas! 🧭**
