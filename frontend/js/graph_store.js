export class GraphStore {
  constructor() {
    this.graph = null;
  }

  setGraph(graph) {
    if (!graph) {
      this.graph = null;
      return;
    }

    this.graph = {
      ...graph,
      nodos: [...(graph.nodos || [])],
      aristas: [...(graph.aristas || [])],
    };
  }

  hasGraph() {
    return Boolean(this.graph);
  }

  getGraph() {
    return this.graph;
  }

  findNodeByCountry(country) {
    if (!this.graph) {
      return null;
    }

    const key = normalizeName(country);
    return (
      this.graph.nodos.find((node) => normalizeName(node.pais) === key) ||
      this.graph.nodos.find((node) => normalizeName(node.nombre) === key) ||
      this.graph.nodos.find((node) => normalizeName(node.id) === key) ||
      null
    );
  }

  upsertNode(node) {
    if (!this.graph) {
      return;
    }

    const key = normalizeName(node.id);
    const index = this.graph.nodos.findIndex(
      (item) => normalizeName(item.id) === key
    );

    if (index >= 0) {
      this.graph.nodos[index] = node;
    } else {
      this.graph.nodos.push(node);
    }
  }

  addRoute(originId, destinationId, route) {
    if (!this.graph) {
      throw new Error("No hay un grafo cargado.");
    }

    const exists = this.graph.aristas.some(
      (edge) =>
        normalizeName(edge.origen) === normalizeName(originId) &&
        normalizeName(edge.destino) === normalizeName(destinationId)
    );

    if (exists) {
      throw new Error("La ruta ya existe.");
    }

    const newEdge = {
      origen: originId,
      destino: destinationId,
      distanciaKm: route.distanciaKm,
      aeronaves: route.aeronaves,
      costoBase: route.costoBase,
      estanciaMinima: route.estanciaMinima,
    };

    this.graph = {
      ...this.graph,
      nodos: [...this.graph.nodos],
      aristas: [...this.graph.aristas, newEdge],
    };

    return this.graph;
  }
}

function normalizeName(value) {
  return (value || "").trim().toLowerCase();
}
