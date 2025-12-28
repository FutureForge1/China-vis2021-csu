#!/usr/bin/env node
// scripts/compare-map-names.js
// Usage: node scripts/compare-map-names.js
const fs = require("fs");
const path = require("path");

function normalizeProvince(name) {
  if (!name) return "";
  let n = String(name).split("|").pop().trim();
  const direct = {
    北京: "北京市",
    天津: "天津市",
    上海: "上海市",
    重庆: "重庆市",
    "内蒙古自治区": "内蒙古自治区",
    内蒙古: "内蒙古自治区",
    "广西壮族自治区": "广西壮族自治区",
    广西: "广西壮族自治区",
    "新疆维吾尔自治区": "新疆维吾尔自治区",
    新疆: "新疆维吾尔自治区",
    "宁夏回族自治区": "宁夏回族自治区",
    宁夏: "宁夏回族自治区",
    "西藏自治区": "西藏自治区",
    西藏: "西藏自治区",
    "香港特别行政区": "香港特别行政区",
    香港: "香港特别行政区",
    "澳门特别行政区": "澳门特别行政区",
    澳门: "澳门特别行政区",
    "中国香港": "香港特别行政区",
    "中國香港": "香港特别行政区",
    "中国澳门": "澳门特别行政区",
    "中國澳門": "澳门特别行政区",
    "台湾省": "台湾省",
    台湾: "台湾省",
    "黑龙江省": "黑龙江省",
    "黑龍江省": "黑龙江省",
  };
  if (direct[n]) return direct[n];
  n = n.replace(/省|市|自治区|壮族自治区|维吾尔自治区|回族自治区|特别行政区/g, "").trim();
  if (!n) return "";
  return `${n}省`;
}

function normalizeRegionName(name) {
  if (!name) return "";
  return String(name).split("|").pop().trim();
}

function readJsonSafe(p) {
  try {
    const raw = fs.readFileSync(p, "utf8");
    return JSON.parse(raw);
  } catch (e) {
    console.warn("Failed to read/parse", p, e.message);
    return null;
  }
}

function walkDir(dir, ext = ".json") {
  const out = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      out.push(...walkDir(full, ext));
    } else if (e.isFile() && e.name.endsWith(ext)) {
      out.push(full);
    }
  }
  return out;
}

(function main() {
  const root = process.cwd();
  const chinaPath = path.join(root, "front", "public", "china.json");
  const regionPath = path.join(root, "front", "public", "region.json");
  const dataDir = path.join(root, "front", "public", "data", "2013");

  const report = { timestamp: new Date().toISOString(), missingProvinces: [], missingCoordsSamples: [] };

  const china = readJsonSafe(chinaPath);
  if (!china || !china.features) {
    console.error("china.json not found or invalid at", chinaPath);
  }
  const chinaNames = new Set((china && china.features ? china.features.map(f => (f && f.properties && f.properties.name) ? f.properties.name : null).filter(Boolean) : []));

  const regionList = readJsonSafe(regionPath) || [];
  const regionKeys = new Set();
  for (const item of regionList) {
    const keys = [
      normalizeRegionName(item.county),
      normalizeRegionName(item.city),
      normalizeRegionName(item.province),
    ].filter(Boolean);
    for (const k of keys) regionKeys.add(k);
  }

  // Walk data files and collect names
  const dataFiles = fs.existsSync(dataDir) ? walkDir(dataDir, ".json") : [];
  const uniqueProvinceRaw = new Set();
  const uniqueScatterNamesRaw = new Set();
  console.log(`Found ${dataFiles.length} day JSON files under ${dataDir}`);

  for (const f of dataFiles) {
    try {
      const json = readJsonSafe(f);
      if (!Array.isArray(json)) continue;
      for (const row of json) {
        if (!row || typeof row !== "object") continue;
        if (row.province) uniqueProvinceRaw.add(row.province);
        // scatter uses city | county | province fallback
        const city = normalizeRegionName(row.city) || normalizeRegionName(row.county) || normalizeRegionName(row.province);
        if (city) uniqueScatterNamesRaw.add(city);
      }
    } catch (e) {
      // ignore
    }
  }

  // Normalize province names as App.vue does
  const normalizedProvinces = new Set();
  for (const p of uniqueProvinceRaw) {
    const n = normalizeProvince(p);
    if (n) normalizedProvinces.add(n);
  }

  // Find which normalized provinces are NOT present in china.json feature names
  const missingProvinces = [];
  for (const np of normalizedProvinces) {
    if (!chinaNames.has(np)) missingProvinces.push(np);
  }

  // For scatter: check which scatter keys are missing in region.json keys
  const missingCoords = [];
  const samplesLimit = 200;
  for (const name of uniqueScatterNamesRaw) {
    if (!regionKeys.has(name)) {
      if (missingCoords.length < samplesLimit) missingCoords.push(name);
    }
  }

  report.totalProvincesSeen = normalizedProvinces.size;
  report.missingProvincesCount = missingProvinces.length;
  report.missingProvinces = missingProvinces.slice(0, 200);
  report.totalScatterNames = uniqueScatterNamesRaw.size;
  report.missingCoordsCount = missingCoords.length;
  report.missingCoordsSamples = missingCoords.slice(0, samplesLimit);
  report.chinaSample = Array.from(chinaNames).slice(0, 50);

  const outPath = path.join(root, "scripts", "compare-map-names-report.json");
  try {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, JSON.stringify(report, null, 2), "utf8");
    console.log("Report written to", outPath);
  } catch (e) {
    console.error("Failed to write report:", e.message);
  }

  console.log("Summary:");
  console.log(" - provinces seen (normalized):", report.totalProvincesSeen);
  console.log(" - missing provinces vs china.json:", report.missingProvincesCount);
  if (report.missingProvinces.length) {
    console.log("   examples:", report.missingProvinces.slice(0, 40).join(", "));
  }
  console.log(" - unique scatter names:", report.totalScatterNames);
  console.log(" - missing scatter coords (sample):", Math.min(report.missingCoordsCount, samplesLimit), "/", report.missingCoordsCount);
  if (report.missingCoordsSamples.length) {
    console.log("   examples:", report.missingCoordsSamples.slice(0, 40).join(", "));
  }

  console.log("\nIf you want, I can (A) add this script into the repository and run it here, or (B) run it locally if you run the command above and share the report. Which do you prefer?");
})();