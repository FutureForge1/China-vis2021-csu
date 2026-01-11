<template>
  <div class="wrap">
    <div class="heading">
      <h3>MULTI-CITY TREND COMPARISON</h3>
      <span class="sub">{{ metric.toUpperCase() }} · {{ year }}</span>
    </div>
    <div class="controls">
      <div class="control-group">
        <label>城市选择 (最多5个):</label>
        <div class="city-tags">
          <span 
            v-for="city in selectedCities" 
            :key="city" 
            class="city-tag"
            :style="{ borderColor: getCityColor(city) }"
          >
            {{ city }}
            <button class="remove-btn" @click="removeCity(city)">×</button>
          </span>
        </div>
      </div>
      <div class="control-group">
        <select v-model="cityToAdd" @change="addCity">
          <option value="">+ 添加城市</option>
          <option 
            v-for="city in availableCities" 
            :key="city" 
            :value="city"
            :disabled="selectedCities.includes(city)"
          >
            {{ city }}
          </option>
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
  monthlyData: { type: Array, default: () => [] },
  metric: { type: String, default: 'pm25' },
  year: { type: String, default: '2013' }
});

const chartEl = ref(null);
let chart = null;

const cityToAdd = ref('');
const selectedCities = ref([]);

// 城市颜色方案
const cityColors = ['#FFE600', '#2563eb', '#dc2626', '#16a34a', '#9333ea'];

const getCityColor = (city) => {
  const idx = selectedCities.value.indexOf(city);
  return cityColors[idx % cityColors.length];
};

// 获取所有可用城市
const availableCities = computed(() => {
  if (!props.monthlyData || props.monthlyData.length === 0) return [];
  
  const citySet = new Set();
  props.monthlyData.forEach(monthEntry => {
    if (monthEntry.data && Array.isArray(monthEntry.data)) {
      monthEntry.data.forEach(row => {
        if (row.city) citySet.add(row.city);
      });
    }
  });
  
  return Array.from(citySet).sort();
});

// 初始化默认选择的城市
watch(availableCities, (cities) => {
  if (selectedCities.value.length === 0 && cities.length > 0) {
    // 默认选择前3个城市
    selectedCities.value = cities.slice(0, 3);
  }
}, { immediate: true });

const addCity = () => {
  if (cityToAdd.value && !selectedCities.value.includes(cityToAdd.value) && selectedCities.value.length < 5) {
    selectedCities.value.push(cityToAdd.value);
  }
  cityToAdd.value = '';
};

const removeCity = (city) => {
  selectedCities.value = selectedCities.value.filter(c => c !== city);
};

// 构建图表数据
const chartData = computed(() => {
  if (!props.monthlyData || props.monthlyData.length === 0) return { months: [], series: [] };
  
  const months = props.monthlyData.map((m, idx) => `${idx + 1}月`);
  const metricField = `${props.metric}_mean`;
  
  const series = selectedCities.value.map((city, idx) => {
    const data = props.monthlyData.map(monthEntry => {
      if (!monthEntry.data) return null;
      const cityRow = monthEntry.data.find(row => row.city === city);
      if (!cityRow) return null;
      const val = Number(cityRow[metricField] ?? cityRow[props.metric]);
      return isNaN(val) ? null : val;
    });
    
    return {
      name: city,
      data,
      color: cityColors[idx % cityColors.length]
    };
  });
  
  return { months, series };
});

function renderChart() {
  if (!chartEl.value) return;
  
  if (!chart) {
    chart = echarts.init(chartEl.value);
  }
  
  const { months, series } = chartData.value;
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#FFE600',
      borderWidth: 1,
      textStyle: {
        color: '#0a0a0a',
        fontFamily: 'JetBrains Mono',
        fontSize: 11
      },
      formatter: (params) => {
        let html = `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${params[0].axisValue}</div>`;
        params.forEach(p => {
          if (p.value !== null && p.value !== undefined) {
            html += `<div style="display: flex; justify-content: space-between; gap: 20px;">
              <span style="display: flex; align-items: center; gap: 4px;">
                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${p.color};"></span>
                ${p.seriesName}
              </span>
              <span style="font-weight: bold;">${p.value.toFixed(2)}</span>
            </div>`;
          }
        });
        return html;
      }
    },
    legend: {
      data: series.map(s => s.name),
      bottom: 0,
      textStyle: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      }
    },
    grid: {
      top: 30,
      left: 50,
      right: 20,
      bottom: 40
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: {
        color: '#666',
        fontFamily: 'JetBrains Mono',
        fontSize: 10
      },
      axisLine: { lineStyle: { color: '#ddd' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: props.metric.toUpperCase(),
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
    series: series.map(s => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      showSymbol: true,
      symbolSize: 6,
      lineStyle: {
        width: 2,
        color: s.color
      },
      itemStyle: {
        color: s.color,
        borderColor: '#fff',
        borderWidth: 1
      },
      emphasis: {
        focus: 'series',
        itemStyle: {
          shadowBlur: 10,
          shadowColor: 'rgba(0,0,0,0.3)'
        }
      }
    }))
  };
  
  chart.setOption(option, true);
}

function handleResize() {
  chart?.resize();
}

watch([selectedCities, () => props.monthlyData, () => props.metric], renderChart, { deep: true });

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
  align-items: center;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 11px;
  color: #666;
  font-family: "JetBrains Mono", monospace;
  white-space: nowrap;
}

.city-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.city-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 11px;
  font-family: "JetBrains Mono", monospace;
  background: rgba(255, 230, 0, 0.1);
  border: 1px solid #FFE600;
  border-radius: 12px;
  color: #0a0a0a;
}

.remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  padding: 0;
  border: none;
  background: transparent;
  color: #999;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.remove-btn:hover {
  color: #dc2626;
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
