function toNumber(value) {
  const cleaned = String(value ?? "")
    .replace(/,/g, "")
    .replace(/[^\d.-]/g, "");
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function detectChartIntent(text) {
  return /(chart|diagram|graph|plot|visuali[sz]e|2d)/i.test(text);
}

function detectMapIntent(text) {
  return /(map|globe|3d|latitude|longitude|flight)/i.test(text);
}

function parsePairs(lines) {
  const rows = [];
  const bannedLabels = new Set(["display", "create", "show", "plot", "graph", "diagram", "visualize", "visualise"]);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const match = trimmed.match(/^([A-Za-z]{3,12}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|Q\d)\s+(.+)$/);
    if (!match) {
      continue;
    }
    if (bannedLabels.has(match[1].toLowerCase())) {
      continue;
    }
    const value = toNumber(match[2]);
    if (value === null) {
      continue;
    }
    rows.push({
      label: match[1],
      value,
      detail: match[2].trim(),
    });
  }
  return rows;
}

function parseCsv(text) {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (lines.length < 2 || !lines[0].includes(",")) {
    return [];
  }
  const headers = lines[0].split(",").map((item) => item.trim());
  if (headers.length < 2) {
    return [];
  }
  const rows = [];
  for (const line of lines.slice(1)) {
    const parts = line.split(",").map((item) => item.trim());
    if (parts.length < 2) {
      continue;
    }
    const value = toNumber(parts[1]);
    if (value === null) {
      continue;
    }
    rows.push({
      label: parts[0],
      value,
      detail: `${headers[1]}: ${parts[1]}`,
    });
  }
  return rows;
}

function parseCoordinateRows(text) {
  const lines = text.split("\n");
  const points = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const csv = trimmed.split(",").map((item) => item.trim());
    if (csv.length >= 3) {
      const lat = toNumber(csv[1]);
      const lon = toNumber(csv[2]);
      const altitude = csv.length >= 4 ? toNumber(csv[3]) : 0;
      if (lat !== null && lon !== null) {
        points.push({
          id: csv[0],
          label: csv[0],
          lat,
          lon,
          altitude: altitude ?? 0,
          detail: trimmed,
        });
        continue;
      }
    }
    const match = trimmed.match(
      /^(.+?)\s+(?:lat|latitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)\s+(?:lon|lng|longitude)\s*[:=]?\s*(-?\d+(?:\.\d+)?)(?:\s+(?:alt|altitude|z)\s*[:=]?\s*(-?\d+(?:\.\d+)?))?/i,
    );
    if (match) {
      points.push({
        id: match[1].trim(),
        label: match[1].trim(),
        lat: Number(match[2]),
        lon: Number(match[3]),
        altitude: Number(match[4] || 0),
        detail: trimmed,
      });
    }
  }
  return points;
}

function generateMonthlyLabels() {
  return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
}

function buildSyntheticRows(text) {
  const lower = text.toLowerCase();
  if (!detectChartIntent(text)) {
    return [];
  }

  if (/(random).*(salary|income|profit|revenue)|(salary|income|profit|revenue).*(random)/i.test(lower)) {
    const labels = generateMonthlyLabels();
    const base = lower.includes("profit") || lower.includes("revenue") ? 18000 : 12000;
    return labels.map((label, index) => {
      const seasonal = Math.sin(index / 12 * Math.PI * 2) * (base * 0.18);
      const jitter = ((index * 7919) % 9 - 4) * 420;
      const value = Math.round(base + seasonal + jitter);
      return {
        label,
        value: Math.max(2500, value),
        detail: `${label}: ${Math.max(2500, value).toLocaleString()} synthetic value`,
      };
    });
  }

  if (/(one year|1 year|12 months|monthly)/i.test(lower) && /(salary|income|profit|revenue)/i.test(lower)) {
    const labels = generateMonthlyLabels();
    return labels.map((label, index) => {
      const value = 9000 + index * 450;
      return {
        label,
        value,
        detail: `${label}: ${value.toLocaleString()} projected value`,
      };
    });
  }

  return [];
}

