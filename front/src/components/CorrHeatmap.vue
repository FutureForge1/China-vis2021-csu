<template>
  <div class="wrap">
    <div class="heading">
      <h3>POLLUTION-METEOROLOGY CORRELATION</h3>
      <span class="sub">PEARSON</span>
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
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (p) => {
        const item = props.matrix[p.dataIndex];
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">CORRELATION</div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>PAIR:</span><span style="font-weight: bold; color: #0a0a0a;">${item.pollutant} / ${item.meteor}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>VALUE:</span><span style="font-weight: bold; color: #0a0a0a;">${item.value}</span></div>`;
      },
    },
    xAxis: {
      type: "category",
      data: meteors,
      axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ["rgba(0,0,0,0.02)", "rgba(0,0,0,0.05)"] } },
      axisLine: { lineStyle: { color: "#ddd" } },
      axisTick: { show: false }
    },
    yAxis: {
      type: "category",
      data: pollutants,
      axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      splitArea: { show: true, areaStyle: { color: ["rgba(0,0,0,0.02)", "rgba(0,0,0,0.05)"] } },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 0,
      itemWidth: 10,
      itemHeight: 100,
      inRange: { color: ["#2563eb", "#e5e7eb", "#dc2626"] },
      textStyle: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    },
    series: [
      {
        name: "corr",
        type: "heatmap",
        data,
        label: {
          show: true,
          formatter: (p) => props.matrix[p.dataIndex].value,
          color: "#000",
          fontFamily: "JetBrains Mono",
          fontSize: 10
        },
        itemStyle: {
          borderColor: "#000",
          borderWidth: 1
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
  min-height: 250px;
  width: 100%;
}
</style>
