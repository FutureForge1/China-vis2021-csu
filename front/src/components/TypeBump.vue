<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染类型变化</h3>
      <span class="sub">按城市数量</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{name, data}]
});

const palette = {
  标准型: "#22c55e",
  偏二次型: "#facc15",
  偏燃煤型: "#ef4444",
  偏交通型: "#2563eb",
  偏燃烧型: "#a855f7",
  偏颗粒物型: "#f97316",
  未知: "#9ca3af",
};

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "axis" },
  legend: {
    top: 4,
    textStyle: { color: "#cdd9e5" },
  },
  grid: { top: 40, left: 60, right: 20, bottom: 60 },
  xAxis: {
    type: "category",
    data: props.dates,
    axisLabel: { formatter: (v) => v.slice(5), color: "#9eb1c7" },
  },
  yAxis: {
    type: "value",
    name: "城市数",
    axisLabel: { color: "#9eb1c7" },
    splitLine: { lineStyle: { color: "#30363d" } },
  },
  series: props.series.map((s) => ({
    type: "line",
    name: s.name,
    data: s.data,
    smooth: true,
    areaStyle: { opacity: 0.1, color: palette[s.name] || "#9ca3af" },
    lineStyle: { width: 2, color: palette[s.name] || "#9ca3af" },
    symbol: "circle",
    symbolSize: 4,
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
  height: 260px;
}
</style>
