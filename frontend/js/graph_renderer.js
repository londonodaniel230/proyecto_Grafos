import { getLayoutForMode, LayoutModes } from "./graph_layout.js";

export class GraphRenderer {
  constructor(canvas, detailsEl, statsEl, layoutMode = LayoutModes.MAP) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.detailsEl = detailsEl;
    this.statsEl = statsEl;
    this.graph = null;
    this.positions = new Map();
    this.selectedNodeId = null;
    this.colors = this._loadColors();
    this.width = 0;
    this.height = 0;
    this.layoutMode = layoutMode;
    this.layoutFn = getLayoutForMode(layoutMode);
    this._bindEvents();
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const width = Math.max(1, rect.width);
    const height = Math.max(1, rect.height);

    this.canvas.width = width * dpr;
    this.canvas.height = height * dpr;
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    this.width = width;
    this.height = height;

    if (this.graph) {
      this.positions = this._computeLayout();
    }

    this.draw();
  }

  setGraph(graph) {
    this.graph = graph;
    this.selectedNodeId = null;
    this.positions = this._computeLayout();
    this._updateStats();
    this._setDetailsLines(["Selecciona un nodo en el grafo para ver detalles."]);
    this.draw();
  }

  setLayoutMode(layoutMode) {
    this.layoutMode = layoutMode;
    this.layoutFn = getLayoutForMode(layoutMode);
    if (this.graph) {
      this.positions = this._computeLayout();
      this.draw();
    }
  }

  clear() {
    this.graph = null;
    this.selectedNodeId = null;
    this.positions = new Map();
    this._updateStats();
    this._setDetailsLines(["Sin datos cargados."]);
    this.draw();
  }

  draw() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.width, this.height);

    if (!this.graph) {
      this._drawEmptyState();
      return;
    }

    this._drawEdges();
    this._drawNodes();
  }

  _computeLayout() {
    if (!this.graph) {
      return new Map();
    }

    return this.layoutFn(this.graph.nodos, this.width, this.height);
  }

  _bindEvents() {
    this.canvas.addEventListener("click", (event) => {
      if (!this.graph) {
        return;
      }

      const point = this._getPoint(event);
      const node = this._findNodeAt(point.x, point.y);

      if (node) {
        this.selectedNodeId = node.id;
        this._setDetailsNode(node);
      } else {
        this.selectedNodeId = null;
        this._setDetailsLines(["Selecciona un nodo en el grafo para ver detalles."]);
      }

      this.draw();
    });
  }

  _getPoint(event) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  }

  _findNodeAt(x, y) {
    const radius = 12;
    for (const node of this.graph.nodos) {
      const pos = this.positions.get(node.id);
      if (!pos) {
        continue;
      }

      const dx = x - pos.x;
      const dy = y - pos.y;
      if (Math.sqrt(dx * dx + dy * dy) <= radius) {
        return node;
      }
    }

    return null;
  }

  _drawEdges() {
    const ctx = this.ctx;
    ctx.save();
    ctx.strokeStyle = this.colors.edge;
    ctx.lineWidth = 1.4;

    for (const edge of this.graph.aristas) {
      const from = this.positions.get(edge.origen);
      const to = this.positions.get(edge.destino);
      if (!from || !to) {
        continue;
      }

      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      ctx.lineTo(to.x, to.y);
      ctx.stroke();
    }

    ctx.restore();
  }

  _drawNodes() {
    const ctx = this.ctx;
    const radius = 10;

    ctx.save();
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.font = "12px 'Space Grotesk', sans-serif";

    for (const node of this.graph.nodos) {
      const pos = this.positions.get(node.id);
      if (!pos) {
        continue;
      }

      const isSelected = node.id === this.selectedNodeId;
      const fill = isSelected
        ? this.colors.accent
        : node.esHub
        ? this.colors.hub
        : this.colors.node;

      ctx.beginPath();
      ctx.fillStyle = fill;
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = this.colors.accentOutline;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, radius + 4, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = this.colors.label;
      ctx.fillText(node.id, pos.x + radius + 6, pos.y);
    }

    ctx.restore();
  }

  _drawEmptyState() {
    const ctx = this.ctx;
    ctx.save();
    ctx.fillStyle = this.colors.empty;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "14px 'Space Grotesk', sans-serif";
    ctx.fillText("Carga un JSON para ver el grafo.", this.width / 2, this.height / 2);
    ctx.restore();
  }

  _updateStats() {
    const nodeCount = this.graph ? this.graph.nodos.length : 0;
    const edgeCount = this.graph ? this.graph.aristas.length : 0;

    this.statsEl.innerHTML = "";

    const nodeLine = document.createElement("div");
    nodeLine.textContent = `Nodos: ${nodeCount}`;
    const edgeLine = document.createElement("div");
    edgeLine.textContent = `Aristas: ${edgeCount}`;

    this.statsEl.appendChild(nodeLine);
    this.statsEl.appendChild(edgeLine);
  }

  _setDetailsNode(node) {
    const lines = [
      `${node.id} - ${node.nombre}`,
      `Ciudad: ${node.ciudad}, ${node.pais}`,
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
      edge: read("--edge", "rgba(15, 23, 42, 0.2)"),
      label: read("--label", "#0f172a"),
      accent: read("--accent", "#0ea5a4"),
      accentOutline: read("--accent-2", "#f59e0b"),
      empty: read("--muted", "#6b7280"),
    };
  }
}
