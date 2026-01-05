<template>
  <div class="wrap">
    <div class="heading">
      <h3>MONTHLY TREND</h3>
      <span class="sub">{{ year }} - {{ metric.toUpperCase() }}</span>
    </div>
    <div ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  year: String,
  metric: String,
  data: Array
});

const chartEl = ref(null);
let chart = null;

function renderChart() {
  if (!chartEl.value || !props.data.length) return;

  if (!chart) {
    chart = echarts.init(chartEl.value);
  }

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: 'axis',
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
    },
    grid: { top: 30, left: 40, right: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.period),
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
    },
    yAxis: {
      type: 'value',
      name: props.metric.toUpperCase(),
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      nameTextStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
    },
    series: [{
      data: props.data.map(d => d.avgValue),
      type: 'line',
      smooth: true,
      showSymbol: false,
      lineStyle: {
        width: 2,
        color: "#FFE600"
      },
      areaStyle: {
        opacity: 0.2,
        color: {
          type: "linear",
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: "#FFE600" },
            { offset: 1, color: "transparent" },
          ],
        },
      }
    }]
  };

  chart.setOption(option);
}

watch(() => [props.data, props.metric], renderChart, { deep: true });
onMounted(renderChart);
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
  width: 100%;
  height: 250px;
}
</style>