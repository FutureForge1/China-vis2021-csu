<template>
  <div class="panel">
    <div class="panel-head">
      <div class="date">{{ date || "LOADING" }}</div>
      <div class="location-group">
        <div class="location">{{ region || "NATIONAL MEAN" }}</div>
        <button 
          v-if="showReset" 
          class="reset-btn" 
          @click="$emit('reset-region')"
          title="RESET TO DEFAULT"
        >
          RESET
        </button>
      </div>
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

defineEmits(["select-metric", "toggle-map-mode","reset-region"]);

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

// 【新增】判断是否显示重置按钮
const showReset = computed(() => {
  // Show reset if region is not default
  return props.region && props.region !== 'NATIONWIDE' && props.region !== 'NATIONAL MEAN' && props.region !== '全国';
});

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
    
    // 兼容月度/年度数据字段 (u_mean/u_yearly_mean, v_mean/v_yearly_mean)
    const u = Number(row?.u ?? row?.u_mean ?? row?.u_yearly_mean);
    const v = Number(row?.v ?? row?.v_mean ?? row?.v_yearly_mean);
    const wind = Number.isFinite(u) && Number.isFinite(v) ? Math.sqrt(u * u + v * v) : null;
    if (Number.isFinite(wind)) sums.wind += wind;
    
    for (const k of keys) {
      if (k === "wind") continue;
      // 兼容月度/年度数据字段 (例如 pm25_mean, pm25_yearly_mean)
      const val = Number(row?.[k] ?? row?.[`${k}_mean`] ?? row?.[`${k}_yearly_mean`]);
      // Also check if val is 0, sometimes explicit 0 is valid, but missing data might be null.
      // Number(null) is 0, which is bad for pollution averages.
      // Use explicit check
      const rawVal = row?.[k] ?? row?.[`${k}_mean`] ?? row?.[`${k}_yearly_mean`];
      if (rawVal !== undefined && rawVal !== null && !Number.isNaN(Number(rawVal))) {
        sums[k] += Number(rawVal);
      }
    }
  }
  const out = {};
  for (const k of keys) {
    // Avoid division by zero
    out[k] = n ? Number((sums[k] / n).toFixed(k === "wind" ? 2 : 1)) : null;
  }
  out.aqi = aqiCount ? Number((aqiSum / aqiCount).toFixed(0)) : null;
  return out;
}

function gaugeWidth(v) {
  if (v == null) return "0%";
  const val = Number(v);
  const max = 200; 
  return Math.min(100, (val / max) * 100) + "%";
}

function gaugeColor(v) {
  if (v == null) return "#ddd333";
  const val = Number(v);
  if (val < 50) return "#00E676"; // Good
  if (val < 100) return "#FFE600"; // Moderate (Endfield Yellow)
  if (val < 150) return "#FF9100"; // Unhealthy
  return "#FF1744"; // Hazardous
}

function formatVal(v) {
  return v == null ? "-" : v;
}
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 10px;
}

.date {
  font-family: var(--font-display);
  font-size: 24px;
  color: var(--c-white);
}

.location-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.location {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--c-yellow);
}

.reset-btn {
  background: transparent;
  border: 1px solid var(--c-yellow);
  color: var(--c-yellow);
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 6px;
  cursor: pointer;
  text-transform: uppercase;
}

.reset-btn:hover {
  background: var(--c-yellow);
  color: var(--c-black);
}

.main-row {
  display: flex;
  gap: 20px;
}

.aqi-block {
  background: var(--c-yellow);
  color: var(--c-black);
  padding: 10px;
  min-width: 80px;
  text-align: center;
  clip-path: polygon(0 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%);
}

.aqi-block .label {
  font-size: 12px;
  font-weight: 700;
}

.aqi-block .aqi-value {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  line-height: 1;
}

.weather {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.weather-item {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 5px;
}

.weather-item .icon {
  font-family: var(--font-mono);
  color: var(--c-gray);
  font-size: 12px;
}

.weather-item .val {
  font-family: var(--font-mono);
  color: var(--c-white);
  font-size: 14px;
}

.gauge-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.gauge-card {
  border: 1px solid var(--c-border);
  padding: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.gauge-card:hover {
  border-color: var(--c-white);
}

.gauge-card.active {
  border-color: var(--c-yellow);
  background: rgba(255, 230, 0, 0.05);
}

.gauge-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-family: var(--font-mono);
  font-size: 12px;
}

.gauge-label .name {
  color: var(--c-gray);
}

.gauge-label .val {
  color: var(--c-white);
}

.gauge-track {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
}

.gauge-fill {
  height: 100%;
}
</style>
