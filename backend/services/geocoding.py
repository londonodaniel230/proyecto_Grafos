import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from ..errors import ValidationError

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "proyecto-2/1.0 (geocoding)"


def geocode_country(query: str) -> List[Dict[str, Any]]:
    query = (query or "").strip()
    if not query:
        raise ValidationError(["Missing query for geocoding."])

    params = {
        "q": query,
        "format": "json",
        "limit": 6,
        "addressdetails": 1,
        "accept-language": "es",
    }
    url = f"{NOMINATIM_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:
        raise ValidationError(["Geocoding request failed."]) from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValidationError(["Invalid geocoding response."]) from exc

    results: List[Dict[str, Any]] = []
    for item in data or []:
        lat_raw = item.get("lat")
        lon_raw = item.get("lon")
        if lat_raw is None or lon_raw is None:
            continue

        address = item.get("address") or {}
        country = address.get("country") or (item.get("display_name") or "")
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except (TypeError, ValueError):
            continue

        results.append(
            {
                "name": country,
                "displayName": item.get("display_name") or country,
                "lat": lat,
                "lon": lon,
                "type": item.get("type"),
                "class": item.get("class"),
                "address": address,
                "countryCode": address.get("country_code"),
            }
        )

    return results
