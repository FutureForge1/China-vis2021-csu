<template>
  <div class="pollutant-pie">
    <div ref="chartEl" style="width: 100%; height: 300px;"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import * as echarts from 'echarts';

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
    title: {
      text: '污染物比例分布',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c}%'
    },
    series: [{
      name: '污染物比例',
      type: 'pie',
      radius: '70%',
      data: props.data,
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