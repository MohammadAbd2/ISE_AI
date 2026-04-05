import re


def _to_number(value: str) -> float | None:
    cleaned = re.sub(r"[^\d.\-]", "", str(value or "").replace(",", ""))
    if not cleaned:
        return None
    try:
        parsed = float(cleaned)
    except ValueError:
        return None
    return parsed


def _detect_chart_intent(text: str) -> bool:
    return bool(re.search(r"(chart|diagram|graph|plot|visuali[sz]e|2d)", text, re.I))


def _detect_map_intent(text: str) -> bool:
    return bool(re.search(r"(map|globe|3d|latitude|longitude|flight)", text, re.I))


def _parse_pairs(text: str) -> list[dict]:
    rows: list[dict] = []
    banned = {"display", "create", "show", "plot", "graph", "diagram", "visualize", "visualise"}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z]{3,12}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Q\d)\s+(.+)$", line)
        if not match:
            continue
        label, remainder = match.groups()
        if label.lower() in banned:
            continue
        value = _to_number(remainder)
        if value is None:
            continue
        rows.append({"label": label, "value": value, "detail": remainder.strip()})
    return rows


def _parse_coordinates(text: str) -> list[dict]:
    points: list[dict] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        csv = [item.strip() for item in line.split(",")]
        if len(csv) >= 3:
            lat = _to_number(csv[1])
            lon = _to_number(csv[2])
            altitude = _to_number(csv[3]) if len(csv) > 3 else 0
            if lat is not None and lon is not None:
                points.append(
                    {
                        "id": csv[0],
                        "label": csv[0],
                        "lat": lat,
                        "lon": lon,
                        "altitude": altitude or 0,
                        "detail": line,
                    }
                )
                continue
        match = re.match(
            r"^(.+?)\s+(?:lat|latitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s+"
            r"(?:lon|lng|longitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)"
            r"(?:\s+(?:alt|altitude|z)\s*[:=]?\s*(-?\d+(?:\.\d+)?))?$",
            line,
            re.I,
        )
        if match:
            points.append(
                {
                    "id": match.group(1).strip(),
                    "label": match.group(1).strip(),
                    "lat": float(match.group(2)),
                    "lon": float(match.group(3)),
                    "altitude": float(match.group(4) or 0),
                    "detail": line,
                }
            )
    return points


def _build_synthetic_rows(text: str) -> list[dict]:
    lower = text.lower()
    if not _detect_chart_intent(text):
        return []
    if not re.search(r"(salary|income|profit|revenue)", lower):
        return []
    labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    base = 18000 if re.search(r"(profit|revenue)", lower) else 12000
    rows: list[dict] = []
    for index, label in enumerate(labels):
        value = max(2500, round(base + (((index * 7919) % 9) - 4) * 420 + index * 165))
        rows.append(
            {
                "label": label,
                "value": value,
                "detail": f"{label}: {value:,} synthetic value",
            }
        )
    return rows


def build_visualization_response(text: str) -> dict | None:
    rows = _parse_pairs(text)
    points = _parse_coordinates(text)
    if _detect_map_intent(text) and points:
        spec = {
            "type": "map3d",
            "title": "3D map",
            "subtitle": "Auto-built from your message",
            "points": points,
        }
        return {
            "spec": spec,
            "render_blocks": [{"type": "visualization", "payload": spec}],
            "summary": f"Built a 3D map with {len(points)} plotted points.",
        }
    if _detect_chart_intent(text):
        resolved_rows = rows if len(rows) >= 2 else _build_synthetic_rows(text)
        if len(resolved_rows) >= 2:
            spec = {
                "type": "chart2d",
                "title": "2D chart",
                "subtitle": "Auto-built from your message",
                "rows": resolved_rows,
                "yLabel": "Value",
            }
            return {
                "spec": spec,
                "render_blocks": [{"type": "visualization", "payload": spec}],
                "summary": f"Built a 2D chart with {len(resolved_rows)} data points.",
            }
    return None
