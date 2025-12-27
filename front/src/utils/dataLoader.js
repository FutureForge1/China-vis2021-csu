/**
 * Lightweight data helpers for day-level JSON.
 * Expected structure (zero-padded preferred):
 *   /public/data/2013/MM/DD/YYYYMMDD.json
 *   /public/data/2013/index.json -> { "days": ["2013-01-01", ...] }
 */

const BASES = ["/data/2013", "/data/2013/01", "/data/2013/1"];
const HOUR_BASE = "/data/2013_hour";
const POLLUTANTS = ["pm25", "pm10", "so2", "no2", "co", "o3"];
let REGION_INDEX = null;

// AQI breakpoints per GB 3095-2012 (24h averages; O3 uses 8h sliding window).
// Units: SO2/NO2/PM10/PM2.5 in µg/m3, CO in mg/m3, O3 in µg/m3.
const AQI_BREAKPOINTS = {
  pm25: [
    { bpLo: 0, bpHi: 35, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 35, bpHi: 75, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 75, bpHi: 115, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 115, bpHi: 150, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 150, bpHi: 250, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 250, bpHi: 350, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 350, bpHi: 500, iaqiLo: 400, iaqiHi: 500 },
  ],
  pm10: [
    { bpLo: 0, bpHi: 50, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 50, bpHi: 150, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 150, bpHi: 250, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 250, bpHi: 350, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 350, bpHi: 420, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 420, bpHi: 500, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 500, bpHi: 600, iaqiLo: 400, iaqiHi: 500 },
  ],
  so2: [
    { bpLo: 0, bpHi: 50, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 50, bpHi: 150, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 150, bpHi: 475, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 475, bpHi: 800, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 800, bpHi: 1600, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 1600, bpHi: 2100, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 2100, bpHi: 2620, iaqiLo: 400, iaqiHi: 500 },
  ],
  no2: [
    { bpLo: 0, bpHi: 40, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 40, bpHi: 80, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 80, bpHi: 180, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 180, bpHi: 280, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 280, bpHi: 565, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 565, bpHi: 750, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 750, bpHi: 940, iaqiLo: 400, iaqiHi: 500 },
  ],
  co: [
    { bpLo: 0, bpHi: 2, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 2, bpHi: 4, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 4, bpHi: 14, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 14, bpHi: 24, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 24, bpHi: 36, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 36, bpHi: 48, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 48, bpHi: 60, iaqiLo: 400, iaqiHi: 500 },
  ],
  o3: [
    { bpLo: 0, bpHi: 100, iaqiLo: 0, iaqiHi: 50 },
    { bpLo: 100, bpHi: 160, iaqiLo: 50, iaqiHi: 100 },
    { bpLo: 160, bpHi: 215, iaqiLo: 100, iaqiHi: 150 },
    { bpLo: 215, bpHi: 265, iaqiLo: 150, iaqiHi: 200 },
    { bpLo: 265, bpHi: 800, iaqiLo: 200, iaqiHi: 300 },
    { bpLo: 800, bpHi: 1000, iaqiLo: 300, iaqiHi: 400 },
    { bpLo: 1000, bpHi: 1200, iaqiLo: 400, iaqiHi: 500 },
  ],
};

async function fetchJsonWithFallback(paths) {
  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      return await res.json();
    } catch (err) {
      // ignore and try next
    }
  }
  throw new Error(`All paths failed: ${paths.join(", ")}`);
}

export async function loadIndex() {
  try {
    return await fetchJsonWithFallback([
      `${BASES[0]}/index.json`,
      `${BASES[1]}/index.json`,
      `${BASES[2]}/index.json`,
    ]);
  } catch (err) {
    console.warn("Index load failed, using fallback day only:", err);
    return { days: ["2013-01-01"] };
  }
}

function normalizeRegionName(name) {
  if (!name) return "";
  return String(name).split("|").pop().trim();
}

