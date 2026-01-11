<template>
  <div class="wrap">
    <div class="heading">
      <h3>PROVINCE YEARLY HEATMAP</h3>
      <span class="sub">{{ metric.toUpperCase() }} · {{ year }}</span>
    </div>
    <div ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  monthlyData: { type: Array, default: () => [] },
  metric: { type: String, default: 'pm25' },
  year: { type: String, default: '2013' }
});

const chartEl = ref(null);
let chart = null;

// 构建热力图数据
const heatmapData = computed(() => {
  if (!props.monthlyData || props.monthlyData.length === 0) {
    return { provinces: [], months: [], data: [], max: 100, min: 0 };
  }
  
  const metricField = `${props.metric}_mean`;
  const months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'];
  
  // 收集所有省份
  const provinceSet = new Set();
  props.monthlyData.forEach(monthEntry => {
    if (monthEntry.data && Array.isArray(monthEntry.data)) {
      monthEntry.data.forEach(row => {
        if (row.province) provinceSet.add(row.province);
      });
    }
  });
  
  const provinces = Array.from(provinceSet).sort();
  
  // 构建热力图数据
  const data = [];
  let max = 0;
  let min = Infinity;
  
  provinces.forEach((province, pIdx) => {
    props.monthlyData.forEach((monthEntry, mIdx) => {
      if (!monthEntry.data) return;
      
      // 计算该省份在该月的平均值
      const provinceRows = monthEntry.data.filter(row => row.province === province);
      if (provinceRows.length === 0) return;
      
      const values = provinceRows
        .map(row => Number(row[metricField] ?? row[props.metric]))
        .filter(v => !isNaN(v) && v > 0);
      
      if (values.length === 0) return;
      
      const avgValue = values.reduce((a, b) => a + b, 0) / values.length;
      data.push([mIdx, pIdx, avgValue]);
      
      if (avgValue > max) max = avgValue;
      if (avgValue < min) min = avgValue;
    });
  });
  
  return { provinces, months, data, max, min: min === Infinity ? 0 : min };
});

function renderChart() {
  if (!chartEl.value) return;
  
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }
  
  const { provinces, months, data, max, min } = heatmapData.value;
  
  if (provinces.length === 0) {
    chart.setOption({
      title: {
        text: '暂无数据',
        left: 'center',
        top: 'center',
        textStyle: { color: '#999', fontFamily: 'JetBrains Mono' }
      }
    });
    return;
  }
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#FFE600',
      borderWidth: 1,
      textStyle: {
        color: '#0a0a0a',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      },
      formatter: (params) => {
        const month = months[params.data[0]];
        const province = provinces[params.data[1]];
        const value = params.data[2];
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${province}</div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>月份:</span><span style="font-weight: bold;">${month}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>${props.metric.toUpperCase()}:</span><span style="font-weight: bold;">${value.toFixed(2)}</span></div>`;
      }
    },
    grid: {
      top: 10,
      left: 100,
      right: 60,
      bottom: 40
    },
    xAxis: {
      type: 'category',
      data: months,
      position: 'bottom',
      axisLabel: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      },
      axisLine: { lineStyle: { color: '#ddd' } },
      axisTick: { show: false },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'category',
      data: provinces,
      axisLabel: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 9,
        width: 80,
        overflow: 'truncate'
      },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false }
    },
    visualMap: {
      min: min,
      max: max,
      calculable: true,
      orient: 'vertical',
      right: 0,
      top: 'center',
      itemWidth: 10,
      itemHeight: 120,
      inRange: {
        color: ['#16a34a', '#84cc16', '#facc15', '#f97316', '#dc2626']
      },
      textStyle: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      }
    },
    series: [{
      name: props.metric.toUpperCase(),
      type: 'heatmap',
      data: data,
      label: { show: false },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0,0,0,0.3)'
        }
      }
    }]
  };
  
  chart.setOption(option, true);
}

function handleResize() {
  chart?.resize();
}

watch([() => props.monthlyData, () => props.metric], renderChart, { deep: true });

onMounted(() => {
  renderChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  chart?.dispose();
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  min-height: 400px;
  width: 100%;
}
</style>
