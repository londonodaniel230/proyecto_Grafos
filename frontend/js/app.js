import { ApiClient, ApiError } from "./api_client.js";
import { MapRenderer } from "./map_renderer.js";
import { GraphStore } from "./graph_store.js";
import { GeocodeService } from "./services/geocode_service.js";
import { NodeFactory } from "./services/node_factory.js";
import { RouteFormController } from "./controllers/route_form_controller.js";
import { RouteSearchController } from "./controllers/route_search_controller.js";
import { TripController } from "./controllers/trip_controller.js";
import { StatusPanel } from "./ui/status_panel.js";

// DOM refs
const fileInput = document.getElementById("file-input");
const statusEl = document.getElementById("status");
const errorsEl = document.getElementById("errors");
const statsEl = document.getElementById("stats");
const detailsEl = document.getElementById("details");
const mapEl = document.getElementById("map");
const routeForm = document.getElementById("route-form");
const searchForm = document.getElementById("search-form");
const menuToggle = document.getElementById("menu-toggle");
const sideMenu = document.getElementById("side-menu");
const menuOverlay = document.getElementById("menu-overlay");

// Services
const api = new ApiClient();
const store = new GraphStore();
const renderer = new MapRenderer(mapEl, detailsEl, statsEl);
const statusPanel = new StatusPanel(statusEl, errorsEl);
const geocodeService = new GeocodeService(api);
const nodeFactory = new NodeFactory(geocodeService, { defaultFoodCost: 12 });

// Controllers
const routeController = new RouteFormController({
  formEl: routeForm, store, renderer, statusPanel, geocodeService, nodeFactory,
});
const searchController = new RouteSearchController({
  formEl: searchForm, store, renderer, statusPanel, api,
});
const tripForm = document.getElementById("trip-form");
const tripController = new TripController({
  formEl: tripForm, store, renderer, api,
  onViewSwitch: switchToView,
});

// ===== Menu / View switching =====
function closeMenu() {
  menuToggle.classList.remove("open");
  sideMenu.classList.remove("open");
  menuOverlay.classList.add("hidden");
}

function toggleMenu() {
  menuToggle.classList.toggle("open");
  sideMenu.classList.toggle("open");
  menuOverlay.classList.toggle("hidden");
}

function switchToView(viewName) {
  document.querySelectorAll(".menu-item").forEach((mi) => mi.classList.remove("active"));
  const targetItem = document.querySelector(`.menu-item[data-view="${viewName}"]`);
  if (targetItem) targetItem.classList.add("active");
  document.querySelectorAll(".view-panel").forEach((vp) => vp.classList.remove("active"));
  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) targetPanel.classList.add("active");
}

menuToggle.addEventListener("click", toggleMenu);
menuOverlay.addEventListener("click", closeMenu);

document.querySelectorAll(".menu-item").forEach((item) => {
  item.addEventListener("click", () => {
    closeMenu();
    const view = item.dataset.view;
    document.querySelectorAll(".menu-item").forEach((mi) => mi.classList.remove("active"));
    item.classList.add("active");
    document.querySelectorAll(".view-panel").forEach((vp) => vp.classList.remove("active"));
    const target = document.getElementById(`view-${view}`);
    if (target) target.classList.add("active");
  });
});

// ===== Toggle labels =====
const toggleLabels = document.getElementById("toggle-labels");
if (toggleLabels) {
  toggleLabels.addEventListener("click", () => {
    const visible = toggleLabels.classList.toggle("active");
    toggleLabels.textContent = visible ? "Distancias" : "Mostrar distancias";
    renderer.setLabelsVisible(visible);
  });
  // Default ON
  toggleLabels.classList.add("active");
}

// ===== Init =====
renderer.resize();
window.addEventListener("resize", () => renderer.resize());
routeController.init();
searchController.init();
tripController.init();

// ===== Graph loaded helper =====
function afterGraphLoaded() {
  // Refresh datalists for all forms
  if (!store.hasGraph()) return;
  const nodes = store.getGraph().nodos || [];

  const datalistIds = [
    "search-origin-suggestions", "search-destination-suggestions",
    "plan-origin-suggestions",
    "trip-origin-suggestions",
    "origin-suggestions", "destination-suggestions",
    "block-origin-suggestions", "block-destino-suggestions",
  ];

  datalistIds.forEach((id) => {
    const dl = document.getElementById(id);
    if (!dl) return;
    dl.innerHTML = "";
    nodes.forEach((n) => {
      const opt = document.createElement("option");
      opt.value = `${n.pais} | ${n.ciudad} | ${n.nombre}`;
      dl.appendChild(opt);
    });
  });

  // Also fill IATA suggestions for block form
  const blockDatalists = ["block-origin-suggestions", "block-destino-suggestions"];
  blockDatalists.forEach((id) => {
    const dl = document.getElementById(id);
    if (!dl) return;
    dl.innerHTML = "";
    nodes.forEach((n) => {
      const opt = document.createElement("option");
      opt.value = n.id;
      dl.appendChild(opt);
    });
  });

  // Refresh blocked routes display
  if (document.getElementById("blocked-list")) {
    api.getBlockedRoutes().then((blocked) => {
      const el = document.getElementById("blocked-list");
      if (blocked.length === 0) {
        el.textContent = "Sin rutas bloqueadas.";
      } else {
        el.innerHTML = blocked.map(
          (b) => `<div style="color:var(--danger)">${b.origen} &rarr; ${b.destino}</div>`
        ).join("");
      }
      renderer.setBlockedRoutes(blocked);
    }).catch(() => {});
  }
}

