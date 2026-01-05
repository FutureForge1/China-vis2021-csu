<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>POLLUTANT RINGS</h3>
        <span class="sub">SEGMENTS: VALUE · COLOR: AQI</span>
      </div>
      <div class="note">ORDERED BY AQI RANK</div>
    </div>
    <div class="grid" v-if="items && items.length">
      <div class="cell header empty"></div>
      <div
        v-for="m in months"
        :key="m"
        class="cell header month"
      >
        {{ m }}
      </div>
      <div v-for="row in items" :key="row.name" class="grid-row">
        <div class="cell row-label">{{ row.name }}</div>
        <div
          v-for="cell in row.months"
          :key="'cell-' + row.name + '-' + cell.month"
          class="cell ring-cell"
          :style="cellStyle(cell)"
          :title="`${row.name} ${cell.month}\n${metricLabel.toUpperCase()}: ${cell.value}\nAQI: ${cell.aqi.toFixed(1)}`"
        >
          <svg viewBox="0 0 100 100" aria-hidden="true">
            <g :stroke="aqiColor(cell.aqi)" stroke-width="2" stroke-linecap="round">
              <line
                v-for="i in cell.segments"
                :key="i"
                :x1="50"
                :y1="50"
                :x2="50 + 32 * Math.cos((i / cell.segments) * Math.PI * 2)"
                :y2="50 + 32 * Math.sin((i / cell.segments) * Math.PI * 2)"
                :opacity="0.75"
              />
            </g>
            <circle cx="50" cy="50" r="8" :fill="aqiColor(cell.aqi)" fill-opacity="0.8" />
          </svg>
        </div>
      </div>
    </div>
    <div v-else class="placeholder">NO DATA AVAILABLE</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name, months:[{month,value,aqi,segments}]}]
  metric: { type: String, default: "pm25" },
});

const months = Array.from({ length: 12 }, (_, i) => i + 1);
const metricLabel = computed(() => props.metric || "pm25");

const cellStyle = (cell) => {
  const color = aqiColor(cell.aqi);
  return {
    background: `radial-gradient(circle at 50% 50%, ${color}18, rgba(255,255,255,0.03))`,
    borderColor: `${color}55`,
  };
};

function aqiColor(v) {
  if (v <= 50) return "#22c55e";
  if (v <= 100) return "#a3e635";
  if (v <= 150) return "#facc15";
  if (v <= 200) return "#f97316";
  if (v <= 300) return "#ef4444";
  return "#7f1d1d";
}
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 5px;
}
h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--c-white);
}
.sub {
  color: var(--c-gray);
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
}
.note {
  font-size: 10px;
  color: var(--c-black);
  background: var(--c-yellow);
  padding: 2px 6px;
  font-family: var(--font-mono);
  font-weight: bold;
}
.grid {
  display: grid;
  grid-template-columns: 110px repeat(12, 1fr);
  gap: 6px;
  align-items: center;
}
.grid-row {
  display: contents;
}
.cell {
  min-height: 64px;
  border: 1px solid var(--c-border);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
}
.cell.header {
  min-height: 32px;
  font-size: 12px;
  color: var(--c-gray);
  background: var(--c-card);
  font-family: var(--font-mono);
}
.cell.row-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--c-white);
  justify-content: flex-start;
  padding-left: 8px;
  font-family: var(--font-display);
}
.cell.ring-cell {
  height: 64px;
  padding: 4px;
}
.cell.ring-cell svg {
  width: 60px;
  height: 60px;
}
.placeholder {
  padding: 16px;
  color: var(--c-gray);
  text-align: center;
  border: 1px dashed var(--c-border);
  font-family: var(--font-mono);
}
@media (max-width: 1100px) {
  .grid {
    overflow-x: auto;
    padding-bottom: 6px;
  }
}
</style>
