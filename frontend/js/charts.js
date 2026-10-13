// Dependency-free charts. Each chart returns an SVG string or mounts into a
// container. Animation is started by adding class "in" once the element is visible.

const NF_INR = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function fmtINR(v) {
  return "₹" + NF_INR.format(Math.round(Number(v) || 0));
}

export function fmtCompact(v) {
  const n = Number(v) || 0;
  if (Math.abs(n) >= 1e7) return `₹${(n / 1e7).toFixed(2)} Cr`;
  if (Math.abs(n) >= 1e5) return `₹${(n / 1e5).toFixed(2)} L`;
  return fmtINR(n);
}

export function fmtPct(v, digits = 1) {
  return `${(Number(v) || 0).toFixed(digits)}%`;
}

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[c]));
}

export function escapeAttr(s) {
  return escapeHtml(s);
}

const STOPS = [
  [0.0, [63, 182, 168]],   // teal
  [0.45, [124, 140, 255]], // indigo
  [0.75, [242, 165, 65]],  // saffron
  [1.0, [240, 113, 113]],  // coral
];

export function heatColor(t) {
  const x = Math.min(1, Math.max(0, t));
  for (let i = 0; i < STOPS.length - 1; i++) {
    const [a, ca] = STOPS[i];
    const [b, cb] = STOPS[i + 1];
    if (x >= a && x <= b) {
      const k = (x - a) / (b - a);
      const c = ca.map((v, j) => Math.round(v + (cb[j] - v) * k));
      return `rgb(${c[0]},${c[1]},${c[2]})`;
    }
  }
  return "rgb(240,113,113)";
}

/** Start CSS transitions for elements inside `root` on the next frame. */
export function startAnimations(root) {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      root.querySelectorAll(".arc[data-to]").forEach((el) => {
        el.style.strokeDashoffset = el.dataset.to;
      });
      root.querySelectorAll(".draw, .bar-grow, .fade-in").forEach((el) => el.classList.add("in"));
    });
  });
}

// ---------------------------------------------------------------------------
// Donut: share of a total (e.g., interest vs principal) - Ultra Luxury Edition
// ---------------------------------------------------------------------------
let donutIdCounter = 0;
export function donut({ value, total, colorA, colorB, centerTop, centerBottom, gradientType = "auto" }) {
  const size = 200, cx = 100, cy = 100, r = 74, sw = 15;
  const C = 2 * Math.PI * r;
  const frac = total > 0 ? Math.min(1, Math.max(0, value / total)) : 0;
  const gradId = `donutGrad_${++donutIdCounter}`;
  const glowId = `donutGlow_${donutIdCounter}`;
  
  // Choose rich luxury gradient stops
  const isGold = colorB.includes("accent") && !colorB.includes("accent-3");
  const stop1 = isGold ? "#fcd34d" : "#60a5fa";
  const stop2 = isGold ? "#d4af37" : "#3b82f6";
  const stop3 = isGold ? "#92400e" : "#1d4ed8";

  return `
  <svg viewBox="0 0 ${size} ${size}" class="luxury-donut-svg" role="img" aria-label="${centerTop} ${centerBottom}">
    <defs>
      <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="${stop1}"/>
        <stop offset="50%" stop-color="${stop2}"/>
        <stop offset="100%" stop-color="${stop3}"/>
      </linearGradient>
      <filter id="${glowId}" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
    </defs>
    <!-- Background track ring with soft frosted edge -->
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="var(--line-hi)" stroke-width="${sw}" opacity="0.4"/>
    <circle cx="${cx}" cy="${cy}" r="${r + (sw / 2) + 2}" fill="none" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 4" opacity="0.6"/>
    <!-- Animated fill arc with gradient and glow -->
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="url(#${gradId})" stroke-width="${sw}"
            stroke-dasharray="${C}" stroke-dashoffset="${C}" data-to="${C * (1 - frac)}"
            class="arc" transform="rotate(-90 ${cx} ${cy})" stroke-linecap="round"
            filter="url(#${glowId})"/>
    <!-- Center text -->
    <g class="donut-center-group">
      <text x="${cx}" y="${cy - 2}" text-anchor="middle" class="lbl-strong donut-main-pct">${centerTop}</text>
      <text x="${cx}" y="${cy + 20}" text-anchor="middle" class="donut-sub-lbl">${centerBottom}</text>
    </g>
  </svg>`;
}