// ===== File upload =====
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
    tripController.onGraphLoaded();
    afterGraphLoaded();
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

// ===== Plan form =====
const planForm = document.getElementById("plan-form");
if (planForm) {
  const planOrigin = document.getElementById("plan-origin");
  const planBudget = document.getElementById("plan-budget");
  const planTime = document.getElementById("plan-time");
  const planResults = document.getElementById("plan-results");
  const planResultBudget = document.getElementById("plan-result-budget");
  const planResultTime = document.getElementById("plan-result-time");

  planForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!store.hasGraph()) { alert("Carga un grafo primero."); return; }
    const originVal = (planOrigin.value || "").trim();
    if (!originVal) { alert("Selecciona origen."); return; }
    const gn = store.getGraph().nodos || [];
    const originNode = gn.find(
      (n) => `${n.pais} | ${n.ciudad} | ${n.nombre}` === originVal
    );
    if (!originNode) { alert("Origen no encontrado."); return; }
    const budget = parseFloat(planBudget.value) || 0;
    const timeH = parseFloat(planTime.value) || 0;
    if (budget <= 0 || timeH <= 0) { alert("Presupuesto y tiempo deben ser positivos."); return; }

    try {
      const result = await api.autoPlan({
        graph: store.getGraph(),
        originId: originNode.id,
        budget,
        time: timeH,
      });
      planResults.classList.remove("hidden");

      const renderAlt = (data, label, el) => {
        if (!data.encontrado) {
          el.innerHTML = `<span style="color:var(--danger)">${data.error || "Sin ruta"}</span>`;
          return;
        }
        el.innerHTML = `
          Ruta: ${(data.camino || []).join(" &rarr; ")}<br/>
          Destinos: ${(data.camino || []).length - 1}<br/>
          Distancia: ${(data.totalKm || 0).toFixed(0)} km<br/>
          Costo: $${(data.totalCosto || 0).toFixed(2)}
        `;
      };

      renderAlt(result.porPresupuesto, "Por presupuesto", planResultBudget);
      renderAlt(result.porTiempo, "Por tiempo", planResultTime);

      const best = result.porPresupuesto.encontrado ? result.porPresupuesto : result.porTiempo;
      if (best.encontrado) {
        renderer.setRouteResult(best, { label: "Plan automatico", showDestinos: true });
      }
    } catch (err) {
      alert(err.message || "Error al planificar.");
    }
  });
}

// ===== Block form =====
const blockForm = document.getElementById("block-form");
if (blockForm) {
  const blockOrigin = document.getElementById("block-origin");
  const blockDestino = document.getElementById("block-destino");
  const unblockBtn = document.getElementById("unblock-btn");
  const blockedList = document.getElementById("blocked-list");

  const refreshBlocked = async () => {
    try {
      const blocked = await api.getBlockedRoutes();
      if (blocked.length === 0) {
        blockedList.textContent = "Sin rutas bloqueadas.";
      } else {
        blockedList.innerHTML = blocked.map(
          (b) => `<div style="color:var(--danger)">${b.origen} &rarr; ${b.destino}</div>`
        ).join("");
      }
      renderer.setBlockedRoutes(blocked);
    } catch (e) { /* ignore */ }
  };

  blockForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!store.hasGraph()) { alert("Carga un grafo primero."); return; }
    const graph = store.getGraph();
    const payload = {
      graph,
      origen: (blockOrigin.value || "").trim().toUpperCase(),
      destino: (blockDestino.value || "").trim().toUpperCase(),
    };
    if (!payload.origen || !payload.destino) { alert("Origen y destino requeridos."); return; }
    try {
      await api.blockRoute(payload);
      await refreshBlocked();
      tripController.interruptIfRouteMatches(payload.origen, payload.destino);
    } catch (err) {
      alert(err.message || "Error al bloquear.");
    }
  });

  unblockBtn.addEventListener("click", async () => {
    if (!store.hasGraph()) { alert("Carga un grafo primero."); return; }
    const graph = store.getGraph();
    const payload = {
      graph,
      origen: (blockOrigin.value || "").trim().toUpperCase(),
      destino: (blockDestino.value || "").trim().toUpperCase(),
    };
    if (!payload.origen || !payload.destino) { alert("Origen y destino requeridos."); return; }
    try {
      await api.unblockRoute(payload);
      await refreshBlocked();
    } catch (err) {
      alert(err.message || "Error al desbloquear.");
    }
  });

  window._refreshBlocked = refreshBlocked;
}

// Also refresh blocked when graph is loaded via afterGraphLoaded
