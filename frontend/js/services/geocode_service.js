export class GeocodeService {
  constructor(apiClient) {
    this.apiClient = apiClient;
  }

  async geocode(query) {
    const term = (query || "").trim();
    if (!term) {
      return [];
    }

    return this.apiClient.geocode(term);
  }
}
