<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染-气象相关性</h3>
      <span class="sub">皮尔逊</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  matrix: {
    type: Array,
    default: () => [], // [{pollutant, meteor, value}]
  },
});

const option = computed(() => {
  const pollutants = Array.from(new Set(props.matrix.map((d) => d.pollutant)));
  const meteors = Array.from(new Set(props.matrix.map((d) => d.meteor)));
  const data = props.matrix.map((d) => [
    meteors.indexOf(d.meteor),
    pollutants.indexOf(d.pollutant),
    d.value,
  ]);
  return {
    backgroundColor: "transparent",
    tooltip: {
      formatter: (p) => {
        const item = props.matrix[p.dataIndex];
        return `${item.pollutant} / ${item.meteor}<br/>corr: ${item.value}`;
      },
    },
    xAxis: {
      type: "category",
      data: meteors,
      axisLabel: { color: "#cdd9e5" },
      splitArea: { show: true },
    },
    yAxis: {
      type: "category",
      data: pollutants,
      axisLabel: { color: "#cdd9e5" },
      splitArea: { show: true },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 10,
      inRange: { color: ["#2563eb", "#e5e7eb", "#dc2626"] },
      textStyle: { color: "#cdd9e5" },
    },
    series: [
      {
        name: "corr",
        type: "heatmap",
        data,
        label: {
          show: true,
          formatter: (p) => props.matrix[p.dataIndex].value,
          color: "#0f172a",
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.3)" },
        },
      },
    ],
  };
});
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
