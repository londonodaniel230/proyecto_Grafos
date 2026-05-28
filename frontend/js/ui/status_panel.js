export class StatusPanel {
  constructor(statusEl, errorsEl) {
    this.statusEl = statusEl;
    this.errorsEl = errorsEl;
  }

  setStatus(message) {
    if (this.statusEl) {
      this.statusEl.textContent = message || "";
    }
  }

  clearErrors() {
    if (!this.errorsEl) {
      return;
    }
    this.errorsEl.innerHTML = "";
  }

  showErrors(messages) {
    if (!this.errorsEl) {
      return;
    }

    this.clearErrors();
    (messages || []).forEach((message) => {
      const item = document.createElement("li");
      item.textContent = message;
      this.errorsEl.appendChild(item);
    });
  }
}
