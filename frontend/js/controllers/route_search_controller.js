export class RouteSearchController {
  constructor({ formEl, store, renderer, statusPanel, api }) {
    this.formEl = formEl;
    this.store = store;
    this.renderer = renderer;
    this.statusPanel = statusPanel;
    this.api = api;

    this.modeSelect = null;
    this.originInput = null;
    this.destinationInput = null;
    this.originSuggestions = null;
    this.destinationSuggestions = null;
    this.budgetInput = null;
    this.aircraftInput = null;
    this.timeInput = null;
    this.secondarySelect = null;
    this.lodgingInput = null;
    this.foodInput = null;
    this.workInput = null;
  }

  init() {
    if (!this.formEl) {
      return;
    }

    this._cacheElements();
    this._bindEvents();
    this._updateFormState();
  }

  onGraphLoaded() {
    this._refreshSuggestions();
    this._updateFormState();
  }

  _cacheElements() {
    this.modeSelect = this.formEl.querySelector("#search-mode");
    this.originInput = this.formEl.querySelector("#search-origin-country");
    this.destinationInput = this.formEl.querySelector("#search-destination-country");
    this.originSuggestions = this.formEl.querySelector("#search-origin-suggestions");
    this.destinationSuggestions = this.formEl.querySelector(
      "#search-destination-suggestions"
    );
    this.budgetInput = this.formEl.querySelector("#search-budget");
    this.aircraftInput = this.formEl.querySelector("#search-aircraft");
    this.timeInput = this.formEl.querySelector("#search-time");
    this.secondarySelect = this.formEl.querySelector("#search-secondary");
    this.lodgingInput = this.formEl.querySelector("#search-lodging");
    this.foodInput = this.formEl.querySelector("#search-food");
    this.workInput = this.formEl.querySelector("#search-work");
  }

  _bindEvents() {
    this.formEl.addEventListener("submit", (event) => {
      this._onSubmit(event);
    });
  }

  _updateFormState() {
    const submitBtn = this.formEl.querySelector("button[type='submit']");
    if (submitBtn) {
      submitBtn.disabled = !this.store.hasGraph();
    }
  }

  _refreshSuggestions() {
    if (!this.store.hasGraph()) {
      return;
    }

    const nodes = this.store.getGraph().nodos || [];
    const fill = (datalist) => {
      if (!datalist) {
        return;
      }
      datalist.innerHTML = "";
      nodes.forEach((node) => {
        const option = document.createElement("option");
        option.value = `${node.pais} | ${node.ciudad} | ${node.nombre}`;
        datalist.appendChild(option);
      });
    };

    fill(this.originSuggestions);
    fill(this.destinationSuggestions);
  }

  _getModoLabel(modo) {
    const labels = {
      distancia: "Distancia mínima",
      costo: "Costo mínimo",
      tiempo: "Tiempo mínimo",
      destinos: "Mayor cantidad de destinos",
    };
    return labels[modo] || "Ruta";
  }

  async _onSubmit(event) {
    event.preventDefault();
    this.statusPanel.clearErrors();
    this.renderer.setRouteResult({ encontrado: false });

    if (!this.store.hasGraph()) {
      this.statusPanel.showErrors(["Debes cargar un grafo primero."]);
      return;
    }

    const originValue = (this.originInput.value || "").trim();
    const destinationValue = (this.destinationInput.value || "").trim();

    if (!originValue || !destinationValue) {
      this.statusPanel.showErrors(["Completa pais origen y destino."]);
      return;
    }

    const graphNodes = this.store.getGraph().nodos || [];
    const originNodes = [findNodeByDisplay(graphNodes, originValue)].filter(Boolean);
    const destinationNodes = [findNodeByDisplay(graphNodes, destinationValue)].filter(Boolean);

    if (!originNodes.length || !destinationNodes.length) {
      this.statusPanel.showErrors(["Origen o destino no encontrados."]);
      return;
    }

    const budgetRaw = this.budgetInput ? this.budgetInput.value : "";
    const presupuestoTotal = budgetRaw ? Number(budgetRaw) : null;
    if (budgetRaw && !Number.isFinite(presupuestoTotal)) {
      this.statusPanel.showErrors(["Presupuesto invalido."]);
      return;
    }

    const aeronaves = parseAircraftList(
      this.aircraftInput ? this.aircraftInput.value : ""
    );

    const timeRaw = this.timeInput ? this.timeInput.value : "";
    const tiempoMaximo = timeRaw ? Number(timeRaw) : null;
    if (timeRaw && !Number.isFinite(tiempoMaximo)) {
      this.statusPanel.showErrors(["Tiempo maximo invalido."]);
      return;
    }

    const excluirSecundarios =
      this.secondarySelect ? this.secondarySelect.value === "true" : false;

    const inicioIds = uniqueIds(originNodes);
    const destinoIds = uniqueIds(destinationNodes);

    const modo = (this.modeSelect ? this.modeSelect.value : "costo") || "costo";
    const modoLabel = this._getModoLabel(modo);

    const payload = {
      graph: this.store.getGraph(),
      inicioId: inicioIds[0],
      destinoId: destinoIds[0],
      inicioIds,
      destinoIds,
      modo: modo,
      presupuestoTotal: presupuestoTotal,
      tiempoMaximo: tiempoMaximo,
      excluirSecundarios: excluirSecundarios,
      opciones: {
        aeronaves,
        incluirAlojamiento: this.lodgingInput ? this.lodgingInput.checked : true,
        incluirAlimentacion: this.foodInput ? this.foodInput.checked : true,
        incluirTrabajo: this.workInput ? this.workInput.checked : true,
      },
    };

    try {
      const result = await this.api.optimizeRoute(payload);
      if (!result.encontrado) {
        this.statusPanel.showErrors([result.error || "Ruta no encontrada."]);
        return;
      }

      this.renderer.setRouteResult(result, {
        label: `Ruta por ${modoLabel}`,
        showDestinos: modo === "destinos",
      });
      this.statusPanel.setStatus(`Ruta por ${modoLabel} calculada.`);
    } catch (error) {
      const messages =
        error && error.messages ? error.messages : [error.message || "Error."];
      this.statusPanel.showErrors(messages);
    }
  }
}

function parseAircraftList(value) {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function uniqueIds(nodes) {
  const seen = new Set();
  const ids = [];
  nodes.forEach((node) => {
    if (node && node.id && !seen.has(node.id)) {
      seen.add(node.id);
      ids.push(node.id);
    }
  });
  return ids;
}


function findNodeByDisplay(nodes, value) {
 return nodes.find(node => `${node.pais} | ${node.ciudad} | ${node.nombre}` === value);
}
