<template>
  <div class="monthly-trend-chart">
    <div ref="chartEl" style="width: 100%; height: 300px;"></div>
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
    title: {
      text: `${props.year}年${props.metric.toUpperCase()}月度趋势`,
      left: 'center'
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: props.data.map(d => d.period)
    },
    yAxis: {
      type: 'value',
      name: props.metric.toUpperCase()
    },
    series: [{
      data: props.data.map(d => d.avgValue),
      type: 'line',
      smooth: true,
      lineStyle: {
        width: 3
      }
    }]
  };

  chart.setOption(option);
}

watch(() => [props.data, props.metric], renderChart, { deep: true });
onMounted(renderChart);
</script>