export async function loadRegionIndex() {
  if (REGION_INDEX) return REGION_INDEX;
  try {
    const res = await fetch("/region.json");
    const list = await res.json();
    const map = new Map();
    for (const item of list) {
      const lon = Number(item.longitude ?? item.lon);
      const lat = Number(item.latitude ?? item.lat);
      if (!Number.isFinite(lon) || !Number.isFinite(lat)) continue;
      const keys = [
        normalizeRegionName(item.county),
        normalizeRegionName(item.city),
        normalizeRegionName(item.province),
      ].filter(Boolean);
      for (const k of keys) {
        if (!k) continue;
        if (!map.has(k)) {
          map.set(k, { lon, lat });
        }
      }
    }
    REGION_INDEX = map;
    return map;
  } catch (err) {
    console.warn("loadRegionIndex failed", err);
    REGION_INDEX = new Map();
    return REGION_INDEX;
  }
}

export function rowsToScatter(rows, metricKey, regionIndex) {
  if (!regionIndex) return [];
  const out = [];
  for (const row of rows) {
    const name = normalizeRegionName(row.city) || normalizeRegionName(row.county) || normalizeRegionName(row.province);
    const coord = name ? regionIndex.get(name) : null;
    let val = Number(row?.[metricKey]);
    if (metricKey === "wind") {
      const u = Number(row?.u);
      const v = Number(row?.v);
      val = Number.isFinite(u) && Number.isFinite(v) ? Math.sqrt(u * u + v * v) : NaN;
    }
    if (!coord || !Number.isFinite(val)) continue;
    out.push({ name, value: val, coord: [coord.lon, coord.lat] });
  }
  return out;
}

export function buildWindVectors(rows, regionIndex, scale = 0.3) {
  if (!regionIndex) return [];
  const lines = [];
  for (const row of rows) {
    const name = normalizeRegionName(row.city) || normalizeRegionName(row.county) || normalizeRegionName(row.province);
    const coord = name ? regionIndex.get(name) : null;
    const u = Number(row?.u);
    const v = Number(row?.v);
    if (!coord || !Number.isFinite(u) || !Number.isFinite(v)) continue;
    const speed = Math.sqrt(u * u + v * v);
    const dx = u * scale;
    const dy = v * scale;
    lines.push({
      name,
      speed,
      coords: [
        [coord.lon, coord.lat],
        [coord.lon + dx, coord.lat + dy],
      ],
    });
  }
  return lines;
}

// Densified stream-like lines for a "flow" layer (adds jittered seeds to thicken the effect).
export function buildWindFlow(rows, regionIndex, scale = 0.3, density = 3) {
  if (!regionIndex) return [];
  const flow = [];
  for (const row of rows) {
    const baseName = normalizeRegionName(row.city) || normalizeRegionName(row.county) || normalizeRegionName(row.province);
    const coord = baseName ? regionIndex.get(baseName) : null;
    const u = Number(row?.u);
    const v = Number(row?.v);
    if (!coord || !Number.isFinite(u) || !Number.isFinite(v)) continue;
    const speed = Math.sqrt(u * u + v * v);
    for (let i = 0; i < Math.max(1, density); i++) {
      const jitter = 0.2;
      const ox = (Math.random() - 0.5) * jitter;
      const oy = (Math.random() - 0.5) * jitter;
      const dx = u * scale;
      const dy = v * scale;
      flow.push({
        name: baseName,
        speed,
        coords: [
          [coord.lon + ox, coord.lat + oy],
          [coord.lon + ox + dx, coord.lat + oy + dy],
        ],
      });
    }
  }
  return flow;
}

export async function loadOneDay(dateStr) {
  const clean = dateStr.replace(/-/g, "");
  const year = clean.slice(0, 4);
  const monthPadded = clean.slice(4, 6);
  const monthRaw = String(parseInt(monthPadded, 10));
  const day = clean.slice(6, 8);

  const paths = [];
  // Base: /data/2013 -> append month/day
  paths.push(`${BASES[0]}/${monthPadded}/${day}/${clean}.json`);
  paths.push(`${BASES[0]}/${monthRaw}/${day}/${clean}.json`);
  // Base with month embedded
  paths.push(`${BASES[1]}/${day}/${clean}.json`);
  paths.push(`${BASES[2]}/${day}/${clean}.json`);

  try {
    return await fetchJsonWithFallback(paths);
  } catch (err) {
    console.warn(`Day data missing for ${dateStr}:`, err);
    return [];
  }
}

