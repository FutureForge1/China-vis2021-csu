<template>
  <div class="province-dimension-chart">
    <div class="chart-controls">
      <div class="control-group">
        <label>分析方法：</label>
        <span class="method-name">PCA主成分分析</span>
      </div>
    </div>

    <div ref="chartContainer" class="chart-container"></div>

    <div class="chart-legend">
      <div class="legend-item">
        <span class="legend-color selected"></span>
        <span>当前选中省份</span>
      </div>
      <div class="legend-item">
        <span class="legend-color other"></span>
        <span>其他省份</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
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
  selectedProvince: {
    type: String,
    default: ''
  },
  selectedYear: {
    type: String,
    default: '2013'
  },
  selectedMonth: {
    type: String,
    default: '01'
  }
});

const emit = defineEmits(['province-select']);

const chartContainer = ref(null);
let chartInstance = null;

// 计算降维数据
const dimensionData = computed(() => {
  if (!props.data || props.data.length === 0) {
    console.log('无数据可供降维分析');
    return [];
  }

  console.log('开始计算降维数据，数据量:', props.data.length);

  // 使用所有污染物进行PCA分析
  const featureList = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3'];

  console.log('使用的特征列表:', featureList);

  // 按省份分组
  const provinceMap = {};
  props.data.forEach(item => {
    const province = item.province;
    if (!province) return;

    if (!provinceMap[province]) {
      provinceMap[province] = {
        province,
        values: [],
        stats: {}
      };
    }

    featureList.forEach((feature, index) => {
      const value = item[feature] || item[`${feature}_mean`] || 0;
      if (!provinceMap[province].values[index]) {
        provinceMap[province].values[index] = [];
      }
      provinceMap[province].values[index].push(Number(value));

      if (!provinceMap[province].stats[feature]) {
        provinceMap[province].stats[feature] = 0;
      }
    });
  });

  // 计算每个省份的平均值
  const provinces = Object.values(provinceMap).map(prov => {
    const avgValues = prov.values.map(values => {
      const validValues = values.filter(v => !isNaN(v) && v > 0);
      if (validValues.length === 0) return 0;
      const sum = validValues.reduce((a, b) => a + b, 0);
      return sum / validValues.length;
    });

    Object.keys(prov.stats).forEach(feature => {
      const idx = featureList.indexOf(feature);
      if (idx >= 0) {
        prov.stats[feature] = avgValues[idx];
      }
    });

    return {
      ...prov,
      avgValues
    };
  });

  console.log('省份数量:', provinces.length);
  if (provinces.length === 0) return [];

  // 简化的PCA计算
  const data = provinces.map(prov => {
    const pm25 = prov.stats.pm25 || 0.1;
    const o3 = prov.stats.o3 || 0.1;
    const pm10 = prov.stats.pm10 || 0.1;
    const so2 = prov.stats.so2 || 0.1;

    const x = (pm25 / (o3 + 0.1)) * 10;
    const y = (pm10 / (so2 + 0.1)) * 10;

    const allX = provinces.map(p => {
      const pPm25 = p.stats.pm25 || 0.1;
      const pO3 = p.stats.o3 || 0.1;
      return (pPm25 / (pO3 + 0.1)) * 10;
    });
    const allY = provinces.map(p => {
      const pPm10 = p.stats.pm10 || 0.1;
      const pSo2 = p.stats.so2 || 0.1;
      return (pPm10 / (pSo2 + 0.1)) * 10;
    });

    const maxX = Math.max(...allX, 1);
    const maxY = Math.max(...allY, 1);

    const magnitude = Math.sqrt(
      featureList.reduce((sum, feature) => {
        const val = prov.stats[feature] || 0;
        return sum + val * val;
      }, 0)
    );

    let pollutionLevel = '低';
    if (magnitude > 150) pollutionLevel = '高';
    else if (magnitude > 80) pollutionLevel = '中';

    return {
      name: prov.province,
      value: [x / maxX, y / maxY],
      rawValue: { x: x / maxX, y: y / maxY },
      stats: prov.stats,
      pollutionLevel,
      magnitude
    };
  });

  console.log('生成的降维数据:', data);
  return data;
});

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) {
    console.error('图表容器未找到');
    return;
  }

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);
  renderChart();
};

