<template>
  <div class="wrap">
    <div class="heading">
      <h3>POLLUTION LEVELS</h3>
      <span class="sub">{{ scopeLabel }}</span>
    </div>
    <VChart :option="option" class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  levels: { type: Array, default: () => [] }, // [{level, value}]
  scope: { type: String, default: "national" },
});

const scopeLabel = computed(() => {
  const map = {
    national: "NATIONAL · DAILY COUNT",
    province: "PROVINCE · DAILY COUNT",
  };
  const key = (props.scope || "national").toLowerCase();
  return map[key] || `${key.toUpperCase()} · DAILY COUNT`;
});

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: {
    trigger: "item",
    backgroundColor: "rgba(255,255,255,0.95)",
    borderColor: "#FFE600",
    borderWidth: 1,
    textStyle: {
      color: "#0a0a0a",
      fontFamily: "JetBrains Mono",
      fontSize: 12,
    },
    formatter: (p) => {
      return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${p.name}</div>
              <div style="display: flex; justify-content: space-between; gap: 12px;"><span>COUNT:</span><span style="font-weight: bold; color: #0a0a0a;">${p.value}</span></div>`;
    },
  },
  grid: { top: 10, left: 50, right: 30, bottom: 80, containLabel: true },
  xAxis: {
    type: "category",
    data: props.levels.map((l) => l.level),
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    axisLine: { lineStyle: { color: "#ddd" } },
    axisTick: { show: false },
    splitLine: { show: false },
  },
  yAxis: {
    type: "value",
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    axisLine: { lineStyle: { color: "#ddd" } },
    axisTick: { show: false },
  },
  series: [
    {
      type: "bar",
      data: props.levels.map((l) => l.value),
      label: {
        show: true,
        position: "top",
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 10,
      },
      itemStyle: {
        color: (p) => {
          // Endfield Yellow Scale (Dark -> Bright)
          const palette = [
            "#ddd333",
            "#4d4500",
            "#665c00",
            "#998a00",
            "#ccb800",
            "#FFE600",
          ];
          return {
            type: "linear",
            x: 0,
            y: 0,
            x2: 1,
            y2: 0,
            colorStops: [
              { offset: 0, color: palette[p.dataIndex % palette.length] },
              { offset: 1, color: palette[p.dataIndex % palette.length] },
            ],
          };
        },
        borderRadius: 0,
        borderColor: "#000",
        borderWidth: 1,
      },
    },
  ],
}));
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 100%;
  overflow: hidden;
  min-height: 500px;
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
  font-size: 16px;
  font-weight: bold;
  color: #0a0a0a;
  font-family: "Oswald", sans-serif;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.sub {
  color: #000;
  background: #ffe600;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: bold;
  font-family: "JetBrains Mono", monospace;
  text-transform: uppercase;
}

.chart {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 450px;
}
</style>