export function classifyLevels(rows, field) {
  const buckets = [
    { name: "优", min: 0, max: 35 },
    { name: "良", min: 35, max: 75 },
    { name: "轻度", min: 75, max: 115 },
    { name: "中度", min: 115, max: 150 },
    { name: "重度", min: 150, max: 250 },
    { name: "严重", min: 250, max: Infinity },
  ];

  const counts = buckets.map((b) => ({ level: b.name, value: 0 }));
  for (const row of rows) {
    const v = Number(row[field] ?? 0);
    const bucket = buckets.find((b) => v >= b.min && v < b.max) || buckets[0];
    const target = counts.find((c) => c.level === bucket.name);
    target.value += 1;
  }
  return counts;
}

export function computeRadialVector(rows) {
  const metrics = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const sums = {};
  const counts = {};
  for (const m of metrics) {
    sums[m] = 0;
    counts[m] = 0;
  }
  for (const row of rows) {
    for (const m of metrics) {
      const val = Number(row[m] ?? 0);
      if (!Number.isNaN(val)) {
        sums[m] += val;
        counts[m] += 1;
      }
    }
  }
  return metrics.map((m) => ({
    indicator: m.toUpperCase(),
    value: counts[m] ? sums[m] / counts[m] : 0,
  }));
}

export function computeTrendSeries(dayEntries, field) {
  // dayEntries: [{ date, data }]
  return dayEntries.map((entry) => ({
    date: entry.date,
    value: averageMetric(entry.data, field),
  }));
}

function averageMetric(rows, field) {
  let sum = 0;
  let count = 0;
  for (const row of rows) {
    const v = Number(row[field] ?? 0);
    if (!Number.isNaN(v)) {
      sum += v;
      count += 1;
    }
  }
  return count ? sum / count : 0;
}

export function computeLevelTimeline(dayEntries, field) {
  const buckets = [
    { name: "优", min: 0, max: 35 },
    { name: "良", min: 35, max: 75 },
    { name: "轻度", min: 75, max: 115 },
    { name: "中度", min: 115, max: 150 },
    { name: "重度", min: 150, max: 250 },
    { name: "严重", min: 250, max: Infinity },
  ];

  const dates = [];
  const series = buckets.map((b) => ({ name: b.name, data: [] }));

  for (const entry of dayEntries) {
    dates.push(entry.date);
    const counts = buckets.map(() => 0);
    for (const row of entry.data) {
      const v = Number(row[field] ?? 0);
      if (Number.isNaN(v)) continue;
      const idx = buckets.findIndex((b) => v >= b.min && v < b.max);
      if (idx >= 0) counts[idx] += 1;
    }
    counts.forEach((c, i) => {
      series[i].data.push(c);
    });
  }

  return { dates, series };
}

export function computeCorrMatrix(dayEntries, pollutants, meteor) {
  const results = [];
  for (const p of pollutants) {
    for (const m of meteor) {
      const xs = [];
      const ys = [];
      for (const entry of dayEntries) {
        for (const row of entry.data) {
          const xv = Number(row[p]);
          const yv = Number(row[m]);
          if (!Number.isFinite(xv) || !Number.isFinite(yv)) continue;
          xs.push(xv);
          ys.push(yv);
        }
      }
      results.push({
        pollutant: p.toUpperCase(),
        meteor: m.toUpperCase(),
        value: pearson(xs, ys),
      });
    }
  }
  return results;
}

function pearson(xs, ys) {
  const n = xs.length;
  if (n === 0) return 0;
  let sumX = 0,
    sumY = 0,
    sumXY = 0,
    sumX2 = 0,
    sumY2 = 0;
  for (let i = 0; i < n; i++) {
    const x = xs[i];
    const y = ys[i];
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumX2 += x * x;
    sumY2 += y * y;
  }
  const numerator = n * sumXY - sumX * sumY;
  const denom = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  if (!Number.isFinite(denom) || denom === 0) return 0;
  return Number((numerator / denom).toFixed(2));
}

function locateBreakpoint(value, pollutant) {
  const v = Number(value);
  const table = AQI_BREAKPOINTS[pollutant];
  if (!table || Number.isNaN(v)) return null;
  for (const seg of table) {
    if (v <= seg.bpHi) return seg;
  }
  return table[table.length - 1];
}

