export class MapRenderer {
  constructor(mapEl, detailsEl, statsEl) {
    this.mapEl = mapEl;
    this.detailsEl = detailsEl;
    this.statsEl = statsEl;
    this.graph = null;
    this.map = null;
    this.nodeLayer = null;
    this.edgeLayer = null;
    this.routeLayer = null;
    this.routeResult = null;
    this.colors = this._loadColors();
    this._initMap();
  }

  resize() {
    if (this.map) {
      this.map.invalidateSize();
    }
  }

  setGraph(graph) {
    this.graph = graph;
    this.routeResult = null;
    this._clearRoute();
    this._render();
    this._updateStats();
    this._setDetailsLines(["Selecciona un pais en el mapa para ver detalles."]);
  }

  clear() {
    this.graph = null;
    this.routeResult = null;
    this._clearLayers();
    this._clearRoute();
    this._updateStats();
    this._setDetailsLines(["Sin datos cargados."]);
  }

  setRouteResult(routeResult, options = {}) {
    this.routeResult = routeResult;
    this._clearRoute();

    if (!this.graph || !routeResult || !routeResult.encontrado) {
      return;
    }

    const label = options.label || "Ruta";
    const showDestinos = Boolean(options.showDestinos);

    const nodeById = new Map(
      this.graph.nodos.map((node) => [node.id, node])
    );

    const coords = [];
    (routeResult.camino || []).forEach((nodeId) => {
      const node = nodeById.get(nodeId);
      if (this._hasCoords(node)) {
        coords.push([node.lat, node.lon]);
      }
    });

    if (coords.length >= 2) {
      const line = L.polyline(coords, {
        color: options.tripPath ? this.colors.trip : this.colors.route,
        weight: options.tripPath ? 4 : 3,
        opacity: options.tripPath ? 0.8 : 0.9,
        dashArray: options.tripPath ? "10, 6" : null,
      });
      line.addTo(this.routeLayer);
    }

    const totalKm =
      typeof routeResult.totalKm === "number" ? routeResult.totalKm : null;
    const totalCosto =
      typeof routeResult.totalCosto === "number" ? routeResult.totalCosto : null;
    const camino = (routeResult.camino || []).join(" -> ");
    const lines = [
      `${label}:`,
      camino || "(sin ruta)",
    ];

    if (showDestinos) {
      const destinosCount = Math.max((routeResult.camino || []).length - 1, 0);
      lines.push(`Destinos visitados: ${destinosCount}`);
    }

    if (totalKm !== null) {
      lines.push(`Distancia total: ${totalKm.toFixed(2)} km`);
    }
    if (totalCosto !== null) {
      lines.push(`Costo total: ${totalCosto.toFixed(2)} USD`);
    }

    this._setDetailsLines(lines);
  }

  setTripPath(coords, camino) {
    this._clearRoute();
    if (coords.length >= 2) {
      const line = L.polyline(coords, {
        color: this.colors.trip,
        weight: 4,
        opacity: 0.8,
        dashArray: "10, 6",
      });
      line.addTo(this.routeLayer);
    }
    const pathStr = (camino || []).join(" -> ");
    this._setDetailsLines([
      "Viaje interactivo - Ruta:",
      pathStr,
    ]);
  }

  _initMap() {
    this.map = L.map(this.mapEl, {
      worldCopyJump: true,
      zoomControl: true,
      minZoom: 1,
      maxZoom: 6,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
    }).addTo(this.map);

    this.edgeLayer = L.layerGroup().addTo(this.map);
    this.routeLayer = L.layerGroup().addTo(this.map);
    this.nodeLayer = L.layerGroup().addTo(this.map);
    this.blockedLayer = L.layerGroup().addTo(this.map);
    this.labelLayer = L.layerGroup().addTo(this.map);
    this._labelsVisible = true;
    this.map.setView([15, 0], 2);
  }

  _getAircraftByNode() {
    const aircraftByNode = {};
    if (!this.graph) return aircraftByNode;
    for (const edge of this.graph.aristas || []) {
      if (!aircraftByNode[edge.origen]) {
        aircraftByNode[edge.origen] = new Set();
      }
      (edge.aeronaves || []).forEach((a) => aircraftByNode[edge.origen].add(a));
    }
    const result = {};
    for (const [key, val] of Object.entries(aircraftByNode)) {
      result[key] = Array.from(val).sort();
    }
    return result;
  }

