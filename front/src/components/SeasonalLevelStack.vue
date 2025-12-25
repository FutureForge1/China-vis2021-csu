<template>
  <div class="wrap">
    <div class="heading">
      <h3>全年污染等级分布</h3>
      <span class="sub">{{ metricLabel }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" @click="handleClick" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{name, data}]
  metric: { type: String, default: "pm25" },
});

const emit = defineEmits(["select-date"]);

const metricLabel = computed(() => props.metric.toUpperCase());

function handleClick(params) {
  // params.name carries the x-axis category value (date string)
  if (params?.name) emit("select-date", params.name);
}

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "axis" },
  grid: { top: 30, left: 60, right: 20, bottom: 40 },
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
  legend: { top: 4, textStyle: { color: "#cdd9e5" } },
  series: props.series.map((s) => ({
    type: "bar",
    name: s.name,
    stack: "level",
    data: s.data,
    barWidth: "60%",
    emphasis: { focus: "series" },
  })),
  color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
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