// ---------------------------------------------------------------------------
// Historical & 10-Year Future Price Forecast Trajectory Chart
// ---------------------------------------------------------------------------
export function forecastChart({ dataPoints, width = 680, height = 280, currencyFmt = fmtCompact }) {
  const pad = { l: 74, r: 40, t: 36, b: 46 };
  const xs = dataPoints.map((d) => d.year);
  const ys = dataPoints.map((d) => d.price);
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = Math.min(...ys) * 0.88;
  const ymax = Math.max(...ys) * 1.12;

  const sx = (x) => pad.l + ((x - xmin) / (xmax - xmin || 1)) * (width - pad.l - pad.r);
  const sy = (y) => pad.t + (1 - (y - ymin) / (ymax - ymin || 1)) * (height - pad.t - pad.b);

  const gradId = `forecastGrad_${Math.floor(Math.random() * 10000)}`;

  // Grid lines (horizontal)
  const steps = 4;
  let grid = "";
  for (let i = 0; i <= steps; i++) {
    const frac = i / steps;
    const yVal = ymin + (ymax - ymin) * (1 - frac);
    const yPos = pad.t + frac * (height - pad.t - pad.b);
    grid += `
      <line x1="${pad.l}" x2="${width - pad.r}" y1="${yPos}" y2="${yPos}" stroke="var(--line)" stroke-dasharray="3 4"/>
      <text x="${pad.l - 12}" y="${yPos + 4}" text-anchor="end" fill="var(--muted)" font-size="11" font-family="var(--mono)">${currencyFmt(yVal)}</text>
    `;
  }

  // X ticks
  const xticks = dataPoints.map((d) => {
    const xPos = sx(d.year);
    const isPresent = d.isCurrent;
    const isFuture = d.isFuture;
    const color = isPresent ? "var(--accent)" : isFuture ? "var(--accent-light)" : "var(--muted)";
    const weight = isPresent ? "bold" : "normal";
    return `
      <line x1="${xPos}" x2="${xPos}" y1="${height - pad.b}" y2="${height - pad.b + 6}" stroke="${color}" stroke-width="${isPresent ? 2 : 1}"/>
      <text x="${xPos}" y="${height - pad.b + 20}" text-anchor="middle" fill="${color}" font-weight="${weight}" font-size="11">${d.label || d.year}</text>
    `;
  }).join("");

  // Build path d
  const lineD = dataPoints.map((d, i) => `${i === 0 ? "M" : "L"} ${sx(d.year).toFixed(1)} ${sy(d.price).toFixed(1)}`).join(" ");
  // Area path for gradient fill under the line
  const areaD = `${lineD} L ${sx(dataPoints[dataPoints.length - 1].year).toFixed(1)} ${height - pad.b} L ${sx(dataPoints[0].year).toFixed(1)} ${height - pad.b} Z`;

  // Milestone dots
  const dots = dataPoints.map((d) => {
    const xPos = sx(d.year);
    const yPos = sy(d.price);
    const isCurrent = d.isCurrent;
    const fill = isCurrent ? "var(--accent)" : d.isFuture ? "#60a5fa" : "#94a3b8";
    const r = isCurrent ? 6 : 4.5;
    return `
      <g class="forecast-dot-group">
        <circle cx="${xPos}" cy="${yPos}" r="${r + 4}" fill="${fill}" opacity="0.2"/>
        <circle cx="${xPos}" cy="${yPos}" r="${r}" fill="#0d131f" stroke="${fill}" stroke-width="2.5"/>
        <text x="${xPos}" y="${yPos - 12}" text-anchor="middle" fill="var(--text)" font-size="10.5" font-weight="600" font-family="var(--mono)">${currencyFmt(d.price)}</text>
      </g>
    `;
  }).join("");

  return `
  <svg viewBox="0 0 ${width} ${height}" class="forecast-svg" role="img" aria-label="Historical and future property valuation forecast">
    <defs>
      <linearGradient id="${gradId}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.35"/>
        <stop offset="60%" stop-color="var(--accent-3)" stop-opacity="0.12"/>
        <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.0"/>
      </linearGradient>
      <linearGradient id="${gradId}_stroke" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#94a3b8"/>
        <stop offset="35%" stop-color="var(--accent)"/>
        <stop offset="100%" stop-color="#60a5fa"/>
      </linearGradient>
    </defs>
    ${grid}
    <path d="${areaD}" fill="url(#${gradId})"/>
    <path d="${lineD}" fill="none" stroke="url(#${gradId}_stroke)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" class="draw in"/>
    ${dots}
    ${xticks}
  </svg>`;
}