export function buildVisualizationSpec(text) {
  const lines = text.split("\n");
  const chartRows = parsePairs(lines);
  const csvRows = parseCsv(text);
  const syntheticRows = buildSyntheticRows(text);
  const rows = chartRows.length >= 2 ? chartRows : csvRows.length >= 2 ? csvRows : syntheticRows;
  const points = parseCoordinateRows(text);

  if (detectMapIntent(text) && points.length > 0) {
    return {
      type: "map3d",
      title: "3D map",
      subtitle: "Derived from your prompt data",
      points,
    };
  }

  if (detectChartIntent(text) && rows.length >= 2) {
    const max = Math.max(...rows.map((item) => item.value), 1);
    return {
      type: "chart2d",
      title: "2D chart",
      subtitle: "Auto-built from your message",
      rows,
      yLabel: max >= 1000 ? "Value" : "Score",
    };
  }

  return null;
}

export function summarizeVisualization(spec) {
  if (!spec) {
    return "";
  }
  if (spec.type === "chart2d") {
    return `I rendered a 2D chart with ${spec.rows.length} data points from your prompt.`;
  }
  if (spec.type === "map3d") {
    return `I rendered a 3D map with ${spec.points.length} plotted points from your prompt.`;
  }
  return "";
}

function toCsv(rows) {
  const lines = ["label,value,detail"];
  for (const row of rows) {
    lines.push(`"${row.label}",${row.value},"${String(row.detail || "").replace(/"/g, '""')}"`);
  }
  return lines.join("\n");
}

function summarizeChartRows(rows) {
  const values = rows.map((row) => row.value);
  const total = values.reduce((sum, value) => sum + value, 0);
  const max = Math.max(...values);
  const min = Math.min(...values);
  const average = total / rows.length;
  const peak = rows.find((row) => row.value === max);
  const low = rows.find((row) => row.value === min);
  return {
    total,
    average,
    max,
    min,
    peak,
    low,
  };
}

function summarizeMapPoints(points) {
  const altitudeValues = points.map((point) => point.altitude || 0);
  const highest = points.reduce(
    (current, point) => ((point.altitude || 0) > (current.altitude || 0) ? point : current),
    points[0],
  );
  const averageAltitude =
    altitudeValues.reduce((sum, value) => sum + value, 0) / Math.max(altitudeValues.length, 1);
  return {
    highest,
    averageAltitude,
  };
}

export function buildVisualizationArtifacts(spec) {
  if (!spec) {
    return [];
  }

  if (spec.type === "chart2d") {
    const metrics = summarizeChartRows(spec.rows);
    return [
      {
        type: "report",
        payload: {
          title: spec.title || "Chart analysis",
          summary: `Analyzed ${spec.rows.length} points. Total ${metrics.total.toLocaleString()}, average ${metrics.average.toFixed(1)}.`,
          highlights: [
            `Peak: ${metrics.peak?.label} at ${metrics.max.toLocaleString()}`,
            `Low: ${metrics.low?.label} at ${metrics.min.toLocaleString()}`,
            `Range: ${(metrics.max - metrics.min).toLocaleString()}`,
          ],
        },
      },
      {
        type: "file_result",
        payload: {
          title: "Structured chart data",
          files: [
            {
              path: "analysis/chart-data.csv",
              summary: toCsv(spec.rows),
            },
          ],
        },
      },
    ];
  }

  if (spec.type === "map3d") {
    const metrics = summarizeMapPoints(spec.points);
    return [
      {
        type: "report",
        payload: {
          title: spec.title || "Map analysis",
          summary: `Mapped ${spec.points.length} points with an average altitude of ${Math.round(metrics.averageAltitude).toLocaleString()}.`,
          highlights: [
            `Highest point: ${metrics.highest?.label} at ${Math.round(metrics.highest?.altitude || 0).toLocaleString()}`,
            `Plotted identifiers: ${spec.points.slice(0, 4).map((point) => point.label).join(", ")}`,
          ],
        },
      },
      {
        type: "file_result",
        payload: {
          title: "Structured map points",
          files: spec.points.slice(0, 8).map((point) => ({
            path: `points/${point.id}.json`,
            summary: JSON.stringify(point, null, 2),
          })),
        },
      },
    ];
  }

  return [];
}
