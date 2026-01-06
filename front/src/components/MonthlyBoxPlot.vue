<template>
  <div class="monthly-boxplot">
    <div class="chart-header">
      <h3>{{ title === '月度箱线图' ? 'MONTHLY BOXPLOT' : title }}</h3>
      <div class="metric-info">
        <span class="unit">{{ getUnit(metric) }}</span>
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts';
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  metric: {
    type: String,
    default: 'pm25'
  },
  title: {
    type: String,
    default: 'MONTHLY BOXPLOT'
  }
});

const chartContainer = ref(null);
let chartInstance = null;

// 污染物单位映射
const getUnit = (metric) => {
  const units = {
    pm25: 'μg/m³',
    pm10: 'μg/m³',
    so2: 'μg/m³',
    no2: 'μg/m³',
    co: 'mg/m³',
    o3: 'μg/m³',
    temp: '°C',
    rh: '%',
    psfc: 'hPa',
    wind: 'm/s'
  };
  return units[metric] || '';
};

// 计算箱线图数据 [min, Q1, median, Q3, max]
const calculateBoxPlotData = (values) => {
  if (!values || values.length === 0) return [0, 0, 0, 0, 0];

  const sorted = [...values].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const median = sorted[Math.floor(sorted.length / 2)];

  const q1Index = Math.floor(sorted.length / 4);
  const q3Index = Math.floor((3 * sorted.length) / 4);
  const q1 = sorted[q1Index];
  const q3 = sorted[q3Index];

  return [min, q1, median, q3, max];
};

// 准备图表数据
const prepareChartData = () => {
  const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
                 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

  // 按月份分组数据
  const monthlyValues = Array.from({ length: 12 }, () => []);

  props.data.forEach(item => {
    const month = item.month - 1; // 月份从0开始
    const value = item[props.metric] || item[`${props.metric}_mean`];
    if (value !== undefined && value !== null && !isNaN(value)) {
      monthlyValues[month].push(Number(value));
    }
  });

  // 计算每个月的箱线图数据
  const boxData = monthlyValues.map((values, index) => {
    if (values.length === 0) {
      return [0, 0, 0, 0, 0]; // 默认值
    }
    return calculateBoxPlotData(values);
  });

  // 计算异常值 (outliers)
  const outliers = [];
  monthlyValues.forEach((values, monthIndex) => {
    if (values.length === 0) return;

    const [min, q1, , q3, max] = calculateBoxPlotData(values);
    const iqr = q3 - q1;
    const lowerFence = q1 - 1.5 * iqr;
    const upperFence = q3 + 1.5 * iqr;

    values.forEach(value => {
      if (value < lowerFence || value > upperFence) {
        outliers.push([monthIndex, value]);
      }
    });
  });

  return {
    months,
    boxData,
    outliers
  };
};

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return;

  chartInstance = echarts.init(chartContainer.value);
  updateChart();
};

// 更新图表
const updateChart = () => {
  if (!chartInstance) return;

  const { months, boxData, outliers } = prepareChartData();

  const option = {
    backgroundColor: 'transparent',
    title: {
      show: false
    },
    tooltip: {
      trigger: 'item',
      axisPointer: {
        type: 'shadow'
      },
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (params) => {
        if (params.componentType === 'boxplot') {
          const data = params.data;
          const month = months[params.dataIndex];
          return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${month}</div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>MAX:</span><span style="font-weight: bold; color: #0a0a0a;">${data[5].toFixed(1)}</span></div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>Q3:</span><span style="font-weight: bold; color: #0a0a0a;">${data[4].toFixed(1)}</span></div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>MEDIAN:</span><span style="font-weight: bold; color: #0a0a0a;">${data[3].toFixed(1)}</span></div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>Q1:</span><span style="font-weight: bold; color: #0a0a0a;">${data[2].toFixed(1)}</span></div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>MIN:</span><span style="font-weight: bold; color: #0a0a0a;">${data[1].toFixed(1)}</span></div>`;
        } else if (params.componentType === 'scatter') {
          return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${months[params.data[0]]}</div>
                  <div style="display: flex; justify-content: space-between; gap: 12px;"><span>OUTLIER:</span><span style="font-weight: bold; color: #0a0a0a;">${params.data[1].toFixed(1)}</span></div>`;
        }
        return params.name;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: months,
      axisLabel: {
        rotate: 0,
        fontSize: 10,
        color: '#666',
        fontFamily: "JetBrains Mono"
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      axisTick: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: getUnit(props.metric),
      nameTextStyle: {
        fontSize: 10,
        color: '#666',
        fontFamily: "JetBrains Mono"
      },
      axisLabel: {
        fontSize: 10,
        color: '#666',
        fontFamily: "JetBrains Mono"
      },
      splitLine: {
        lineStyle: {
          color: '#ddd',
          type: 'dashed'
        }
      }
    },
    series: [
      {
        name: 'boxplot',
        type: 'boxplot',
        data: boxData,
        itemStyle: {
          color: 'transparent',
          borderColor: '#FFE600',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(255, 230, 0, 0.5)'
          }
        }
      },
      {
        name: 'outlier',
        type: 'scatter',
        data: outliers,
        symbolSize: 4,
        itemStyle: {
          color: '#FFE600',
          opacity: 0.6,
          borderColor: '#FFE600',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            color: '#0a0a0a'
          }
        }
      }
    ]
  };

  chartInstance.setOption(option, true);
};

// 响应窗口大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize();
  }
};

// 监听数据变化
watch(() => [props.data, props.metric], () => {
  nextTick(() => {
    updateChart();
  });
}, { deep: true });

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.monthly-boxplot {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.metric-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit {
  font-size: 10px;
  color: #666;
  font-family: "JetBrains Mono", monospace;
}

.chart-container {
  flex: 1;
  min-height: 0;
  width: 100%;
}
</style>