export function computeIAQI(value, pollutant) {
  const seg = locateBreakpoint(value, pollutant);
  if (!seg) return 0;
  const { bpLo, bpHi, iaqiLo, iaqiHi } = seg;
  const v = Number(value);
  const iaqi = ((iaqiHi - iaqiLo) * (v - bpLo)) / (bpHi - bpLo) + iaqiLo;
  // clamp to the segment upper bound to avoid overshoot when exceeding table
  const capped = Math.min(iaqi, iaqiHi);
  return Number(capped.toFixed(1));
}

export function computeAQI(row) {
  const metrics = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const iaqis = metrics.map((m) => ({
    pollutant: m,
    iaqi: computeIAQI(row?.[m], m),
  }));
  const primary = iaqis.reduce(
    (acc, cur) => (cur.iaqi > (acc?.iaqi ?? -Infinity) ? cur : acc),
    null
  );
  return {
    aqi: primary ? primary.iaqi : 0,
    primaryPollutant: primary ? primary.pollutant : null,
    iaqis,
  };
}

// Convenience: attach AQI/IAQI to each row [{...data, aqi, primaryPollutant, iaqis}]
export function attachAQI(rows) {
  return rows.map((row) => {
    const { aqi, primaryPollutant, iaqis } = computeAQI(row);
    return { ...row, aqi, primaryPollutant, iaqis };
  });
}

// Average AQI by region (default province) with primary pollutant vote.
export function computeAQIRanking(rows, field = "province", topN = 15) {
  const groups = new Map();
  for (const row of rows) {
    const key = row?.[field] || row?.province || row?.city;
    if (!key) continue;
    const { aqi, primaryPollutant } = computeAQI(row);
    if (!Number.isFinite(aqi)) continue;
    if (!groups.has(key)) {
      groups.set(key, {
        sumAQI: 0,
        count: 0,
        primaryCounts: new Map(),
      });
    }
    const g = groups.get(key);
    g.sumAQI += aqi;
    g.count += 1;
    if (primaryPollutant) {
      g.primaryCounts.set(primaryPollutant, (g.primaryCounts.get(primaryPollutant) || 0) + 1);
    }
  }

  const items = [];
  for (const [name, g] of groups.entries()) {
    const avg = g.count ? g.sumAQI / g.count : 0;
    let primary = null;
    let best = -Infinity;
    for (const [p, c] of g.primaryCounts.entries()) {
      if (c > best) {
        best = c;
        primary = p;
      }
    }
    items.push({ name, aqi: Number(avg.toFixed(1)), primaryPollutant: primary });
  }

  return items.sort((a, b) => b.aqi - a.aqi).slice(0, topN);
}

// Prepare parallel coordinates data: averages by region.
export function buildParallelData(rows, field = "province", topN = 30, provinceFilter = null) {
  const metrics = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const groups = new Map();
  for (const row of rows) {
    if (provinceFilter && row?.province !== provinceFilter) continue;
    const key = row?.[field] || row?.province || row?.city;
    if (!key) continue;
    const { aqi, primaryPollutant } = computeAQI(row);
    if (!groups.has(key)) {
      groups.set(key, {
        sumAQI: 0,
        countAQI: 0,
        sums: Object.fromEntries(metrics.map((m) => [m, 0])),
        counts: Object.fromEntries(metrics.map((m) => [m, 0])),
        primaryCounts: new Map(),
      });
    }
    const g = groups.get(key);
    if (Number.isFinite(aqi)) {
      g.sumAQI += aqi;
      g.countAQI += 1;
    }
    if (primaryPollutant) {
      g.primaryCounts.set(primaryPollutant, (g.primaryCounts.get(primaryPollutant) || 0) + 1);
    }
    for (const m of metrics) {
      const v = Number(row?.[m]);
      if (Number.isFinite(v)) {
        g.sums[m] += v;
        g.counts[m] += 1;
      }
    }
  }

  const rowsOut = [];
  for (const [name, g] of groups.entries()) {
    const aqiAvg = g.countAQI ? g.sumAQI / g.countAQI : 0;
    let primary = null;
    let best = -Infinity;
    for (const [p, c] of g.primaryCounts.entries()) {
      if (c > best) {
        best = c;
        primary = p;
      }
    }
    const values = [aqiAvg];
    for (const m of metrics) {
      const avg = g.counts[m] ? g.sums[m] / g.counts[m] : 0;
      values.push(avg);
    }
    rowsOut.push({
      name,
      values: values.map((v) => Number(v.toFixed(2))),
      primaryPollutant: primary,
    });
  }

  return rowsOut.sort((a, b) => b.values[0] - a.values[0]).slice(0, topN);
}

