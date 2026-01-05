<template>
  <div class="wrap">
    <div class="heading">
      <h3>AQI RANKING</h3>
      <span class="sub">BY PROVINCE MEAN</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name, aqi, primaryPollutant}]
});

const emit = defineEmits(["select"]);

const option = computed(() => {
  const names = props.items.map((d) => d.name);
  const values = props.items.map((d) => d.aqi);
  const primary = props.items.map((d) => d.primaryPollutant?.toUpperCase?.() || "-");
  const colors = values.map((v) => aqiColor(v));

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (p) => {
        const i = p[0].dataIndex;
        return `<div style="font-weight:bold; font-family: 'Oswald'">${names[i]}</div>
                <div style="font-size:12px">AQI: ${values[i]}</div>
                <div style="font-size:12px">PRIMARY: ${primary[i]}</div>`;
      },
    },
    grid: { left: 80, right: 30, top: 10, bottom: 10 },
    xAxis: {
      type: "value",
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    },
    yAxis: {
      type: "category",
      data: names,
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
    },
    series: [
      {
        type: "bar",
        data: values,
        itemStyle: {
          color: (p) => ({
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: colors[p.dataIndex] + "88" },
              { offset: 1, color: colors[p.dataIndex] },
            ],
          }),
          borderRadius: [0, 0, 0, 0], // Industrial sharp corners
        },
        label: {
          show: true,
          position: "right",
          color: "#0a0a0a",
          fontSize: 10,
          fontFamily: 'JetBrains Mono'
        },
      },
    ],
    on: {
      click: (params) => {
        const idx = params?.dataIndex;
        if (idx != null) emit("select", names[idx]);
      },
    },
  };
});

function aqiColor(v) {
  if (v <= 50) return "#ddd333";
  if (v <= 100) return "#665c00";
  if (v <= 150) return "#998a00";
  if (v <= 200) return "#ccb800";
  if (v <= 300) return "#e6cf00";
  return "#FFE600";
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
  height: 300px;
}
</style>
