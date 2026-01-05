<template>
  <div class="monthly-radar">
    <div ref="chartEl" style="width: 100%; height: 300px;"></div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts';
import { onMounted, ref, watch } from 'vue';

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
    backgroundColor: 'transparent',
    title: {
      text: 'POLLUTANT DISTRIBUTION RADAR',
      left: 'center',
      textStyle: {
        color: '#0a0a0a',
        fontFamily: "Oswald",
        fontSize: 14,
        fontWeight: 'bold'
      }
    },
    tooltip: {
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (params) => {
        let res = `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${params.name}</div>`;
        params.value.forEach((val, i) => {
          res += `<div style="display: flex; justify-content: space-between; gap: 12px;">
            <span>${props.data.indicators[i].name}:</span>
            <span style="font-weight: bold; color: #0a0a0a;">${val}</span>
          </div>`;
        });
        return res;
      }
    },
    radar: {
      indicator: props.data.indicators,
      axisName: {
        color: '#666',
        fontFamily: "JetBrains Mono",
        fontSize: 10
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0,0,0,0.08)'
        }
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(0,0,0,0.02)', 'rgba(0,0,0,0.05)']
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(0,0,0,0.1)'
        }
      }
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.data.values,
        name: 'POLLUTANT CONCENTRATION',
        itemStyle: {
          color: '#FFE600'
        },
        lineStyle: {
          color: '#FFE600',
          width: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(255, 230, 0, 0.5)' },
            { offset: 1, color: 'rgba(255, 230, 0, 0.1)' }
          ])
        }
      }]
    }]
  };

  chart.setOption(option);
}

watch(() => props.data, renderChart, { deep: true });
onMounted(renderChart);
</script>