function classifyPollutionType(shares) {
  const entries = Object.entries(shares).sort((a, b) => b[1] - a[1]);
  const [primary, ratio] = entries[0] || [null, 0];
  if (!primary) return { type: "未知", primary };
  if (ratio < 0.3) return { type: "标准型", primary };
  if (primary === "o3") return { type: "偏二次型", primary };
  if (primary === "so2") return { type: "偏燃煤型", primary };
  if (primary === "no2") return { type: "偏交通型", primary };
  if (primary === "co") return { type: "偏燃烧型", primary };
  if (primary === "pm25" || primary === "pm10") return { type: "偏颗粒物型", primary };
  return { type: "标准型", primary };
}

function computeShares(row) {
  const values = {};
  let total = 0;
  for (const m of POLLUTANTS) {
    const v = Number(row?.[m]);
    values[m] = Number.isFinite(v) && v > 0 ? v : 0;
    total += values[m];
  }
  const shares = {};
  for (const m of POLLUTANTS) {
    shares[m] = total > 0 ? values[m] / total : 0;
  }
  return shares;
}

export function computeTypeByRegion(rows, field = "city") {
  const groups = new Map();
  for (const row of rows) {
    const key = row?.[field] || row?.city || row?.province;
    if (!key) continue;
    if (!groups.has(key)) {
      groups.set(key, { sums: Object.fromEntries(POLLUTANTS.map((m) => [m, 0])), count: 0 });
    }
    const g = groups.get(key);
    for (const m of POLLUTANTS) {
      const v = Number(row?.[m]);
      if (Number.isFinite(v) && v > 0) {
        g.sums[m] += v;
      }
    }
    g.count += 1;
  }

  const result = [];
  for (const [name, g] of groups.entries()) {
    const avg = Object.fromEntries(
      POLLUTANTS.map((m) => [m, g.count ? g.sums[m] / g.count : 0])
    );
    const shares = computeShares(avg);
    const { type, primary } = classifyPollutionType(shares);
    result.push({ name, type, primary, shares });
  }
  return result;
}

export function buildTypeScatter(rows, field = "city") {
  const typed = computeTypeByRegion(rows, field);
  return typed.map((item) => {
    const particles = (item.shares.pm25 || 0) + (item.shares.pm10 || 0);
    const secondary = item.shares.o3 || 0;
    const coal = item.shares.so2 || 0;
    return {
      name: item.name,
      type: item.type,
      primary: item.primary,
      x: Number(particles.toFixed(3)),
      y: Number(secondary.toFixed(3)),
      size: Number((coal + secondary + particles).toFixed(3)),
    };
  });
}

export function computeTypeTimeline(dayEntries, field = "city", provinceFilter = null) {
  const dates = [];
  const typeSet = new Set();
  const seriesMap = new Map();

  for (const entry of dayEntries) {
    dates.push(entry.date);
    const data = provinceFilter
      ? entry.data.filter((r) => (r?.province || r?.city) === provinceFilter)
      : entry.data;
    const typed = computeTypeByRegion(data, field);
    const counts = new Map();
    for (const t of typed) {
      counts.set(t.type, (counts.get(t.type) || 0) + 1);
      typeSet.add(t.type);
    }
    for (const type of typeSet) {
      if (!seriesMap.has(type)) {
        seriesMap.set(type, []);
      }
    }
    for (const type of typeSet) {
      seriesMap.get(type).push(counts.get(type) || 0);
    }
  }

  const series = Array.from(seriesMap.entries()).map(([name, data]) => ({
    name,
    data,
  }));

  return { dates, series };
}

