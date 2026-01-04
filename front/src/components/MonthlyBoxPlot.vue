<template>
  <div class="monthly-boxplot">
    <div class="chart-header">
      <h3>{{ title }}</h3>
      <div class="metric-info">
        <span class="unit">{{ getUnit(metric) }}</span>
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as echarts from 'echarts';

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
    default: '月度箱线图'
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
  const months = ['1月', '2月', '3月', '4月', '5月', '6月',
                 '7月', '8月', '9月', '10月', '11月', '12月'];

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
    title: {
      show: false
    },
    tooltip: {
      trigger: 'item',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        if (params.componentType === 'boxplot') {
          const data = params.data;
          const month = months[params.dataIndex];
          return `
            ${month}<br/>
            最大值: ${data[4].toFixed(1)}<br/>
            上四分位: ${data[3].toFixed(1)}<br/>
            中位数: ${data[2].toFixed(1)}<br/>
            下四分位: ${data[1].toFixed(1)}<br/>
            最小值: ${data[0].toFixed(1)}
          `;
        } else if (params.componentType === 'scatter') {
          return `${months[params.data[0]]} 异常值: ${params.data[1].toFixed(1)}`;
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
        rotate: 45,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      name: getUnit(props.metric),
      nameTextStyle: {
        fontSize: 12
      }
    },
    series: [
      {
        name: '箱线图',
        type: 'boxplot',
        data: boxData,
        itemStyle: {
          color: '#2f7e57',
          borderColor: '#1f5a42',
          borderWidth: 1.5
        },
        emphasis: {
          itemStyle: {
            color: '#8bbf5f',
            borderColor: '#2f7e57',
            borderWidth: 2
          }
        }
      },
      {
        name: '异常值',
        type: 'scatter',
        data: outliers,
        symbolSize: 6,
        itemStyle: {
          color: '#eab308',
          borderColor: '#d97706',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            color: '#f59e0b'
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
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(18, 24, 40, 0.08);
}

.chart-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.metric-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.unit {
  font-size: 12px;
  color: var(--muted);
  background: rgba(47, 126, 87, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid rgba(47, 126, 87, 0.2);
}

.chart-container {
  flex: 1;
  min-height: 250px;
}
</style>
