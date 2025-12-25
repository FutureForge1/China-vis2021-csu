<template>
  <div class="wrap">
    <div class="heading">
      <h3>多年 AQI 折线对比</h3>
      <span class="sub">1 月逐日均值</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  days: { type: Array, default: () => [] }, // ["1","2",...]
  series: { type: Array, default: () => [] }, // [{name, data}]
});

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "axis" },
  legend: { top: 4, textStyle: { color: "#cdd9e5" } },
  grid: { top: 40, left: 60, right: 20, bottom: 40 },
  xAxis: {
    type: "category",
    data: props.days,
    axisLabel: { color: "#9eb1c7" },
  },
  yAxis: {
    type: "value",
    name: "AQI",
    axisLabel: { color: "#9eb1c7" },
    splitLine: { lineStyle: { color: "#30363d" } },
  },
  series: props.series.map((s) => ({
    type: "line",
    name: s.name,
    data: s.data,
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 2 },
  })),
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
  height: 220px;
}
</style>