function parseDateParts(dateStr) {
  const parts = String(dateStr || "").split("-");
  if (parts.length !== 3) return null;
  const [y, m, d] = parts.map((p) => Number(p));
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return null;
  return { year: y, month: m, day: d };
}

function aqiToLevel(aqi) {
  if (aqi <= 50) return "优";
  if (aqi <= 100) return "良";
  if (aqi <= 150) return "轻度";
  if (aqi <= 200) return "中度";
  if (aqi <= 300) return "重度";
  return "严重";
}

export function computeYearlyRadial(dayEntries) {
  const yearly = new Map();
  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts) continue;
    const y = parts.year;
    if (!yearly.has(y)) {
      yearly.set(y, {
        sums: Object.fromEntries(POLLUTANTS.map((m) => [m, 0])),
        counts: Object.fromEntries(POLLUTANTS.map((m) => [m, 0])),
      });
    }
    const bucket = yearly.get(y);
    for (const row of entry.data) {
      for (const m of POLLUTANTS) {
        const v = Number(row?.[m]);
        if (Number.isFinite(v) && v > 0) {
          bucket.sums[m] += v;
          bucket.counts[m] += 1;
        }
      }
    }
  }

  const out = [];
  const years = Array.from(yearly.keys()).sort((a, b) => a - b);
  for (const y of years) {
    const bucket = yearly.get(y);
    const data = POLLUTANTS.map((m) => ({
      indicator: m.toUpperCase(),
      value: bucket.counts[m] ? Number((bucket.sums[m] / bucket.counts[m]).toFixed(2)) : 0,
    }));
    out.push({ name: String(y), data });
  }
  return out;
}

export function computeAQIRain(dayEntries, monthFilter = 1) {
  const levels = ["优", "良", "轻度", "中度", "重度", "严重"];
  const yearsSet = new Set();
  const countsMap = new Map(); // year -> Map(level -> count)

  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts || parts.month !== monthFilter) continue;
    const year = parts.year;
    yearsSet.add(year);
    if (!countsMap.has(year)) {
      countsMap.set(year, new Map(levels.map((l) => [l, 0])));
    }
    const levelCounts = countsMap.get(year);
    for (const row of entry.data) {
      const { aqi } = computeAQI(row);
      const level = aqiToLevel(aqi);
      levelCounts.set(level, (levelCounts.get(level) || 0) + 1);
    }
  }

  const years = Array.from(yearsSet).sort((a, b) => a - b);
  const data = [];
  years.forEach((y, yi) => {
    const levelCounts = countsMap.get(y) || new Map();
    levels.forEach((lv, li) => {
      data.push([li, yi, levelCounts.get(lv) || 0]);
    });
  });

  return { years, levels, data };
}

export function computeAQICompareLines(dayEntries, monthFilter = 1) {
  const maxDay = 31;
  const yearsMap = new Map(); // year -> array length 31

  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts || parts.month !== monthFilter) continue;
    const year = parts.year;
    if (!yearsMap.has(year)) {
      yearsMap.set(year, new Array(maxDay).fill(null));
    }
    const arr = yearsMap.get(year);
    const dayIdx = Math.min(Math.max(parts.day, 1), maxDay) - 1;
    let sum = 0;
    let cnt = 0;
    for (const row of entry.data) {
      const { aqi } = computeAQI(row);
      if (Number.isFinite(aqi)) {
        sum += aqi;
        cnt += 1;
      }
    }
    arr[dayIdx] = cnt ? Number((sum / cnt).toFixed(1)) : null;
  }

  const years = Array.from(yearsMap.keys()).sort((a, b) => a - b);
  const series = years.map((y) => ({
    name: String(y),
    data: yearsMap.get(y),
  }));
  const days = Array.from({ length: maxDay }, (_, i) => String(i + 1));
  return { days, series };
}

