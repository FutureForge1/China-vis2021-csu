<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染物与 AQI 平行坐标</h3>
      <span class="sub">按省均值</span>
    </div>
    <VChart :option="option" autoresize class="chart" @click="handleClick" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  rows: { type: Array, default: () => [] }, // [{name, values:[AQI, pm25...], primaryPollutant}]
});

const emit = defineEmits(["select"]);

const dimensions = ["AQI", "PM2.5", "PM10", "SO2", "NO2", "CO", "O3"];

const option = computed(() => {
  const axis = dimensions.map((d, idx) => ({
    dim: idx,
    name: d,
    nameTextStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
    axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
    axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
  }));

  const data = props.rows.map((r) => ({
    name: r.name,
    value: r.values,
    primary: r.primaryPollutant?.toUpperCase?.() || "-",
  }));

  return {
    backgroundColor: "transparent",
    parallelAxis: axis,
    parallel: {
      left: 60,
      right: 40,
      bottom: 30,
      top: 40,
    },
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (p) => {
        const d = data[p.dataIndex];
        const lines = [`<div style="font-family: 'Oswald'; font-weight: bold">${d.name}</div>`];
        dimensions.forEach((dim, i) => {
          lines.push(`${dim}: ${d.value[i]}`);
        });
        lines.push(`PRIMARY: ${d.primary}`);
        return lines.join("<br/>");
      },
    },
    visualMap: {
      type: "continuous",
      min: 0,
      max: Math.max(...(data.map((d) => d.value[0]).filter((n) => Number.isFinite(n))), 50),
      dimension: 0,
      inRange: {
        color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
      },
      text: ["HIGH", "LOW"],
      textStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
    },
    series: [
      {
        type: "parallel",
        lineStyle: { width: 1, opacity: 0.7 },
        data,
      },
    ],
  };
});

function handleClick(p) {
  const idx = p?.dataIndex;
  if (idx != null) emit("select", props.rows[idx]?.name);
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
  align-items: baseline;
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
.chart {
  height: 320px;
}
</style>
