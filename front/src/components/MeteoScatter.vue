<template>
  <div class="wrap">
    <div class="heading">
      <h3>METEOROLOGY-POLLUTION SCATTER</h3>
      <span class="sub">{{ xMetricLabel }} vs {{ yMetricLabel }}</span>
    </div>
    <div class="controls">
      <div class="control-group">
        <label>X轴 (气象):</label>
        <select v-model="localXMetric">
          <option value="temp">温度 TEMP</option>
          <option value="rh">湿度 RH</option>
          <option value="psfc">气压 PSFC</option>
        </select>
      </div>
      <div class="control-group">
        <label>Y轴 (污染物):</label>
        <select v-model="localYMetric">
          <option value="pm25">PM2.5</option>
          <option value="pm10">PM10</option>
          <option value="o3">O₃</option>
          <option value="no2">NO₂</option>
          <option value="so2">SO₂</option>
          <option value="co">CO</option>
        </select>
      </div>
    </div>
    <div ref="chartEl" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  data: { type: Array, default: () => [] },
  xMetric: { type: String, default: 'temp' },
  yMetric: { type: String, default: 'pm25' }
});

const chartEl = ref(null);
let chart = null;

const localXMetric = ref(props.xMetric);
const localYMetric = ref(props.yMetric);

const metricLabels = {
  temp: 'TEMP (K)',
  rh: 'RH (%)',
  psfc: 'PSFC (Pa)',
  pm25: 'PM2.5 (μg/m³)',
  pm10: 'PM10 (μg/m³)',
  o3: 'O₃ (μg/m³)',
  no2: 'NO₂ (μg/m³)',
  so2: 'SO₂ (μg/m³)',
  co: 'CO (mg/m³)'
};

const xMetricLabel = computed(() => metricLabels[localXMetric.value] || localXMetric.value.toUpperCase());
const yMetricLabel = computed(() => metricLabels[localYMetric.value] || localYMetric.value.toUpperCase());

// 计算散点数据
const scatterData = computed(() => {
  if (!props.data || props.data.length === 0) return [];
  
  const xField = `${localXMetric.value}_mean`;
  const yField = `${localYMetric.value}_mean`;
  
  return props.data
    .filter(row => {
      const xVal = Number(row[xField] ?? row[localXMetric.value]);
      const yVal = Number(row[yField] ?? row[localYMetric.value]);
      return !isNaN(xVal) && !isNaN(yVal) && xVal > 0 && yVal > 0;
    })
    .map(row => {
      const xVal = Number(row[xField] ?? row[localXMetric.value]);
      const yVal = Number(row[yField] ?? row[localYMetric.value]);
      return {
        value: [xVal, yVal],
        city: row.city || row.province || 'Unknown',
        province: row.province || ''
      };
    });
});

// 计算趋势线
const trendLine = computed(() => {
  if (scatterData.value.length < 2) return [];
  
  const points = scatterData.value.map(d => d.value);
  const n = points.length;
  
  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
  for (const [x, y] of points) {
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumX2 += x * x;
  }
  
  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
  const intercept = (sumY - slope * sumX) / n;
  
  const xValues = points.map(p => p[0]);
  const minX = Math.min(...xValues);
  const maxX = Math.max(...xValues);
  
  return [
    [minX, slope * minX + intercept],
    [maxX, slope * maxX + intercept]
  ];
});

function renderChart() {
  if (!chartEl.value) return;
  
  if (!chart) {
    chart = echarts.init(chartEl.value);
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
        if (params.seriesType === 'line') return '';
        const d = params.data;
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${d.city}</div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>${xMetricLabel.value}:</span><span style="font-weight: bold;">${d.value[0].toFixed(2)}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>${yMetricLabel.value}:</span><span style="font-weight: bold;">${d.value[1].toFixed(2)}</span></div>`;
      }
    },
    grid: {
      top: 30,
      left: 60,
      right: 30,
      bottom: 50
    },
    xAxis: {
      type: 'value',
      name: xMetricLabel.value,
      nameLocation: 'middle',
      nameGap: 30,
      nameTextStyle: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      },
      axisLabel: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      },
      axisLine: { lineStyle: { color: '#ddd' } },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.05)' } }
    },
    yAxis: {
      type: 'value',
      name: yMetricLabel.value,
      nameLocation: 'middle',
      nameGap: 45,
      nameTextStyle: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      },
      axisLabel: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(0,0,0,0.05)' } }
    },
    series: [
      {
        name: 'scatter',
        type: 'scatter',
        data: scatterData.value,
        symbolSize: 8,
        itemStyle: {
          color: '#FFE600',
          borderColor: '#0a0a0a',
          borderWidth: 1,
          opacity: 0.7
        },
        emphasis: {
          itemStyle: {
            opacity: 1,
            shadowBlur: 10,
            shadowColor: 'rgba(255, 230, 0, 0.5)'
          }
        }
      },
      {
        name: 'trend',
        type: 'line',
        data: trendLine.value,
        smooth: false,
        showSymbol: false,
        lineStyle: {
          color: '#dc2626',
          width: 2,
          type: 'dashed'
        },
        z: 10
      }
    ]
  };
  
  chart.setOption(option, true);
}

function handleResize() {
  chart?.resize();
}

watch([localXMetric, localYMetric, () => props.data], renderChart, { deep: true });

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

.controls {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.control-group label {
  font-size: 11px;
  color: #666;
  font-family: "JetBrains Mono", monospace;
}

.control-group select {
  padding: 4px 8px;
  font-size: 11px;
  font-family: "JetBrains Mono", monospace;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  color: #0a0a0a;
  cursor: pointer;
}

.control-group select:hover {
  border-color: #FFE600;
}

.control-group select:focus {
  outline: none;
  border-color: #FFE600;
  box-shadow: 0 0 0 2px rgba(255, 230, 0, 0.2);
}

.chart {
  flex: 1;
  min-height: 280px;
  width: 100%;
}
</style>