export function computeMonthlyRing(dayEntries) {
  const monthly = new Map();
  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts) continue;
    const key = parts.month;
    if (!monthly.has(key)) {
      monthly.set(key, {
        sums: Object.fromEntries(POLLUTANTS.map((m) => [m, 0])),
        counts: Object.fromEntries(POLLUTANTS.map((m) => [m, 0])),
        aqiSum: 0,
        aqiCount: 0,
      });
    }
    const bucket = monthly.get(key);
    for (const row of entry.data) {
      const { aqi } = computeAQI(row);
      if (Number.isFinite(aqi)) {
        bucket.aqiSum += aqi;
        bucket.aqiCount += 1;
      }
      for (const m of POLLUTANTS) {
        const v = Number(row?.[m]);
        if (Number.isFinite(v) && v > 0) {
          bucket.sums[m] += v;
          bucket.counts[m] += 1;
        }
      }
    }
  }

  const out = [];
  const months = Array.from(monthly.keys()).sort((a, b) => a - b);
  for (const m of months) {
    const bucket = monthly.get(m);
    const data = POLLUTANTS.map((p) => ({
      indicator: p.toUpperCase(),
      value: bucket.counts[p] ? Number((bucket.sums[p] / bucket.counts[p]).toFixed(2)) : 0,
    }));
    const avgAQI = bucket.aqiCount ? Number((bucket.aqiSum / bucket.aqiCount).toFixed(1)) : 0;
    out.push({ name: `${m}月`, data, aqi: avgAQI, level: aqiToLevel(avgAQI) });
  }
  return out;
}

// Province-level monthly pollutant grid for ring view.
export function computeMonthlyRingGrid(dayEntries, pollutant = "pm25", orderNames = [], topN = 12) {
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  const buckets = new Map();

  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts) continue;
    const month = parts.month;
    for (const row of entry.data) {
      const key = row?.province || row?.city;
      if (!key) continue;
      if (!buckets.has(key)) {
        buckets.set(key, {
          months: months.map(() => ({
            sum: 0,
            count: 0,
            aqiSum: 0,
            aqiCount: 0,
          })),
        });
      }
      const bucket = buckets.get(key).months[month - 1];
      const val = Number(row?.[pollutant]);
      if (Number.isFinite(val)) {
        bucket.sum += val;
        bucket.count += 1;
      }
      const { aqi } = computeAQI(row);
      if (Number.isFinite(aqi)) {
        bucket.aqiSum += aqi;
        bucket.aqiCount += 1;
      }
    }
  }

  // Convert to averages
  const result = [];
  for (const [name, data] of buckets.entries()) {
    const monthsData = data.months.map((m) => ({
      value: m.count ? m.sum / m.count : 0,
      aqi: m.aqiCount ? m.aqiSum / m.aqiCount : 0,
    }));
    const avgAqi =
      monthsData.reduce((s, d) => s + (Number.isFinite(d.aqi) ? d.aqi : 0), 0) / monthsData.length;
    result.push({ name, months: monthsData, avgAqi });
  }

  // Sort by orderNames first, otherwise by avgAqi desc
  const orderMap = new Map(orderNames.map((n, i) => [n, i]));
  result.sort((a, b) => {
    const ia = orderMap.has(a.name) ? orderMap.get(a.name) : Infinity;
    const ib = orderMap.has(b.name) ? orderMap.get(b.name) : Infinity;
    if (ia !== ib) return ia - ib;
    return (b.avgAqi || 0) - (a.avgAqi || 0);
  });

  const trimmed = result.slice(0, topN);
  const globalMax = Math.max(
    1,
    ...trimmed.flatMap((r) => r.months.map((m) => Number(m.value) || 0))
  );

  return trimmed.map((r) => ({
    name: r.name,
    months: r.months.map((m, idx) => {
      const segments = Math.max(
        3,
        Math.min(24, Math.round(((Number(m.value) || 0) / globalMax) * 20))
      );
      return {
        month: months[idx],
        value: Number((m.value || 0).toFixed(2)),
        aqi: Number((m.aqi || 0).toFixed(1)),
        segments,
      };
    }),
  }));
}

