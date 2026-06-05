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

    startFlightAnimation({
      origenLat,
      origenLon,
      destinoLat,
      destinoLon,
      origenId,
      destinoId,
      aeronave,
      onProgress,
      onComplete,
      onInterrupted,
    }) {
      this.stopFlightAnimation();

      this._flightSegment = L.polyline(
        [
          [origenLat, origenLon],
          [destinoLat, destinoLon],
        ],
        {
          color: this.colors.trip,
          weight: 5,
          opacity: 0.9,
          dashArray: null,
        }
      ).addTo(this.routeLayer);

      const icon = L.divIcon({
        className: "aircraft-marker",
        html: '<div class="aircraft-marker-inner">&#9992;</div>',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      this._flightMarker = L.marker([origenLat, origenLon], {
        icon,
        interactive: false,
      }).addTo(this.routeLayer);

      this._flightOrigen = [origenLat, origenLon];
      this._flightDestino = [destinoLat, destinoLon];
      this._flightOrigenId = origenId;
      this._flightDestinoId = destinoId;
      this._flightAeronave = aeronave;
      this._flightOnProgress = onProgress;
      this._flightOnComplete = onComplete;
      this._flightOnInterrupted = onInterrupted;
      this._flightCancelled = false;
      this._flightCompleted = false;

      this._flightProgress = 0;
      this._flightTargetProgress = 0;
      this._flightStartTime = performance.now();

      const tick = () => {
        if (this._flightCancelled || this._flightCompleted) return;
        if (!this._flightMarker) return;

        const diff = this._flightTargetProgress - this._flightProgress;
        if (Math.abs(diff) > 0.0001) {
          const smoothing = 0.22;
          this._flightProgress += diff * smoothing;
          this.updateFlightPosition(this._flightProgress);
        }

        if (typeof this._flightOnProgress === "function") {
          this._flightOnProgress();
        }

        this._flightRaf = requestAnimationFrame(tick);
      };
      this._flightRaf = requestAnimationFrame(tick);
    }

    setFlightTargetProgress(progress) {
      if (this._flightTargetProgress === undefined) return;
      const p = Math.max(0, Math.min(1, Number(progress) || 0));
      if (p > this._flightTargetProgress) {
        this._flightTargetProgress = p;
      }
    }

    getFlightProgress() {
      return this._flightProgress;
    }

    updateFlightPosition(progress) {
      if (!this._flightMarker || !this._flightOrigen || !this._flightDestino) {
        return;
      }
      const p = Math.max(0, Math.min(1, progress));
      const [latO, lonO] = this._flightOrigen;
      const [latD, lonD] = this._flightDestino;
      const curLat = latO + (latD - latO) * p;
      const curLon = lonO + (lonD - lonO) * p;
      this._flightMarker.setLatLng([curLat, curLon]);
    }

    completeFlightAnimation() {
      this._flightCompleted = true;
      this._flightTargetProgress = 1;
      this._flightProgress = 1;
      if (this._flightRaf) {
        cancelAnimationFrame(this._flightRaf);
        this._flightRaf = null;
      }
      if (this._flightMarker) {
        const [latD, lonD] = this._flightDestino || [0, 0];
        this._flightMarker.setLatLng([latD, lonD]);
      }
      if (typeof this._flightOnComplete === "function") {
        const cb = this._flightOnComplete;
        this._flightOnComplete = null;
        cb();
      }
    }

    interruptFlightAnimation(onDone) {
      this._flightCancelled = true;
      if (this._flightRaf) {
        cancelAnimationFrame(this._flightRaf);
        this._flightRaf = null;
      }
      if (!this._flightMarker || !this._flightOrigen) {
        if (typeof onDone === "function") onDone();
        return;
      }

      // Phase 1: Show blocked route in red with flash
      if (this._flightSegment) {
        this._flightSegment.setStyle({
          color: "#ef4444",
          weight: 6,
          opacity: 1,
          dashArray: "12, 6",
        });
      }

      // Change marker to warning state
      if (this._flightMarker) {
        this._flightMarker.setIcon(L.divIcon({
          className: "aircraft-marker",
          html: '<div class="aircraft-marker-inner aircraft-marker-returning">&#9888;</div>',
          iconSize: [28, 28],
          iconAnchor: [14, 14],
        }));
      }

      // Phase 2: After a brief pause for the visual warning, animate back to origin
      const pauseDuration = 600;
      setTimeout(() => {
        if (!this._flightMarker || !this._flightOrigen) {
          if (typeof onDone === "function") onDone();
          return;
        }

        const startTime = performance.now();
        const duration = 1500;
        const startPos = this._flightMarker.getLatLng();
        const endPos = L.latLng(this._flightOrigen[0], this._flightOrigen[1]);

        // Add a return path polyline
        const returnLine = L.polyline(
          [[startPos.lat, startPos.lng], [endPos.lat, endPos.lng]],
          {
            color: "#f59e0b",
            weight: 3,
            opacity: 0.7,
            dashArray: "8, 8",
          }
        ).addTo(this.routeLayer);

        const step = (now) => {
          const t = Math.min(1, (now - startTime) / duration);
          const eased = t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
          const lat = startPos.lat + (endPos.lat - startPos.lat) * eased;
          const lng = startPos.lng + (endPos.lng - startPos.lng) * eased;
          if (this._flightMarker) {
            this._flightMarker.setLatLng([lat, lng]);
          }
          if (t < 1) {
            requestAnimationFrame(step);
          } else {
            // Cleanup
            if (returnLine) {
              this.routeLayer.removeLayer(returnLine);
            }
            if (this._flightSegment) {
              this.routeLayer.removeLayer(this._flightSegment);
              this._flightSegment = null;
            }
            if (this._flightMarker) {
              this.routeLayer.removeLayer(this._flightMarker);
              this._flightMarker = null;
            }
            this._flightOrigen = null;
            this._flightDestino = null;
            if (typeof onDone === "function") onDone();
          }
        };
        requestAnimationFrame(step);
      }, pauseDuration);
    }

    stopFlightAnimation() {
      this._flightCancelled = true;
      this._flightCompleted = true;
      if (this._flightRaf) {
        cancelAnimationFrame(this._flightRaf);
        this._flightRaf = null;
      }
      if (this._flightSegment) {
        this.routeLayer.removeLayer(this._flightSegment);
        this._flightSegment = null;
      }
      if (this._flightMarker) {
        this.routeLayer.removeLayer(this._flightMarker);
        this._flightMarker = null;
      }
      this._flightOrigen = null;
      this._flightDestino = null;
      this._flightOrigenId = null;
      this._flightDestinoId = null;
      this._flightAeronave = null;
      this._flightProgress = 0;
      this._flightTargetProgress = 0;
      this._flightOnProgress = null;
      this._flightOnComplete = null;
      this._flightOnInterrupted = null;
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

      // Mostrar tipo de aeronave y distancia en km sobre la arista
      if (edge.distanciaKm) {
        const midLat = (from.lat + to.lat) / 2;
        const midLon = (from.lon + to.lon) / 2;
        const aeronaves = (edge.aeronaves || []).join(", ") || "N/D";
        const label = L.marker([midLat, midLon], {
          icon: L.divIcon({
            className: "edge-label",
            html: `<div class="edge-label-aircraft">${aeronaves}</div><div class="edge-label-distance">${edge.distanciaKm} km</div>`,
            iconSize: [110, 34],
            iconAnchor: [55, 17],
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
