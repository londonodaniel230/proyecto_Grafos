export class TripController {
  constructor({ formEl, store, renderer, api }) {
    this.formEl = formEl;
    this.store = store;
    this.renderer = renderer;
    this.api = api;

    this.originInput = null;
    this.budgetInput = null;
    this.originSuggestions = null;
    this.panel = null;
    this.statusEl = null;
    this.actionsEl = null;
    this.reportEl = null;

    this.sessionId = null;
    this.currentStep = null;

    this._flightTickHandle = null;
    this._flightPollHandle = null;
    this._flightInProgress = false;
  }

  init() {
    if (!this.formEl) {
      return;
    }

    this._cacheElements();
    this._bindEvents();
  }

  onGraphLoaded() {
    this._refreshSuggestions();
  }

  _cacheElements() {
    this.originInput = this.formEl.querySelector("#trip-origin");
    this.budgetInput = this.formEl.querySelector("#trip-budget");
    this.originSuggestions = this.formEl.querySelector("#trip-origin-suggestions");
    this.panel = document.getElementById("trip-panel");
    this.statusEl = document.getElementById("trip-status");
    this.actionsEl = document.getElementById("trip-actions");
    this.reportEl = document.getElementById("trip-report");
  }

  _bindEvents() {
    this.formEl.addEventListener("submit", (event) => {
      this._onStartTrip(event);
    });
  }

  _refreshSuggestions() {
    if (!this.store.hasGraph() || !this.originSuggestions) {
      return;
    }

    const nodes = this.store.getGraph().nodos || [];
    this.originSuggestions.innerHTML = "";
    nodes.forEach((node) => {
      const option = document.createElement("option");
      option.value = `${node.pais} | ${node.ciudad} | ${node.nombre}`;
      this.originSuggestions.appendChild(option);
    });
  }

  async _onStartTrip(event) {
    event.preventDefault();

    if (!this.store.hasGraph()) {
      alert("Debes cargar un grafo primero.");
      return;
    }

    const originValue = (this.originInput.value || "").trim();
    if (!originValue) {
      alert("Selecciona un pais de origen.");
      return;
    }

    const graphNodes = this.store.getGraph().nodos || [];
    const originNode = graphNodes.find(
      (n) => `${n.pais} | ${n.ciudad} | ${n.nombre}` === originValue
    );
    if (!originNode) {
      alert("Origen no encontrado en el grafo.");
      return;
    }

    const budgetRaw = this.budgetInput ? this.budgetInput.value : "1000";
    const initialBudget = Number(budgetRaw);
    if (!Number.isFinite(initialBudget) || initialBudget <= 0) {
      alert("Presupuesto invalido.");
      return;
    }

    const payload = {
      graph: this.store.getGraph(),
      originId: originNode.id,
      initialBudget: initialBudget,
    };

    try {
      const data = await this.api.startTrip(payload);
      this.sessionId = data.sessionId;
      this.currentStep = data.step;
      this.panel.classList.remove("hidden");
      this._renderStep();
    } catch (error) {
      const messages =
        error && error.messages
          ? error.messages
          : [error.message || "Error al iniciar viaje."];
      alert(messages.join("\n"));
    }
  }

  async _doAction(actionPayload) {
    if (!this.sessionId) {
      return;
    }

    const payload = {
      sessionId: this.sessionId,
      ...actionPayload,
    };

    try {
      const data = await this.api.tripAction(payload);
      if (data.report) {
        this._renderReport(data.report);
        return;
      }
      this.currentStep = data.step;
      if (data.error) {
        this._renderStep(data.error);
      } else {
        this._renderStep();
      }
    } catch (error) {
      const messages =
        error && error.messages
          ? error.messages
          : [error.message || "Error en accion."];
      this._renderStep(messages.join("\n"));
    }
  }

  _renderStep(errorMsg) {
    const step = this.currentStep;
    if (!step) {
      return;
    }

    const lines = [
      `Ubicacion: ${step.nodeNombre} (${step.nodeCiudad}, ${step.nodePais})`,
      `Presupuesto: $${step.presupuestoActual.toFixed(2)}`,
      `Gastado: $${step.totalGastado.toFixed(2)} | Ganado: $${step.totalGanado.toFixed(2)}`,
      `Tiempo transcurrido: ${step.tiempoTranscurridoHoras.toFixed(1)} h`,
      `Destinos visitados: ${step.destinosVisitados.length}`,
    ];

    this.statusEl.innerHTML = "";
    lines.forEach((line) => {
      const div = document.createElement("div");
      div.textContent = line;
      this.statusEl.appendChild(div);
    });

    if (errorMsg) {
      const errDiv = document.createElement("div");
      errDiv.className = "trip-error";
      errDiv.textContent = errorMsg;
      this.statusEl.appendChild(errDiv);
    }

    // Renderizar acciones disponibles
    this.actionsEl.innerHTML = "";
    this._renderMandatoryActions(step);
    this._renderActivityActions(step);
    this._renderJobActions(step);
    this._renderFlightActions(step);
    this._renderEndAction(step);
  }

  _renderMandatoryActions(step) {
    if (step.necesitaAlojamiento) {
      const btn = document.createElement("button");
      btn.className = "trip-action mandatory";
      btn.textContent = `Alojarse ($${step.costoAlojamiento.toFixed(2)}, 8h)`;
      btn.addEventListener("click", () => this._doAction({ action: "alojamiento" }));
      this.actionsEl.appendChild(btn);
    }

    if (step.necesitaAlimentacion) {
      const btn = document.createElement("button");
      btn.className = "trip-action mandatory";
      btn.textContent = `Alimentarse ($${step.costoAlimentacion.toFixed(2)}, 1h)`;
      btn.addEventListener("click", () => this._doAction({ action: "alimentacion" }));
      this.actionsEl.appendChild(btn);
    }
  }

  _renderActivityActions(step) {
    const actividades = step.actividadesOpcionales || [];
    if (actividades.length === 0) {
      return;
    }

    const header = document.createElement("div");
    header.className = "trip-section-label";
    header.textContent = "Actividades opcionales:";
    this.actionsEl.appendChild(header);

    actividades.forEach((act, idx) => {
      const duracion = (act.duracionMin / 60).toFixed(1);
      const btn = document.createElement("button");
      btn.className = "trip-action optional";
      btn.textContent = `${act.nombre} ($${act.costoUSD.toFixed(2)}, ${duracion}h)`;
      btn.addEventListener("click", () =>
        this._doAction({ action: "actividad", activityIndex: idx })
      );
      this.actionsEl.appendChild(btn);
    });
  }

  _renderJobActions(step) {
    if (!step.puedeTrabajar) {
      return;
    }

    const trabajos = step.trabajosDisponibles || [];
    if (trabajos.length === 0) {
      return;
    }

    const header = document.createElement("div");
    header.className = "trip-section-label warning";
    header.textContent = `Presupuesto bajo (${step.presupuestoActual.toFixed(2)} < 35%). Trabajos disponibles:`;
    this.actionsEl.appendChild(header);

    trabajos.forEach((job, idx) => {
      const btn = document.createElement("button");
      btn.className = "trip-action job";
      btn.textContent = `${job.nombre} - $${job.tarifaHora}/h (max ${job.maxHoras}h)`;
      btn.addEventListener("click", () => {
        const horas = prompt(
          `Horas para ${job.nombre} (max ${job.maxHoras}):`,
          "1"
        );
        if (horas !== null) {
          const h = parseFloat(horas);
          if (!isNaN(h) && h > 0) {
            this._doAction({ action: "trabajo", jobIndex: idx, hours: h });
          }
        }
      });
      this.actionsEl.appendChild(btn);
    });
  }

  _renderFlightActions(step) {
    const vuelos = step.vuelosDisponibles || [];
    if (vuelos.length === 0) {
      return;
    }

    const header = document.createElement("div");
    header.className = "trip-section-label";
    header.textContent = "Vuelos disponibles:";
    this.actionsEl.appendChild(header);

    vuelos.forEach((vuelo) => {
      const aeronaves = vuelo.aeronaves || [];
      aeronaves.forEach((aero) => {
        const subsidioTag = aero.esSubsidiada ? " [SUBSIDIADA]" : "";
        const btn = document.createElement("button");
        btn.className = "trip-action flight";
        btn.disabled = this._flightInProgress;
        btn.textContent =
          `${vuelo.destinoNombre} (${vuelo.destinoCiudad}) ` +
          `via ${aero.nombre} - $${aero.costoTotal.toFixed(2)}, ` +
          `${aero.tiempoVueloHoras.toFixed(1)}h${subsidioTag}`;
        btn.addEventListener("click", () =>
          this._iniciarVueloConAnimacion(
            vuelo.destinoId,
            aero.nombre
          )
        );
        this.actionsEl.appendChild(btn);
      });
    });
  }

  async _iniciarVueloConAnimacion(destinationId, aircraftName) {
    if (this._flightInProgress) {
      return;
    }
    this._flightInProgress = true;
    this._setActionsEnabled(false);

    try {
      const data = await this.api.iniciarVuelo({
        sessionId: this.sessionId,
        destinationId,
        aircraftName,
      });
      const snapshot = data.snapshot;
      if (!snapshot || !snapshot.enVuelo) {
        this._flightInProgress = false;
        this._setActionsEnabled(true);
        if (data.error) {
          this._renderStep(data.error);
        }
        return;
      }

      if (data.step) {
        this.currentStep = data.step;
      }
      this._renderFlightStatus(snapshot, "Vuelo en curso...");

      this.renderer.startFlightAnimation({
        origenLat: snapshot.latOrigen,
        origenLon: snapshot.lonOrigen,
        destinoLat: snapshot.latDestino,
        destinoLon: snapshot.lonDestino,
        origenId: snapshot.origenId,
        destinoId: snapshot.destinoId,
        aeronave: snapshot.aeronave,
        onProgress: () => this._onFlightTick(),
        onComplete: () => {},
        onInterrupted: () => {},
      });

      this._scheduleFlightTick(snapshot.tiempoVueloHoras);
      this._scheduleBlockPoll();
    } catch (error) {
      this._flightInProgress = false;
      this._setActionsEnabled(true);
      const messages =
        error && error.messages
          ? error.messages
          : [error.message || "Error al iniciar vuelo."];
      this._renderStep(messages.join("\n"));
    }
  }

  _scheduleFlightTick(tiempoVueloHoras) {
    if (this._flightTickHandle) {
      clearTimeout(this._flightTickHandle);
    }
    const totalSegundosServidor = Math.max(tiempoVueloHoras, 0.01) * 3600;
    const duracionAnimacionMs = Math.min(
      Math.max(totalSegundosServidor * 50, 4000),
      30000
    );
    const duracionAnimacionSeg = duracionAnimacionMs / 1000;
    const factorEscalado = totalSegundosServidor / duracionAnimacionSeg;
    const tickMs = 200;
    const tickSegundosUI = tickMs / 1000;
    const tickSegundosServidor = tickSegundosUI * factorEscalado;

    const advance = async () => {
      if (!this._flightInProgress) {
        return;
      }
      try {
        const data = await this.api.avanzarVuelo({
          sessionId: this.sessionId,
          dtSegundos: tickSegundosServidor,
        });
        const snap = data.snapshot;
        if (snap && snap.enVuelo) {
          this.renderer.setFlightTargetProgress(snap.progress);
          this._renderFlightStatus(snap, "Vuelo en curso...");
          if (snap.bloqueado) {
            this._flightTickHandle = null;
            await this._manejarInterrupcion();
            return;
          }
        }
        if (snap && snap.completado) {
          this.renderer.setFlightTargetProgress(1);
          this._flightTickHandle = null;
          this._onFlightCompleted(data);
          return;
        }
      } catch (error) {
        this._flightTickHandle = null;
        this._flightInProgress = false;
        this._setActionsEnabled(true);
        const messages =
          error && error.messages
            ? error.messages
            : [error.message || "Error al avanzar vuelo."];
        this._renderStep(messages.join("\n"));
        return;
      }

      if (this._flightInProgress) {
        this._flightTickHandle = setTimeout(advance, tickMs);
      }
    };

    this._flightTickHandle = setTimeout(advance, tickMs);
  }

  _scheduleBlockPoll() {
    if (this._flightPollHandle) {
      clearInterval(this._flightPollHandle);
    }
    this._flightPollHandle = setInterval(async () => {
      if (!this._flightInProgress) {
        this._stopBlockPoll();
        return;
      }
      try {
        const data = await this.api.verificarBloqueo({
          sessionId: this.sessionId,
        });
        if (data.bloqueado) {
          this._stopBlockPoll();
          await this._manejarInterrupcion();
        }
      } catch (error) {
        /* ignore polling errors */
      }
    }, 1500);
  }

  _stopBlockPoll() {
    if (this._flightPollHandle) {
      clearInterval(this._flightPollHandle);
      this._flightPollHandle = null;
    }
  }

  async _manejarInterrupcion() {
    if (this._flightTickHandle) {
      clearTimeout(this._flightTickHandle);
      this._flightTickHandle = null;
    }
    this._stopBlockPoll();

    this._renderFlightStatus(null, "Vuelo interrumpido, regresando al origen...");

    this.renderer.interruptFlightAnimation(async () => {
      try {
        const data = await this.api.cancelarVuelo({
          sessionId: this.sessionId,
        });
        this._flightInProgress = false;
        this._setActionsEnabled(true);
        if (data.step) {
          this.currentStep = data.step;
        }
        if (data.nuevaRuta) {
          this.renderer.setRouteResult(data.nuevaRuta, {
            label: "Ruta recalculada (tramo bloqueado)",
            showDestinos: false,
          });
          const detalles = [
            "Vuelo interrumpido. El viajero regreso al origen del tramo.",
            `Origen del tramo: ${data.origenTramo}`,
            `Destino original: ${data.destinoOriginal}`,
            "Nueva ruta: " + (data.nuevaRuta.camino || []).join(" -> "),
          ];
          this.statusEl.innerHTML = "";
          detalles.forEach((linea) => {
            const d = document.createElement("div");
            d.textContent = linea;
            this.statusEl.appendChild(d);
          });
          this._renderStep(
            data.errorRecalc
              ? `Recalculo: ${data.errorRecalc}`
              : "Selecciona el primer vuelo de la nueva ruta."
          );
        } else {
          this._renderStep(
            data.errorRecalc
              ? `No se pudo recalcular: ${data.errorRecalc}`
              : "Vuelo cancelado. Elige otro destino."
          );
        }
      } catch (error) {
        this._flightInProgress = false;
        this._setActionsEnabled(true);
        const messages =
          error && error.messages
            ? error.messages
            : [error.message || "Error al cancelar vuelo."];
        this._renderStep(messages.join("\n"));
      }
    });
  }

  async _onFlightCompleted(data) {
    this._stopBlockPoll();
    this._flightInProgress = false;
    this._setActionsEnabled(true);
    this.renderer.completeFlightAnimation();
    if (data.step) {
      this.currentStep = data.step;
    }
    this._renderStep();
  }

  _onFlightTick() {
    /* hook para futuras extensiones; la posición se actualiza en el loop principal */
  }

  _renderFlightStatus(snapshot, message) {
    if (!this.statusEl) return;
    const lines = [];
    if (message) lines.push(message);
    if (snapshot) {
      const progress = (snapshot.progress || 0) * 100;
      lines.push(
        `Vuelo: ${snapshot.origenId} -> ${snapshot.destinoId}`
      );
      lines.push(
        `Aeronave: ${snapshot.aeronave} | Distancia: ${snapshot.distanciaKm} km`
      );
      lines.push(
        `Progreso: ${progress.toFixed(0)}%`
      );
      lines.push(
        `Tiempo de vuelo: ${snapshot.tiempoVueloHoras} h`
      );
      if (snapshot.bloqueado) {
        const warn = document.createElement("div");
        warn.className = "trip-error";
        warn.textContent = "Ruta bloqueada: interrumpiendo vuelo...";
        this.statusEl.innerHTML = "";
        lines.forEach((line) => {
          const d = document.createElement("div");
          d.textContent = line;
          this.statusEl.appendChild(d);
        });
        this.statusEl.appendChild(warn);
        return;
      }
    }
    this.statusEl.innerHTML = "";
    lines.forEach((line) => {
      const div = document.createElement("div");
      div.textContent = line;
      this.statusEl.appendChild(div);
    });
  }

  _setActionsEnabled(enabled) {
    if (!this.actionsEl) return;
    const buttons = this.actionsEl.querySelectorAll("button");
    buttons.forEach((b) => {
      b.disabled = !enabled;
    });
  }

  _renderEndAction(step) {
    const btn = document.createElement("button");
    btn.className = "trip-action end";
    btn.textContent = "Finalizar viaje";
    btn.addEventListener("click", () => this._doAction({ action: "finalizar" }));
    this.actionsEl.appendChild(btn);
  }

  _renderReport(report) {
    this.panel.classList.remove("hidden");
    this.statusEl.innerHTML = "<strong>Viaje finalizado</strong>";
    this.actionsEl.innerHTML = "";

    const lines = [
      `Destinos visitados: ${report.destinosVisitados}`,
      `Vuelos realizados: ${report.vuelosRealizados}`,
      `Actividades realizadas: ${report.actividadesRealizadas}`,
      `Trabajos realizados: ${report.trabajosRealizados}`,
      `Alojamientos pagados: ${report.alojamientosPagados}`,
      `Alimentos consumidos: ${report.alimentosConsumidos}`,
      `Total gastado: $${report.totalGastado.toFixed(2)}`,
      `Total ganado: $${report.totalGanado.toFixed(2)}`,
      `Presupuesto final: $${report.presupuestoFinal.toFixed(2)}`,
      `Tiempo total: ${report.tiempoTotalHoras.toFixed(1)} h`,
      `Ruta: ${(report.camino || []).join(" -> ")}`,
    ];

    this.reportEl.classList.remove("hidden");
    this.reportEl.innerHTML = "";
    const header = document.createElement("div");
    header.className = "trip-section-label";
    header.textContent = "Reporte final:";
    this.reportEl.appendChild(header);

    lines.forEach((line) => {
      const div = document.createElement("div");
      div.textContent = line;
      this.reportEl.appendChild(div);
    });

    const decisionsHeader = document.createElement("div");
    decisionsHeader.className = "trip-section-label";
    decisionsHeader.textContent = `Decisiones (${report.decisiones.length}):`;
    this.reportEl.appendChild(decisionsHeader);

    (report.decisiones || []).forEach((dec, i) => {
      const div = document.createElement("div");
      div.className = "trip-decision";
      div.textContent = `${i + 1}. ${dec.tipo} @ ${dec.nodeId}: $${dec.costo.toFixed(2)} costo, $${dec.ingreso.toFixed(2)} ingreso, ${dec.tiempoInvertidoHoras.toFixed(1)}h`;
      this.reportEl.appendChild(div);
    });

    // Mostrar la ruta en el mapa
    if (report.camino && report.camino.length > 1) {
      const graphNodes = this.store.getGraph().nodos || [];
      const nodeById = new Map(graphNodes.map((n) => [n.id, n]));
      const coords = [];
      report.camino.forEach((id) => {
        const node = nodeById.get(id);
        if (node && typeof node.lat === "number" && typeof node.lon === "number") {
          coords.push([node.lat, node.lon]);
        }
      });
      if (coords.length >= 2) {
        this.renderer.setTripPath(coords, report.camino);
      }
    }

    // Mostrar detalles de la ruta
    if (report.camino && report.camino.length > 1) {
      const detailsLines = [
        `Viaje interactivo - Ruta completa:`,
        (report.camino || []).join(" -> "),
        `Destinos: ${report.destinosVisitados}`,
        `Gasto total: $${report.totalGastado.toFixed(2)}`,
        `Ganancia total: $${report.totalGanado.toFixed(2)}`,
        `Tiempo: ${report.tiempoTotalHoras.toFixed(1)} h`,
      ];
      this.renderer.setRouteResult(
        {
          encontrado: true,
          camino: report.camino,
          totalKm: null,
          totalCosto: report.totalGastado,
        },
        { label: "Viaje interactivo", showDestinos: true }
      );
    }
  }
}