// Per-city monthly stats for current month.
export function computeCityMonthStats(dayEntries, cityName, monthFilter) {
  const metrics = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const agg = new Map(); // metric -> {sum,count,min,max}
  const target = normalizeRegionName(cityName);
  for (const m of metrics) {
    agg.set(m, { sum: 0, count: 0, min: Infinity, max: -Infinity });
  }

  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts || (monthFilter && parts.month !== monthFilter)) continue;
    for (const row of entry.data) {
      const name = normalizeRegionName(row.city) || normalizeRegionName(row.province);
      if (!name) continue;
      if (target && name !== target) continue;
      for (const m of metrics) {
        const v = Number(row?.[m]);
        if (!Number.isFinite(v)) continue;
        const a = agg.get(m);
        a.sum += v;
        a.count += 1;
        a.min = Math.min(a.min, v);
        a.max = Math.max(a.max, v);
      }
    }
  }

  const out = {};
  for (const m of metrics) {
    const a = agg.get(m);
    if (!a.count) {
      out[m] = { avg: 0, min: 0, max: 0 };
    } else {
      out[m] = {
        avg: a.sum / a.count,
        min: a.min,
        max: a.max,
      };
    }
  }
  return out;
}

// City type trajectory within a month (per city, per day -> type index).
export function computeCityTypeTrajectory(dayEntries, provinceFilter = null, monthFilter = null) {
  const typeOrder = [
    "偏燃烧型",
    "偏钢铁型",
    "偏机动车型",
    "其他型",
    "标准型",
    "偏氮氧化型",
    "偏二次型",
    "偏沙尘型",
  ];
  const typeIndex = new Map(typeOrder.map((t, i) => [t, i]));
  const dates = [];
  const perCity = new Map(); // city -> values[]

  for (const entry of dayEntries) {
    const parts = parseDateParts(entry.date);
    if (!parts || (monthFilter && parts.month !== monthFilter)) continue;
    dates.push(entry.date);
    const typed = computeTypeByRegion(
      provinceFilter
        ? entry.data.filter((r) => (r?.province || r?.city) === provinceFilter)
        : entry.data,
      "city"
    );
    const map = new Map(typed.map((t) => [normalizeRegionName(t.name), t.type]));
    // ensure all seen cities align lengths
    for (const name of map.keys()) {
      if (!perCity.has(name)) perCity.set(name, []);
    }
    for (const [name, series] of perCity.entries()) {
      const type = map.get(name);
      const idx = typeIndex.has(type) ? typeIndex.get(type) : typeIndex.size;
      series.push(idx ?? null);
    }
  }

  const series = Array.from(perCity.entries()).map(([name, data]) => ({
    name,
    data,
  }));
  return { dates, typeOrder, series };
}

export function buildFeatureScatterTSNE(rows, field = "city") {
  const typed = computeTypeByRegion(rows, field);
  return typed.map((item) => {
    const particles = (item.shares.pm25 || 0) + (item.shares.pm10 || 0);
    const secondary = item.shares.o3 || 0;
    const combustion = (item.shares.co || 0) + (item.shares.so2 || 0);
    return {
      name: item.name,
      type: item.type,
      primary: item.primary,
      x: Number((particles - secondary).toFixed(3)),
      y: Number((secondary - combustion).toFixed(3)),
      cluster: item.type,
    };
  });
}

export function computeWindRose(rows) {
  // Approximate eight-direction mean speed from u/v if present.
  const dirs = [
    { name: "E", u: 1, v: 0 },
    { name: "NE", u: 1, v: -1 },
    { name: "N", u: 0, v: -1 },
    { name: "NW", u: -1, v: -1 },
    { name: "W", u: -1, v: 0 },
    { name: "SW", u: -1, v: 1 },
    { name: "S", u: 0, v: 1 },
    { name: "SE", u: 1, v: 1 },
  ];
  const sums = dirs.map(() => 0);
  const counts = dirs.map(() => 0);
  for (const row of rows) {
    const u = Number(row?.u);
    const v = Number(row?.v);
    if (!Number.isFinite(u) || !Number.isFinite(v)) continue;
    const angle = Math.atan2(v, u); // radians
    const deg = ((angle * 180) / Math.PI + 360) % 360;
    const speed = Math.sqrt(u * u + v * v);
    const idx = Math.round(deg / 45) % 8;
    sums[idx] += speed;
    counts[idx] += 1;
  }
  return dirs.map((d, i) => ({
    dir: d.name,
    value: counts[i] ? Number((sums[i] / counts[i]).toFixed(2)) : 0,
  }));
}
