<template>
  <div class="wrap">
    <div class="heading">
      <h3>MONTHLY POLLUTANT RING</h3>
      <span class="sub">COLOR=AQI LEVEL</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name,data,aqi,level}]
});

const levelColor = {
  优: "#22c55e",
  良: "#a3e635",
  轻度: "#facc15",
  中度: "#f97316",
  重度: "#ef4444",
  严重: "#7f1d1d",
};

const option = computed(() => {
  const indicators = props.items[0]?.data?.map((d) => d.indicator) || [];
  const max = Math.max(
    10,
    ...props.items.flatMap((item) => item.data?.map((d) => Number(d.value) || 0) || [])
  );

  return {
    backgroundColor: "transparent",
    legend: { 
      top: 0, 
      right: 0,
      textStyle: { 
        color: "#666",
        fontFamily: "JetBrains Mono",
        fontSize: 10
      },
      itemWidth: 12,
      itemHeight: 2
    },
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
        const item = props.items[p.seriesIndex];
        const vals = indicators.map((ind, idx) => `<div style="display: flex; justify-content: space-between; gap: 12px;"><span>${ind}:</span><span style="font-weight: bold; color: #0a0a0a;">${p.value[idx]}</span></div>`).join("");
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${item.name}</div>
                <div style="margin-bottom: 4px;">AQI: <span style="color: ${levelColor[item.level] || '#0a0a0a'}">${item.aqi} (${item.level})</span></div>
                ${vals}`;
      },
    },
    radar: {
      indicator: indicators.map((ind) => ({ name: ind, max })),
      splitNumber: 5,
      splitArea: { areaStyle: { color: ["rgba(0,0,0,0.02)", "rgba(0,0,0,0.04)"] } },
      axisName: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      axisLabel: { show: false },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.08)" } },
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } }
    },
    series: props.items.map((item) => ({
      type: "radar",
      name: item.name,
      data: [item.data.map((d) => d.value)],
      areaStyle: { opacity: 0.12, color: levelColor[item.level] || "#60a5fa" },
      lineStyle: { width: 2, color: levelColor[item.level] || "#60a5fa" },
      symbol: "none"
    })),
  };
});
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
