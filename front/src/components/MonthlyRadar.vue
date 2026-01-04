<template>
  <div class="monthly-radar">
    <div ref="chartEl" style="width: 100%; height: 300px;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  data: Object
});

const chartEl = ref(null);
let chart = null;

function renderChart() {
  if (!chartEl.value || !props.data) return;

  if (!chart) {
    chart = echarts.init(chartEl.value);
  }

  const option = {
    title: {
      text: '污染物分布雷达图',
      left: 'center'
    },
    radar: {
      indicator: props.data.indicators
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.data.values,
        name: '污染物浓度'
      }]
    }]
  };

  chart.setOption(option);
}

watch(() => props.data, renderChart, { deep: true });
onMounted(renderChart);
</script>