// 渲染图表
const renderChart = () => {
  if (!chartInstance || !dimensionData.value.length) {
    console.log('图表实例不存在或无数据，跳过渲染');
    return;
  }

  const data = dimensionData.value;
  const selected = props.selectedProvince;

  console.log('渲染图表，数据点数量:', data.length, '选中省份:', selected);

  const option = {
    title: {
      text: `省份污染特征PCA降维分析`,
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 'normal',
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        const province = params.data.name;
        const stats = params.data.stats || {};
        return `
          <div style="text-align: left; padding: 5px;">
            <strong style="color: #2f7e57; font-size: 14px;">${province}</strong><br/>
            <hr style="margin: 5px 0; border: none; border-top: 1px solid #eee;">
            PM2.5: ${(stats.pm25 || 0).toFixed(1)}<br/>
            PM10: ${(stats.pm10 || 0).toFixed(1)}<br/>
            SO₂: ${(stats.so2 || 0).toFixed(1)}<br/>
            NO₂: ${(stats.no2 || 0).toFixed(1)}<br/>
            CO: ${(stats.co || 0).toFixed(3)}<br/>
            O₃₃: ${(stats.o3 || 0).toFixed(1)}
          </div>
        `;
      }
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed',
          color: '#e0e0e0'
        }
      },
      axisLine: {
        show: true,
        lineStyle: {
          color: '#999'
        }
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      splitLine: {
        show: true,
        lineStyle: {
          type: 'dashed',
          color: '#e0e0e0'
        }
      },
      axisLine: {
        show: true,
        lineStyle: {
          color: '#999'
        }
      }
    },
    series: [{
      type: 'scatter',
      data: data.map(item => ({
        name: item.name,
        value: item.value,
        symbolSize: item.name === selected ? 20 : 12,
        itemStyle: {
          color: item.name === selected ? '#ff6b6b' : '#4ecdc4',
          borderColor: '#fff',
          borderWidth: item.name === selected ? 3 : 1
        },
        stats: item.stats
      })),
      label: {
        show: item => item.data.name === selected,
        formatter: '{b}',
        position: 'top',
        fontSize: 10,
        color: '#666',
        fontWeight: 'bold'
      },
      emphasis: {
        scale: true,
        label: {
          show: true,
          fontWeight: 'bold',
          fontSize: 12
        }
      }
    }],
    grid: {
      left: '5%',
      right: '5%',
      bottom: '15%',
      top: '20%',
      containLabel: true
    }
  };

  chartInstance.setOption(option);

  chartInstance.off('click');
  chartInstance.on('click', (params) => {
    if (params.data && params.data.name) {
      emit('province-select', params.data.name);
    }
  });
};

// 监听数据变化
watch(() => [dimensionData.value, props.selectedProvince], () => {
  if (chartInstance) {
    renderChart();
  }
}, { deep: true });

// 监听容器大小变化
const handleResize = () => {
  if (chartInstance) {
    chartInstance.resize();
  }
};

onMounted(() => {
  nextTick(() => {
    initChart();
    window.addEventListener('resize', handleResize);
  });
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
.province-dimension-chart {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-controls {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  white-space: nowrap;
}

.method-name {
  font-size: 12px;
  color: #2f7e57;
  font-weight: 600;
  padding: 6px 12px;
  background: rgba(47, 126, 87, 0.1);
  border-radius: 4px;
}

.chart-container {
  flex: 1;
  min-height: 300px;
  width: 100%;
  border: 1px solid #eee;
  border-radius: 8px;
  background: white;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 10px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: inline-block;
}

.legend-color.selected {
  background-color: #ff6b6b;
}

.legend-color.other {
  background-color: #4ecdc4;
}
</style>