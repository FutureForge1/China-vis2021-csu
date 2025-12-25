<template>
  <div class="wrap">
    <div class="heading">
      <h3>趋势</h3>
      <span class="sub">{{ metric.toUpperCase() }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  series: { type: Array, default: () => [] }, // [{date, value}]
  dates: { type: Array, default: () => [] },
  metric: { type: String, default: "pm25" },
});

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "axis" },
  grid: { top: 30, left: 40, right: 20, bottom: 50 },
  xAxis: {
    type: "category",
    data: props.dates,
    boundaryGap: false,
  },
  yAxis: {
    type: "value",
    name: props.metric.toUpperCase(),
    alignTicks: false,
  },
  dataZoom: [
    { type: "inside", start: 0, end: 100 },
    { type: "slider", start: 0, end: 100 },
  ],
  series: [
    {
      type: "line",
      data: props.series.map((s) => s.value),
      smooth: true,
      showSymbol: false,
      areaStyle: { opacity: 0.15 },
      lineStyle: { width: 2 },
    },
  ],
}));
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.heading {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.sub {
  color: #9eb1c7;
  font-size: 12px;
}

.chart {
  height: 200px;
}
</style>
