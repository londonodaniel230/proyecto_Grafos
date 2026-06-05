export class ApiError extends Error {
  constructor(messages) {
    super("API Error");
    this.messages = messages;
  }
}

export class ApiClient {
  async uploadGraph(file) {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("/api/graph", {
      method: "POST",
      body: formData,
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const messages = data && data.errors ? data.errors : ["Unknown server error."];
      throw new ApiError(messages);
    }

    return data;
  }

  async geocode(query) {
    const url = `/api/geocode?query=${encodeURIComponent(query)}`;
    const response = await fetch(url);

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const messages = data && data.errors ? data.errors : ["Geocoding error."];
      throw new ApiError(messages);
    }

    return data && data.results ? data.results : [];
  }

  async optimizeRoute(payload) {
    const response = await fetch("/api/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const messages = data && data.errors ? data.errors : ["Unknown server error."];
      throw new ApiError(messages);
    }

    return data;
  }

  async startTrip(payload) {
    const response = await fetch("/api/trip/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const messages = data && data.errors ? data.errors : ["Unknown server error."];
      throw new ApiError(messages);
    }

    return data;
  }

  async tripAction(payload) {
    const response = await fetch("/api/trip/act", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data = null;
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      data = await response.json();
    }

    if (!response.ok) {
      const messages = data && data.errors ? data.errors : ["Unknown server error."];
      throw new ApiError(messages);
    }

    return data;
  }

  async blockRoute(payload) {
    const response = await fetch("/api/route/block", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(data.errors || ["Error blocking route."]);
    }
    return data;
  }

  async unblockRoute(payload) {
    const response = await fetch("/api/route/unblock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(data.errors || ["Error unblocking route."]);
    }
    return data;
  }

  async getBlockedRoutes() {
    const response = await fetch("/api/route/blocked");
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(data.errors || ["Error fetching blocked routes."]);
    }
    return data.blocked || [];
  }

  async autoPlan(payload) {
    const response = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new ApiError(data.errors || ["Error planning routes."]);
    }
    return data;
  }
}
