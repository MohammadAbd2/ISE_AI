import { useMemo, useState } from "react";

function Chart2D({ spec }) {
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const width = 720;
  const height = 280;
  const padding = 40;
  const rows = spec.rows || [];
  const maxValue = Math.max(...rows.map((row) => row.value), 1);

  const points = rows.map((row, index) => {
    const x = padding + (index * (width - padding * 2)) / Math.max(rows.length - 1, 1);
    const y = height - padding - (row.value / maxValue) * (height - padding * 2);
    return { ...row, x, y };
  });

  const path = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  return (
    <div className="viz-card">
      <div className="viz-header">
        <div>
          <h3>{spec.title}</h3>
          <p>{spec.subtitle}</p>
        </div>
      </div>
      <div className="chart-frame">
        <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" role="img" aria-label={spec.title}>
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} className="chart-axis" />
          <path d={path} className="chart-line" />
          {points.map((point, index) => (
            <g key={`${point.label}-${index}`}>
              <circle
                cx={point.x}
                cy={point.y}
                r={hoveredIndex === index ? 7 : 5}
                className="chart-point"
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
              <text x={point.x} y={height - 14} textAnchor="middle" className="chart-label">
                {point.label}
              </text>
            </g>
          ))}
        </svg>
        {hoveredIndex !== null ? (
          <div className="chart-tooltip">
            <strong>{points[hoveredIndex].label}</strong>
            <span>{points[hoveredIndex].value.toLocaleString()}</span>
            <small>{points[hoveredIndex].detail}</small>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function projectPoint(point, rotation, zoom) {
  const lat = (point.lat * Math.PI) / 180;
  const lon = ((point.lon + rotation) * Math.PI) / 180;
  const radius = 120 + (point.altitude || 0) * 0.004;
  const x = Math.cos(lat) * Math.sin(lon);
  const y = Math.sin(lat);
  const z = Math.cos(lat) * Math.cos(lon);
  const perspective = zoom / (2 - z);
  return {
    ...point,
    x: x * radius * perspective,
    y: y * radius * perspective,
    z,
    visible: z > -0.35,
  };
}

function Map3D({ spec }) {
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1.15);
  const [hovered, setHovered] = useState(null);

  const projected = useMemo(
    () => spec.points.map((point) => projectPoint(point, rotation, zoom)),
    [rotation, spec.points, zoom],
  );

  function handlePointerDown(event) {
    const startX = event.clientX;
    const startRotation = rotation;
    const move = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      setRotation(startRotation + delta * 0.35);
    };
    const stop = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", stop);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  }

  function handleWheel(event) {
    event.preventDefault();
    setZoom((current) => Math.min(2.1, Math.max(0.75, current - event.deltaY * 0.001)));
  }

  return (
    <div className="viz-card">
      <div className="viz-header">
        <div>
          <h3>{spec.title}</h3>
          <p>{spec.subtitle}</p>
        </div>
        <div className="map-controls">
          <button type="button" onClick={() => setZoom((current) => Math.min(2.1, current + 0.1))}>+</button>
          <button type="button" onClick={() => setZoom((current) => Math.max(0.75, current - 0.1))}>-</button>
          <button type="button" onClick={() => { setZoom(1.15); setRotation(0); }}>Reset</button>
        </div>
      </div>
      <div className="map-frame" onPointerDown={handlePointerDown} onWheel={handleWheel}>
        <svg viewBox="-180 -160 360 320" className="map-svg" role="img" aria-label={spec.title}>
          <defs>
            <radialGradient id="globeFill" cx="50%" cy="35%">
              <stop offset="0%" stopColor="#66ddff" stopOpacity="0.36" />
              <stop offset="100%" stopColor="#0c1f30" stopOpacity="0.95" />
            </radialGradient>
          </defs>
          <circle cx="0" cy="0" r="124" className="globe-shell" fill="url(#globeFill)" />
          <ellipse cx="0" cy="0" rx="124" ry="42" className="globe-grid" />
          <ellipse cx="0" cy="0" rx="86" ry="124" className="globe-grid" />
          {projected.filter((point) => point.visible).map((point) => (
            <g
              key={point.id}
              transform={`translate(${point.x}, ${point.y})`}
              onMouseEnter={() => setHovered(point)}
              onMouseLeave={() => setHovered(null)}
            >
              <line x1="0" y1="0" x2="0" y2={-Math.max(10, point.altitude * 0.02)} className="map-stem" />
              <circle cy={-Math.max(10, point.altitude * 0.02)} r="5.5" className="map-point" />
            </g>
          ))}
        </svg>
        {hovered ? (
          <div className="map-tooltip">
            <strong>{hovered.label}</strong>
            <span>{hovered.lat}, {hovered.lon}</span>
            <small>{hovered.detail}</small>
          </div>
        ) : (
          <div className="map-instructions">Drag to rotate. Scroll or use buttons to zoom.</div>
        )}
      </div>
    </div>
  );
}

export default function DynamicVisualization({ spec }) {
  if (!spec) {
    return null;
  }
  if (spec.type === "map3d") {
    return <Map3D spec={spec} />;
  }
  return <Chart2D spec={spec} />;
}