// ---------------------------------------------------------------------------
// Horizontal bars (DOM). Used for city ranking and the accuracy comparison.
// ---------------------------------------------------------------------------
export function mountHbars(container, items, { format = (v) => v, max = null } = {}) {
  const top = max ?? Math.max(...items.map((i) => i.value), 1);
  container.innerHTML = "";
  items.forEach((it) => {
    const row = document.createElement("div");
    row.className = "hbar-row";
    const pct = Math.max(2, (it.value / top) * 100);
    row.innerHTML = `
      <span class="name" title="${it.label}">${it.label}</span>
      <span class="hbar-track"><span class="hbar-fill" data-w="${pct}"></span></span>
      <span class="hbar-val">${format(it.value)}</span>`;
    container.appendChild(row);
  });
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      container.querySelectorAll(".hbar-fill").forEach((el) => {
        el.style.width = el.dataset.w + "%";
      });
    });
  });
}

// ---------------------------------------------------------------------------
// Line chart: EMI vs tenure, one series per rate
// ---------------------------------------------------------------------------
export function lineChart({ series, xLabel, yFormat, width = 640, height = 260 }) {
  const pad = { l: 64, r: 16, t: 16, b: 40 };
  const xs = series.flatMap((s) => s.points.map((p) => p.x));
  const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const xmin = Math.min(...xs), xmax = Math.max(...xs);
  const ymin = 0, ymax = Math.max(...ys) * 1.08;
  const sx = (x) => pad.l + ((x - xmin) / (xmax - xmin || 1)) * (width - pad.l - pad.r);
  const sy = (y) => pad.t + (1 - (y - ymin) / (ymax - ymin || 1)) * (height - pad.t - pad.b);

  const grid = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const y = pad.t + f * (height - pad.t - pad.b);
    const v = ymax - f * (ymax - ymin);
    return `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-dasharray="3 4"/>
            <text x="${pad.l - 8}" y="${y + 4}" text-anchor="end">${yFormat(v)}</text>`;
  }).join("");

  const xticks = [...new Set(xs)].filter((_, i, arr) => arr.length <= 8 || i % 2 === 0);
  const xt = xticks.map((x) => `<text x="${sx(x)}" y="${height - 14}" text-anchor="middle">${x}y</text>`).join("");

  const paths = series.map((s) => {
    const d = s.points.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" ");
    const last = s.points[s.points.length - 1];
    return `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2.6" stroke-linecap="round" pathLength="1" class="draw"/>
            <circle cx="${sx(last.x)}" cy="${sy(last.y)}" r="4" fill="${s.color}" class="fade-in"/>
            `;
  }).join("");

  const legend = series.map((s, i) => `
    <line x1="${pad.l + 4}" x2="${pad.l + 22}" y1="${pad.t + 6 + i * 18}" y2="${pad.t + 6 + i * 18}" stroke="${s.color}" stroke-width="3" stroke-linecap="round"/>
    <text x="${pad.l + 28}" y="${pad.t + 10 + i * 18}" style="fill:var(--text)">${s.label} p.a.</text>`).join("");

  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${xLabel}">
    ${grid}${xt}${paths}${legend}
    <text x="${(pad.l + width - pad.r) / 2}" y="${height}" text-anchor="middle">${xLabel}</text>
  </svg>`;
}

// ---------------------------------------------------------------------------
// Geographic Cluster Map of Micro-Markets across India
// High-precision calibrated projection with stylized subcontinent coastline,
// coordinate graticules, metro beacon rings, and interactive dot clusters.
// ---------------------------------------------------------------------------
export function scatterMap({ points, width = 640, height = 580, activeFilter = "all" }) {
  // Calibrated India Bounding Box
  const lonMin = 68.0, lonMax = 94.0;
  const latMin = 7.8, latMax = 33.5;
  const pad = { l: 28, r: 28, t: 26, b: 32 };

  const sx = (lon) => pad.l + ((lon - lonMin) / (lonMax - lonMin)) * (width - pad.l - pad.r);
  const sy = (lat) => height - pad.b - ((lat - latMin) / (latMax - latMin)) * (height - pad.t - pad.b);

  // Stylized India Coastline & Perimeter Control Points (lat, lon)
  const indiaPerimeter = [
    [32.8, 74.8], [32.2, 75.8], [31.1, 77.2], [30.4, 78.1], [30.0, 80.2],
    [27.4, 88.2], [27.8, 89.0], [27.0, 92.0], [27.8, 96.0], [26.8, 96.5],
    [25.0, 94.5], [23.5, 93.0], [22.0, 92.5], [21.8, 89.0],
    [21.5, 87.0], [19.8, 85.8], [17.7, 83.3], [16.0, 80.9], [13.1, 80.3],
    [10.8, 79.8], [9.2, 79.1], [8.1, 77.5],
    [8.5, 76.9], [9.9, 76.2], [12.9, 74.8], [15.5, 73.8],
    [18.9, 72.8], [20.0, 72.8], [21.1, 72.6],
    [20.7, 70.9], [21.7, 69.4], [22.5, 69.0], [23.0, 70.2],
    [23.7, 68.5], [24.5, 68.8], [24.5, 71.0],
    [26.0, 70.0], [28.0, 70.5], [29.5, 71.5], [31.5, 74.5], [32.8, 74.8]
  ];

  const indiaPathD = indiaPerimeter
    .map(([lat, lon], idx) => `${idx === 0 ? "M" : "L"} ${sx(lon).toFixed(1)} ${sy(lat).toFixed(1)}`)
    .join(" ") + " Z";

  // Graticules (Latitudes & Longitudes)
  const lats = [12, 16, 20, 24, 28, 32];
  const lons = [72, 76, 80, 84, 88];

  const graticules = [
    ...lats.map((lt) => {
      const y = sy(lt).toFixed(1);
      return `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y}" y2="${y}" stroke="var(--line)" stroke-dasharray="3 5" opacity="0.35"/>
              <text x="${pad.l + 4}" y="${y - 4}" class="graticule-lbl">${lt}°N</text>`;
    }),
    ...lons.map((ln) => {
      const x = sx(ln).toFixed(1);
      return `<line x1="${x}" x2="${x}" y1="${pad.t}" y2="${height - pad.b}" stroke="var(--line)" stroke-dasharray="3 5" opacity="0.35"/>
              <text x="${x + 4}" y="${height - pad.b + 14}" class="graticule-lbl">${ln}°E</text>`;
    }),
  ].join("");

  // Prime Metro Beacons
  const metroAnchors = [
    { name: "MUMBAI MMR", lat: 19.10, lon: 72.88 },
    { name: "DELHI NCR", lat: 28.52, lon: 77.20 },
    { name: "BENGALURU", lat: 12.95, lon: 77.65 },
    { name: "HYDERABAD", lat: 17.44, lon: 78.38 },
    { name: "PUNE", lat: 18.53, lon: 73.85 },
    { name: "CHENNAI", lat: 13.04, lon: 80.22 },
    { name: "KOLKATA", lat: 22.57, lon: 88.42 },
  ];

  const metroBeacons = metroAnchors.map((m) => {
    const cx = sx(m.lon).toFixed(1);
    const cy = sy(m.lat).toFixed(1);
    return `
      <g class="metro-anchor-beacon" data-metro="${m.name}">
        <circle cx="${cx}" cy="${cy}" r="22" class="metro-beacon-ring" fill="none" stroke="var(--accent)" stroke-width="1" opacity="0.35"/>
        <circle cx="${cx}" cy="${cy}" r="12" class="metro-beacon-inner" fill="none" stroke="var(--accent-light)" stroke-width="0.8" stroke-dasharray="2 2" opacity="0.5"/>
        <text x="${cx}" y="${cy - 14}" text-anchor="middle" class="metro-beacon-lbl">${m.name}</text>
      </g>`;
  }).join("");

  // Rank-based colour palette
  const sorted = points.map((p) => p.value).sort((a, b) => a - b);
  const rankOf = (v) => {
    let lo = 0, hi = sorted.length - 1;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (sorted[mid] < v) lo = mid + 1;
      else hi = mid;
    }
    return lo / Math.max(1, sorted.length - 1);
  };

  // Micro-market dots
  const dots = points.map((p, i) => {
    const x = sx(p.lon).toFixed(1);
    const y = sy(p.lat).toFixed(1);
    const norm = rankOf(p.value);
    const col = heatColor(norm);
    const r = (5.5 + norm * 4.2).toFixed(1);
    const tier = p.value >= 25000 ? "Trophy Luxury" : p.value >= 12000 ? "Prime Metro" : p.value >= 7500 ? "High Growth" : "Accessible";

    return `
      <g class="map-dot-group" data-city="${escapeAttr(p.city || '')}" data-locality="${escapeAttr(p.locality || '')}" data-psf="${p.value}" data-tier="${tier}" data-label="${escapeAttr(p.label)}" data-x="${x}" data-y="${y}">
        <circle class="dot-aura" cx="${x}" cy="${y}" r="${Number(r) + 4.5}" fill="${col}" opacity="0.2"/>
        <circle class="map-dot" cx="${x}" cy="${y}" r="${r}" fill="${col}" stroke="#0c1017" stroke-width="1.8"
                style="animation-delay:${(i % 30) * 20}ms" tabindex="0" role="button" aria-label="${escapeAttr(p.label)}: ₹${Math.round(p.value).toLocaleString('en-IN')}/sq.ft."/>
      </g>`;
  }).join("");

  // Top 3 Leaderboard HUD Callout
  const top = [...points].sort((a, b) => b.value - a.value).slice(0, 3);
  const trophyCallout = `
    <g class="trophy-hud-card" transform="translate(24, 22)">
      <rect width="210" height="88" rx="8" fill="rgba(14, 20, 30, 0.88)" stroke="rgba(212, 175, 55, 0.45)" stroke-width="1"/>
      <line x1="12" x2="198" y1="26" y2="26" stroke="rgba(212, 175, 55, 0.25)"/>
      <text x="12" y="19" class="trophy-hud-title">★ TOP CAPITAL VALUE MARKETS</text>
      ${top.map((t, idx) => `
        <text x="12" y="${42 + idx * 16}" class="trophy-hud-row">
          <tspan fill="#f7e29c" font-weight="700">${idx + 1}. ${escapeHtml(t.locality || t.label.split(',')[0])}</tspan>
          <tspan fill="var(--accent)" dx="4">₹${Math.round(t.value / 1000)}k</tspan>
        </text>
      `).join("")}
    </g>`;

  // Compass Rose (Top Right)
  const compass = `
    <g class="compass-rose" transform="translate(${width - 48}, 42)">
      <circle cx="0" cy="0" r="16" fill="rgba(14,20,30,0.7)" stroke="var(--line-hi)" stroke-width="1"/>
      <polygon points="0,-13 4,0 0,4 -4,0" fill="var(--accent)"/>
      <polygon points="0,13 4,0 0,-4 -4,0" fill="var(--muted)" opacity="0.6"/>
      <text x="0" y="-17" text-anchor="middle" font-size="9" font-family="var(--mono)" font-weight="bold" fill="var(--accent)">N</text>
    </g>`;

  return `
  <svg viewBox="0 0 ${width} ${height}" class="luxury-map-svg" role="img" aria-label="Micro-market spatial intelligence map of India">
    <defs>
      <linearGradient id="indiaLandGrad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="rgba(212, 175, 55, 0.08)"/>
        <stop offset="50%" stop-color="rgba(18, 24, 34, 0.65)"/>
        <stop offset="100%" stop-color="rgba(10, 15, 24, 0.9)"/>
      </linearGradient>
      <linearGradient id="indiaCoastStroke" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="rgba(212, 175, 55, 0.55)"/>
        <stop offset="40%" stop-color="rgba(96, 165, 250, 0.4)"/>
        <stop offset="100%" stop-color="rgba(212, 175, 55, 0.55)"/>
      </linearGradient>
      <filter id="hudGlow" x="-20%" y="-20%" width="140%" height="140%">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feComposite in="SourceGraphic" in2="blur" operator="over"/>
      </filter>
    </defs>
    <!-- Background Frame -->
    <rect x="0" y="0" width="${width}" height="${height}" rx="14" fill="var(--bg-2)" stroke="var(--line)"/>
    <!-- Coordinate Graticules -->
    ${graticules}
    <!-- Ocean Watermarks -->
    <text x="110" y="445" class="ocean-watermark" transform="rotate(-32 110 445)">ARABIAN SEA</text>
    <text x="505" y="445" class="ocean-watermark" transform="rotate(32 505 445)">BAY OF BENGAL</text>
    <text x="320" y="${height - 12}" class="ocean-watermark" text-anchor="middle">INDIAN OCEAN</text>
    <!-- India Stylized Landmass Silhouette -->
    <path class="india-coast-path" d="${indiaPathD}" fill="url(#indiaLandGrad)" stroke="url(#indiaCoastStroke)" stroke-width="1.6"/>
    <!-- Metropolitan Anchor Radar Beacons -->
    ${metroBeacons}
    <!-- Micro-Market Data Points -->
    ${dots}
    <!-- Top-3 Trophy HUD Card -->
    ${trophyCallout}
    <!-- Compass Rose -->
    ${compass}
  </svg>`;
}

// ---------------------------------------------------------------------------
// Stacked bar (DOM) for cost composition
// ---------------------------------------------------------------------------
export function mountStack(container, segments) {
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  container.innerHTML = segments
    .map((s) => `<span title="${s.label}: ${fmtCompact(s.value)}" style="background:${s.color}" data-w="${(s.value / total) * 100}"></span>`)
    .join("");
  requestAnimationFrame(() => requestAnimationFrame(() => {
    container.querySelectorAll("span").forEach((el) => (el.style.width = el.dataset.w + "%"));
  }));
}

// ---------------------------------------------------------------------------
// Count-up number. Respects reduced motion.
// ---------------------------------------------------------------------------
export function countUp(el, to, format, duration = 900) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !Number.isFinite(to)) {
    el.textContent = format(to);
    return;
  }
  const start = performance.now();
  const from = 0;
  const step = (now) => {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = format(from + (to - from) * eased);
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
