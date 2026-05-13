export class MapRenderer {
  constructor(mapEl, detailsEl, statsEl) {
    this.mapEl = mapEl;
    this.detailsEl = detailsEl;
    this.statsEl = statsEl;
    this.graph = null;
    this.map = null;
    this.nodeLayer = null;
    this.edgeLayer = null;
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
    this._render();
    this._updateStats();
    this._setDetailsLines(["Selecciona un pais en el mapa para ver detalles."]);
  }

  clear() {
    this.graph = null;
    this._clearLayers();
    this._updateStats();
    this._setDetailsLines(["Sin datos cargados."]);
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
    this.nodeLayer = L.layerGroup().addTo(this.map);
    this.map.setView([15, 0], 2);
  }

  _render() {
    this._clearLayers();
    if (!this.graph) {
      return;
    }

    const nodeById = new Map(
      this.graph.nodos.map((node) => [node.id, node])
    );
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
        this._setDetailsNode(node);
      });

      marker.addTo(this.nodeLayer);
      bounds.extend([node.lat, node.lon]);
    });

    if (bounds.isValid()) {
      this.map.fitBounds(bounds, { padding: [40, 40] });
    }
  }

  _clearLayers() {
    if (this.edgeLayer) {
      this.edgeLayer.clearLayers();
    }
    if (this.nodeLayer) {
      this.nodeLayer.clearLayers();
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

  _setDetailsNode(node) {
    const lines = [
      `${node.pais || node.nombre || node.id}`,
      `Capital: ${node.ciudad}`,
      `Zona horaria: ${node.zonaHoraria}`,
      `Hub: ${node.esHub ? "si" : "no"}`,
      `Alojamiento USD: ${node.costoAlojamiento}`,
      `Alimentacion USD: ${node.costoAlimentacion}`,
      `Actividades: ${node.actividades.length}`,
      `Trabajos: ${node.trabajos.length}`,
    ];

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
    };
  }
}