  _render() {
    this._clearLayers();
    if (!this.graph) {
      return;
    }

    const nodeById = new Map(
      this.graph.nodos.map((node) => [node.id, node])
    );
    const aircraftByNode = this._getAircraftByNode();
    const bounds = L.latLngBounds();

    this.graph.aristas.forEach((edge) => {
      const from = nodeById.get(edge.origen);
      const to = nodeById.get(edge.destino);
      if (!this._hasCoords(from) || !this._hasCoords(to)) {
        return;
      }

      const line = L.polyline(
        [
          [from.lat, from.lon],
          [to.lat, to.lon],
        ],
        {
          color: this.colors.edge,
          weight: 2,
          opacity: 0.6,
        }
      );
      line.addTo(this.edgeLayer);

      // Mostrar distancia en km sobre la arista (en capa independiente)
      if (edge.distanciaKm) {
        const midLat = (from.lat + to.lat) / 2;
        const midLon = (from.lon + to.lon) / 2;
        const label = L.marker([midLat, midLon], {
          icon: L.divIcon({
            className: "edge-label",
            html: `${edge.distanciaKm} km`,
            iconSize: [80, 20],
            iconAnchor: [40, 10],
          }),
          interactive: false,
        });
        label.addTo(this.labelLayer);
      }
    });

    this.graph.nodos.forEach((node) => {
      if (!this._hasCoords(node)) {
        return;
      }

      const label = node.pais || node.nombre || node.id;
      const marker = L.circleMarker([node.lat, node.lon], {
        radius: 6,
        color: this.colors.nodeStroke,
        weight: 2,
        fillColor: node.esHub ? this.colors.hub : this.colors.node,
        fillOpacity: 0.9,
      });

      marker.bindTooltip(label, {
        direction: "top",
        offset: [0, -6],
      });

      marker.on("click", () => {
        this._setDetailsNode(node, aircraftByNode[node.id] || []);
      });

      marker.addTo(this.nodeLayer);
      bounds.extend([node.lat, node.lon]);
    });

    this._renderBlockedEdges();

    if (bounds.isValid()) {
      this.map.fitBounds(bounds, { padding: [40, 40] });
    }
  }

  setBlockedRoutes(blockedRoutes) {
    this._blockedRoutes = blockedRoutes || [];
    this._render();
  }

  _renderBlockedEdges() {
    this.blockedLayer.clearLayers();
    if (!this.graph || !this._blockedRoutes) return;

    const nodeById = new Map(this.graph.nodos.map((n) => [n.id, n]));
    const blockedSet = new Set(
      (this._blockedRoutes || []).map((b) => `${b.origen}|${b.destino}`)
    );

    this.graph.aristas.forEach((edge) => {
      const key = `${edge.origen}|${edge.destino}`;
      if (!blockedSet.has(key)) return;
      const from = nodeById.get(edge.origen);
      const to = nodeById.get(edge.destino);
      if (!this._hasCoords(from) || !this._hasCoords(to)) return;
      const line = L.polyline(
        [[from.lat, from.lon], [to.lat, to.lon]],
        {
          color: "#ef4444",
          weight: 4,
          opacity: 0.8,
          dashArray: "8, 4",
        }
      );
      line.addTo(this.blockedLayer);
    });
  }

  setLabelsVisible(visible) {
    this._labelsVisible = visible;
    if (this.labelLayer) {
      if (visible) {
        this.map.addLayer(this.labelLayer);
      } else {
        this.map.removeLayer(this.labelLayer);
      }
    }
  }

  _clearLayers() {
    if (this.edgeLayer) {
      this.edgeLayer.clearLayers();
    }
    if (this.nodeLayer) {
      this.nodeLayer.clearLayers();
    }
    if (this.blockedLayer) {
      this.blockedLayer.clearLayers();
    }
    if (this.labelLayer) {
      this.labelLayer.clearLayers();
    }
  }

  _clearRoute() {
    if (this.routeLayer) {
      this.routeLayer.clearLayers();
    }
  }

  _hasCoords(node) {
    return node && typeof node.lat === "number" && typeof node.lon === "number";
  }

  _updateStats() {
    const nodeCount = this.graph ? this.graph.nodos.length : 0;
    const edgeCount = this.graph ? this.graph.aristas.length : 0;

    this.statsEl.innerHTML = "";

    const nodeLine = document.createElement("div");
    nodeLine.textContent = `Paises: ${nodeCount}`;
    const edgeLine = document.createElement("div");
    edgeLine.textContent = `Rutas: ${edgeCount}`;

    this.statsEl.appendChild(nodeLine);
    this.statsEl.appendChild(edgeLine);
  }

  _setDetailsNode(node, aeronavesDisponibles = []) {
    const lines = [
      `${node.pais || node.nombre || node.id}`,
      `Capital: ${node.ciudad}`,
      `Zona horaria: ${node.zonaHoraria}`,
      `Hub: ${node.esHub ? "si" : "no"}`,
      `Alojamiento USD: ${node.costoAlojamiento}`,
      `Alimentacion USD: ${node.costoAlimentacion}`,
      `Actividades: ${(node.actividades || []).length}`,
      `Trabajos: ${(node.trabajos || []).length}`,
    ];
    if (aeronavesDisponibles.length > 0) {
      lines.push(`Aeronaves: ${aeronavesDisponibles.join(", ")}`);
    }

    this._setDetailsLines(lines);
  }

  _setDetailsLines(lines) {
    this.detailsEl.innerHTML = "";
    lines.forEach((line) => {
      const item = document.createElement("div");
      item.textContent = line;
      this.detailsEl.appendChild(item);
    });
  }

  _loadColors() {
    const styles = getComputedStyle(document.documentElement);
    const read = (name, fallback) => {
      const value = styles.getPropertyValue(name).trim();
      return value || fallback;
    };

    return {
      node: read("--node", "#1f2937"),
      hub: read("--hub", "#e76f51"),
      edge: read("--edge", "rgba(15, 23, 42, 0.3)"),
      nodeStroke: read("--label", "#0f172a"),
      route: read("--accent", "#0ea5a4"),
      trip: read("--trip", "#8b5cf6"),
    };
  }
}
