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
    formatter: (p) => {
      const level = props.matrix.levels[p.data[0]];
      const year = props.matrix.years[p.data[1]];
      return `${year} 年<br/>等级：${level}<br/>省份-天数：${p.data[2]}`;
    },
  },
  grid: { top: 40, left: 70, right: 20, bottom: 50 },
  xAxis: {
    type: "category",
    data: props.matrix.levels,
    axisLabel: { color: "#cdd9e5" },
  },
  yAxis: {
    type: "category",
    data: props.matrix.years.map((y) => String(y)),
    axisLabel: { color: "#cdd9e5" },
  },
  visualMap: {
    min: 0,
    max: Math.max(...props.matrix.data.map((d) => d[2]), 1),
    calculable: true,
    orient: "horizontal",
    left: "center",
    bottom: 10,
    inRange: { color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"] },
    textStyle: { color: "#cdd9e5" },
  },
  series: [
    {
      name: "AQI-Level",
      type: "heatmap",
      data: props.matrix.data,
      label: { show: true, color: "#0f172a" },
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
  height: 260px;
}
</style>
