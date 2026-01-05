<template>
  <div class="wrap">
    <div class="heading">
      <h3>POLLUTANT DISTRIBUTION</h3>
      <span class="sub">PERCENTAGE</span>
    </div>
    <div ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts';
import { onMounted, ref, watch } from 'vue';

const props = defineProps({
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
      trigger: 'item',
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: '{b}: {c}%'
    },
    series: [{
      name: 'POLLUTANT',
      type: 'pie',
      radius: ['40%', '70%'],
      data: props.data.map(d => ({
        ...d,
        name: d.name.toUpperCase()
      })),
      label: {
        color: "#0a0a0a",
        fontFamily: 'JetBrains Mono'
      },
      itemStyle: {
        borderRadius: 0,
        borderColor: '#0a0a0a',
        borderWidth: 2
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  };

  chart.setOption(option);
}

watch(() => props.data, renderChart, { deep: true });
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