"""Pull schema.org Event objects out of JSON-LD script tags. No network."""

import json

from bs4 import BeautifulSoup


def extract_events(html: str) -> list[dict]:
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or "")
        except (TypeError, json.JSONDecodeError):
            continue
        found.extend(_events_from(data))
    return found


def _events_from(data) -> list[dict]:
    if isinstance(data, list):
        rows = []
        for item in data:
            rows.extend(_events_from(item))
        return rows
    if not isinstance(data, dict):
        return []
    kind = data.get("@type")
    types = kind if isinstance(kind, list) else [kind]
    if "Event" in types:
        return [_normalise(data)]
    graph = data.get("@graph")
    if graph:
        return _events_from(graph)
    return []


def _normalise(data: dict) -> dict:
    location = data.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    address = location.get("address") if isinstance(location, dict) else None
    if isinstance(address, dict):
        place = ", ".join(
            part
            for part in (address.get("addressLocality"), address.get("addressCountry"))
            if part
        )
    else:
        place = location.get("name") if isinstance(location, dict) else None
    offers = data.get("offers") or {}
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    price = offers.get("price") if isinstance(offers, dict) else None
    return {
        "title": data.get("name") or "",
        "description": data.get("description") or "",
        "start_time": data.get("startDate"),
        "end_time": data.get("endDate"),
        "venue": location.get("name") if isinstance(location, dict) else None,
        "location": place,
        "registration_link": data.get("url"),
        "is_free": str(price) in ("0", "0.0", "0.00", "") or price is None,
        "format": "online" if data.get("eventAttendanceMode", "").endswith("OnlineEventAttendanceMode") else "in_person",
    }
