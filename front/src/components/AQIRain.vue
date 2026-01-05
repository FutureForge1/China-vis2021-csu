<template>
  <div class="wrap">
    <div class="heading">
      <h3>全国 AQI 等级晴雨图</h3>
      <span class="sub">固定 1 月</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  matrix: {
    type: Object,
    default: () => ({ years: [], levels: [], data: [] }), // data: [levelIdx, yearIdx, count]
  },
});

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: {
    backgroundColor: "rgba(255,255,255,0.95)",
    borderColor: "#FFE600",
    borderWidth: 1,
    textStyle: {
      color: "#0a0a0a",
      fontFamily: "JetBrains Mono",
      fontSize: 12
    },
    formatter: (p) => {
      const level = props.matrix.levels[p.data[0]];
      const year = props.matrix.years[p.data[1]];
      return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${year}</div>
              <div style="display: flex; justify-content: space-between; gap: 12px;">
                <span>LEVEL:</span>
                <span style="font-weight: bold; color: #0a0a0a;">${level}</span>
              </div>
              <div style="display: flex; justify-content: space-between; gap: 12px;">
                <span>COUNT:</span>
                <span style="font-weight: bold; color: #0a0a0a;">${p.data[2]}</span>
              </div>`;
    },
  },
  grid: { top: 20, left: 50, right: 20, bottom: 40 },
  xAxis: {
    type: "category",
    data: props.matrix.levels,
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    axisLine: { lineStyle: { color: "#ddd" } },
    axisTick: { show: false }
  },
  yAxis: {
    type: "category",
    data: props.matrix.years.map((y) => String(y)),
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false }
  },
  visualMap: {
    min: 0,
    max: Math.max(...props.matrix.data.map((d) => d[2]), 1),
    calculable: true,
    orient: "horizontal",
    left: "center",
    bottom: 0,
    itemWidth: 10,
    itemHeight: 100,
    inRange: { color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"] },
    textStyle: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
  },
  series: [
    {
      name: "AQI-Level",
      type: "heatmap",
      data: props.matrix.data,
      label: { show: true, color: "#000", fontFamily: "JetBrains Mono", fontSize: 10 },
      itemStyle: {
        borderColor: "#000",
        borderWidth: 1
      }
    },
  ],
}));
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 100%;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
}
h3 {
  margin: 0;
  font-size: 14px;
  font-weight: bold;
  color: #0a0a0a;
  font-family: "Oswald", sans-serif;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.sub {
  color: #FFE600;
  font-size: 10px;
  font-family: "JetBrains Mono", monospace;
  text-transform: uppercase;
}
.chart {
  flex: 1;
  min-height: 0;
}
</style>
