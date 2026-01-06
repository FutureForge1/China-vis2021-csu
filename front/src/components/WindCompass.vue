<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>WIND COMPASS</h3>
        <span class="sub">DAILY U/V MEAN</span>
      </div>
      <div class="badge">SPEED m/s</div>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{dir,value}]
});

function directionToAngle(dir) {
  const map = {
    N: 0, NNE: 22.5, NE: 45, ENE: 67.5,
    E: 90, ESE: 112.5, SE: 135, SSE: 157.5,
    S: 180, SSW: 202.5, SW: 225, WSW: 247.5,
    W: 270, WNW: 292.5, NW: 315, NNW: 337.5,
  };
  return map[dir] ?? 0;
}

const option = computed(() => {
  const dirs = props.data.map((d) => d.dir);
  const values = props.data.map((d) => d.value);
  const angles = dirs.map(directionToAngle);
  const max = values.length ? Math.max(...values) : 1;
  const gradient = ["#FFE600", "#FFD700", "#FFC107", "#FFB300"];

  return {
    backgroundColor: "transparent",
    tooltip: {
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "rgba(0,0,0,0.08)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (p) =>
        `<div style="font-family:'Oswald';font-weight:bold">${dirs[p.dataIndex]}</div>
         <div style="font-size:12px">SPEED: ${values[p.dataIndex].toFixed(2)} m/s</div>`,
    },
    polar: { radius: ["12%", "78%"] },
    angleAxis: {
      type: "category",
      data: dirs,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisLabel: { color: "#666", fontSize: 11, fontFamily: 'JetBrains Mono' },
      axisTick: { show: false },
    },
    radiusAxis: {
      min: 0,
      max: Math.max(max, 1),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    },
    series: [
      {
        type: "line",
        coordinateSystem: "polar",
        data: values,
        smooth: true,
        areaStyle: { color: "rgba(255, 230, 0, 0.14)" },
        lineStyle: { color: gradient[3], width: 2 },
        symbol: "none",
        itemStyle: { color: gradient[3] },
        z: 3,
      },
      {
        type: "scatter",
        coordinateSystem: "polar",
        data: values.map((v, i) => ({ value: v, symbolRotate: angles[i] })),
        symbol: "arrow",
        symbolSize: 14,
        itemStyle: { color: "#0a0a0a" },
        emphasis: { scale: true },
        z: 4,
      }
    ],
  };
});
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
.badge {
  font-size: 10px;
  color: var(--c-black);
  background: var(--c-yellow);
  padding: 2px 6px;
  font-family: var(--font-mono);
  font-weight: bold;
}
.chart {
  height: 250px;
}
</style>
