export class RouteFormController {
  constructor({
    formEl,
    store,
    renderer,
    statusPanel,
    geocodeService,
    nodeFactory,
  }) {
    this.formEl = formEl;
    this.store = store;
    this.renderer = renderer;
    this.statusPanel = statusPanel;
    this.geocodeService = geocodeService;
    this.nodeFactory = nodeFactory;

    this.originInput = null;
    this.destinationInput = null;
    this.originSuggestions = null;
    this.destinationSuggestions = null;
    this.routeDistanceInput = null;
    this.routeCostInput = null;
    this.routeStayInput = null;
    this.routeAircraftInput = null;
    this.originHubSelect = null;
    this.originLodgingInput = null;
    this.destinationHubSelect = null;
    this.destinationLodgingInput = null;
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
    this._updateDistance();
  }

  _cacheElements() {
    this.originInput = this.formEl.querySelector("#origin-country");
    this.destinationInput = this.formEl.querySelector("#destination-country");
    this.originSuggestions = this.formEl.querySelector("#origin-suggestions");
    this.destinationSuggestions = this.formEl.querySelector(
      "#destination-suggestions"
    );
    this.routeDistanceInput = this.formEl.querySelector("#route-distance");
    this.routeCostInput = this.formEl.querySelector("#route-cost");
    this.routeStayInput = this.formEl.querySelector("#route-stay");
    this.routeAircraftInput = this.formEl.querySelector("#route-aircraft");
    this.originHubSelect = this.formEl.querySelector("#origin-hub");
    this.originLodgingInput = this.formEl.querySelector("#origin-lodging");
    this.destinationHubSelect = this.formEl.querySelector("#destination-hub");
    this.destinationLodgingInput = this.formEl.querySelector(
      "#destination-lodging"
    );
  }

  _bindEvents() {
    this.formEl.addEventListener("submit", (event) => {
      this._onSubmit(event);
    });

    if (this.originInput) {
      this.originInput.addEventListener("change", () => this._updateDistance());
    }
    if (this.destinationInput) {
      this.destinationInput.addEventListener("change", () => this._updateDistance());
    }
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
        option.value = node.pais || node.nombre || node.id;
        datalist.appendChild(option);
      });
    };

    fill(this.originSuggestions);
    fill(this.destinationSuggestions);
  }

  async _onSubmit(event) {
    event.preventDefault();
    this.statusPanel.clearErrors();

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

    try {
      const origin = await this._ensureNode(originValue, "origin");
      const destination = await this._ensureNode(destinationValue, "destination");

      const distanciaKm = this._readDistance(origin, destination);
      const costoBase = toNumber(this.routeCostInput.value, 0);
      const estanciaMinima = toNumber(this.routeStayInput.value, 0);
      const aeronaves = parseAircraftList(this.routeAircraftInput.value);

      this.store.addRoute(origin.id, destination.id, {
        distanciaKm,
        costoBase,
        estanciaMinima,
        aeronaves,
      });

      this.renderer.setGraph(this.store.getGraph());
      this.statusPanel.setStatus("Ruta agregada.");
      this._refreshSuggestions();
      this._updateDistance();
    } catch (error) {
      const message = error && error.message ? error.message : "Error al agregar.";
      this.statusPanel.showErrors([message]);
    }
  }

  async _ensureNode(query, prefix) {
    const existing = this.store.findNodeByCountry(query);
    if (existing) {
      return existing;
    }

    const overrides = this._readNodeOverrides(query, prefix);
    const node = await this.nodeFactory.createFromQuery(query, overrides);
    this.store.upsertNode(node);
    return node;
  }

  _readNodeOverrides(query, prefix) {
    const isOrigin = prefix === "origin";
    const hubSelect = isOrigin ? this.originHubSelect : this.destinationHubSelect;
    const lodgingInput = isOrigin
      ? this.originLodgingInput
      : this.destinationLodgingInput;

    return {
      id: query,
      nombre: query,
      pais: query,
      esHub: hubSelect ? hubSelect.value === "true" : false,
      costoAlojamiento: toNumber(lodgingInput ? lodgingInput.value : 0, 0),
    };
  }

  _updateDistance() {
    if (!this.routeDistanceInput || !this.store.hasGraph()) {
      return;
    }

    const origin = this.store.findNodeByCountry(this.originInput.value || "");
    const destination = this.store.findNodeByCountry(
      this.destinationInput.value || ""
    );

    if (!origin || !destination || !hasCoords(origin) || !hasCoords(destination)) {
      return;
    }

    const distancia = computeDistanceKm(origin, destination);
    this.routeDistanceInput.value = Math.round(distancia).toString();
  }

  _readDistance(origin, destination) {
    if (this.routeDistanceInput && this.routeDistanceInput.value) {
      return toNumber(this.routeDistanceInput.value, 0);
    }

    if (origin && destination && hasCoords(origin) && hasCoords(destination)) {
      return computeDistanceKm(origin, destination);
    }

    return 0;
  }
}

function parseAircraftList(value) {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toNumber(value, fallback) {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

function hasCoords(node) {
  return node && typeof node.lat === "number" && typeof node.lon === "number";
}

function computeDistanceKm(origin, destination) {
  const R = 6371;
  const lat1 = (origin.lat * Math.PI) / 180;
  const lat2 = (destination.lat * Math.PI) / 180;
  const deltaLat = lat2 - lat1;
  const deltaLon = ((destination.lon - origin.lon) * Math.PI) / 180;

  const a =
    Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) * Math.sin(deltaLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c;
}
