<template>
  <div class="wrap">
    <div class="heading">
      <h3>POLLUTANT RADAR</h3>
      <span class="sub">MEAN</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{indicator, value}]
});

const option = computed(() => {
  const values = props.data.map((d) => Number(d.value ?? 0));
  const rawMax = values.length ? Math.max(...values) : 10;
  const roundedMax = Math.max(10, Math.ceil((rawMax || 10) / 10) * 10);
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
    },
    radar: {
      indicator: props.data.map((d) => ({
        name: d.indicator.toUpperCase(),
        min: 0,
        max: roundedMax,
      })),
      splitNumber: 5,
      splitArea: { areaStyle: { color: ["rgba(0,0,0,0.02)", "rgba(0,0,0,0.04)"] } },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisName: { color: "#666", fontFamily: 'JetBrains Mono' },
      axisLabel: { show: false },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name: "MEAN",
            areaStyle: { color: "#FFE600", opacity: 0.2 },
            lineStyle: { width: 2, color: "#FFE600" },
            itemStyle: { color: "#FFE600" },
            symbol: "none"
          },
        ],
      },
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
  height: 250px;
}
</style>
