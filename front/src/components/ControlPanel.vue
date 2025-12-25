<template>
  <div class="panel">
    <div class="panel-head">
      <div class="date">{{ date || "加载中" }}</div>
      <div class="location">{{ region || "全国均值" }}</div>
    </div>
    <div class="main-row">
      <div class="aqi-block">
        <div class="label">AQI</div>
        <div class="aqi-value">{{ stats.aqi ?? "-" }}</div>
      </div>
      <div class="weather">
        <div class="weather-item" v-for="item in weatherList" :key="item.key">
          <div class="icon">{{ item.icon }}</div>
          <div class="val">{{ item.value }}</div>
        </div>
      </div>
    </div>
    <div class="gauge-grid">
      <div
        v-for="p in pollutantList"
        :key="p.key"
        class="gauge-card"
        :class="{ active: metric === p.key }"
        @click="$emit('select-metric', p.key)"
      >
        <div class="gauge-label">
          <span class="name">{{ p.label }}</span>
          <span class="val">{{ formatVal(stats[p.key]) }}</span>
        </div>
        <div class="gauge-track">
          <div
            class="gauge-fill"
            :style="{
              width: gaugeWidth(stats[p.key]),
              background: gaugeColor(stats[p.key]),
            }"
          ></div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { computed } from "vue";
import { computeAQI } from "../utils/dataLoader";

const props = defineProps({
  date: { type: String, default: "" },
  region: { type: String, default: "" },
  rows: { type: Array, default: () => [] },
  metric: { type: String, default: "pm25" },
  mapMode: { type: String, default: "pollution" },
});

defineEmits(["select-metric", "toggle-map-mode"]);

const pollutantList = [
  { key: "pm25", label: "PM2.5" },
  { key: "pm10", label: "PM10" },
  { key: "so2", label: "SO2" },
  { key: "no2", label: "NO2" },
  { key: "co", label: "CO" },
  { key: "o3", label: "O3" },
];

const stats = computed(() => aggregateStats(props.rows));

const weatherList = computed(() => [
  { key: "wind", icon: "W", value: stats.value.wind ? `${stats.value.wind} m/s` : "-" },
  { key: "temp", icon: "T", value: stats.value.temp ? `${stats.value.temp} ℃` : "-" },
  { key: "rh", icon: "H", value: stats.value.rh ? `${stats.value.rh} %` : "-" },
  { key: "psfc", icon: "P", value: stats.value.psfc ? `${stats.value.psfc} Pa` : "-" },
]);

function aggregateStats(rows) {
  const sums = {};
  const keys = ["pm25", "pm10", "so2", "no2", "co", "o3", "temp", "rh", "psfc", "wind"];
  keys.forEach((k) => (sums[k] = 0));
  let n = 0;
  let aqiSum = 0;
  let aqiCount = 0;
  for (const row of rows) {
    n += 1;
    const { aqi } = computeAQI(row);
    if (Number.isFinite(aqi)) {
      aqiSum += aqi;
      aqiCount += 1;
    }
    const u = Number(row?.u);
    const v = Number(row?.v);
    const wind = Number.isFinite(u) && Number.isFinite(v) ? Math.sqrt(u * u + v * v) : null;
    if (Number.isFinite(wind)) sums.wind += wind;
    for (const k of keys) {
      if (k === "wind") continue;
      const val = Number(row?.[k]);
      if (Number.isFinite(val)) {
        sums[k] += val;
      }
    }
  }
  const out = {};
  for (const k of keys) {
    out[k] = n ? Number((sums[k] / n).toFixed(k === "wind" ? 2 : 1)) : null;
  }
  out.aqi = aqiCount ? Number((aqiSum / aqiCount).toFixed(0)) : null;
  return out;
}

function gaugeWidth(v) {
  if (!Number.isFinite(v)) return "0%";
  const max = 300;
  return `${Math.min((v / max) * 100, 100)}%`;
}

function gaugeColor(v) {
  if (!Number.isFinite(v)) return "#e5e7eb";
  if (v <= 50) return "#22c55e";
  if (v <= 100) return "#a3e635";
  if (v <= 150) return "#facc15";
  if (v <= 200) return "#f97316";
  if (v <= 300) return "#ef4444";
  return "#7f1d1d";
}

function formatVal(v) {
  return Number.isFinite(v) ? v : "-";
}
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 12px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7), 0 10px 24px rgba(79, 114, 143, 0.12);
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.date {
  font-weight: 700;
  font-size: 16px;
}

.location {
  color: var(--muted);
  font-size: 14px;
}

.aqi-block {
  background: linear-gradient(135deg, rgba(47, 126, 87, 0.12), rgba(139, 191, 95, 0.12));
  border: 1px solid rgba(47, 126, 87, 0.24);
  border-radius: 12px;
  padding: 10px;
}

.aqi-block .label {
  font-size: 12px;
  color: var(--muted);
}

.aqi-block .aqi-value {
  font-size: 22px;
  font-weight: 800;
}

.main-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.weather {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px;
}

.weather-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(0, 0, 0, 0.04);
  font-size: 12px;
}

.weather-item .icon {
  font-size: 14px;
}

.gauge-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.gauge-card {
  padding: 10px;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.04);
  background: rgba(0, 0, 0, 0.01);
  cursor: pointer;
  transition: transform 0.15s ease, border-color 0.15s ease;
}

.gauge-card:hover {
  transform: translateY(-2px);
  border-color: rgba(47, 126, 87, 0.25);
}

.gauge-card.active {
  border-color: rgba(47, 126, 87, 0.45);
  box-shadow: 0 6px 16px rgba(47, 126, 87, 0.15);
}

.gauge-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: #e5e7eb;
  overflow: hidden;
}

.gauge-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.3s ease, background 0.3s ease;
}

.gauge-label {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 12px;
}

.actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.actions button {
  border: 1px solid rgba(47, 126, 87, 0.2);
  background: rgba(47, 126, 87, 0.08);
  color: #1f2937;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.actions button.active {
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  color: #0f172a;
  box-shadow: 0 8px 16px rgba(47, 126, 87, 0.2);
}
</style>
