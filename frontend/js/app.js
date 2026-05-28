import { ApiClient, ApiError } from "./api_client.js";
import { MapRenderer } from "./map_renderer.js";
import { GraphStore } from "./graph_store.js";
import { GeocodeService } from "./services/geocode_service.js";
import { NodeFactory } from "./services/node_factory.js";
import { RouteFormController } from "./controllers/route_form_controller.js";
import { RouteSearchController } from "./controllers/route_search_controller.js";
import { StatusPanel } from "./ui/status_panel.js";

const fileInput = document.getElementById("file-input");
const statusEl = document.getElementById("status");
const errorsEl = document.getElementById("errors");
const statsEl = document.getElementById("stats");
const detailsEl = document.getElementById("details");
const mapEl = document.getElementById("map");
const routeForm = document.getElementById("route-form");
const searchForm = document.getElementById("search-form");

const api = new ApiClient();
const store = new GraphStore();
const renderer = new MapRenderer(mapEl, detailsEl, statsEl);
const statusPanel = new StatusPanel(statusEl, errorsEl);
const geocodeService = new GeocodeService(api);
const nodeFactory = new NodeFactory(geocodeService, { defaultFoodCost: 12 });
const routeController = new RouteFormController({
  formEl: routeForm,
  store,
  renderer,
  statusPanel,
  geocodeService,
  nodeFactory,
});
const searchController = new RouteSearchController({
  formEl: searchForm,
  store,
  renderer,
  statusPanel,
  api,
});

renderer.resize();
window.addEventListener("resize", () => renderer.resize());
routeController.init();
searchController.init();

fileInput.addEventListener("change", async () => {
  statusPanel.clearErrors();

  const file = fileInput.files[0];
  if (!file) {
    statusPanel.setStatus("Sin archivo.");
    renderer.clear();
    store.setGraph(null);
    return;
  }

  statusPanel.setStatus(`Cargando ${file.name}...`);

  try {
    const graph = await api.uploadGraph(file);
    store.setGraph(graph);
    renderer.setGraph(store.getGraph());
    statusPanel.setStatus("Grafo cargado.");
    routeController.onGraphLoaded();
    searchController.onGraphLoaded();
  } catch (error) {
    statusPanel.setStatus("Error al cargar el JSON.");
    const messages =
      error instanceof ApiError
        ? error.messages
        : [error.message || "Error desconocido."];
    statusPanel.showErrors(messages);
    renderer.clear();
  }
});
