<template>
  <div class="icicle-chart">
    <div ref="chartContainer" class="chart-container"></div>
    <div class="chart-controls">
      <div class="control-group">
        <label>视图模式：</label>
        <select v-model="viewMode" @change="handleViewModeChange">
          <option value="current">当前污染物 ({{ currentMetricLabel }})</option>
          <option value="comprehensive">综合污染指数</option>
        </select>
      </div>
      <div class="control-group" v-if="viewMode === 'comprehensive'">
        <label>权重设置：</label>
        <select v-model="weightMode">
          <option value="equal">等权重</option>
          <option value="aqi">AQI标准权重</option>
        </select>
      </div>
    </div>
    <div class="chart-legend">
      <div class="legend-scale">
        <span>优</span>
        <div class="scale-bar">
          <div class="scale-segment" style="background-color: #00e400"></div>
          <div class="scale-segment" style="background-color: #ffff00"></div>
          <div class="scale-segment" style="background-color: #ff7e00"></div>
          <div class="scale-segment" style="background-color: #ff0000"></div>
          <div class="scale-segment" style="background-color: #8f3f97"></div>
          <div class="scale-segment" style="background-color: #7e0023"></div>
        </div>
        <span>严重污染</span>
      </div>
      <div class="legend-stats">
        <span>当前视图：{{ currentLevel === 'national' ? '全国' : currentProvince }}</span>
        <span v-if="selectedNode">污染指数：{{ selectedNodeValue.toFixed(2) }}</span>
        <button
          v-if="currentLevel === 'province'"
          @click="backToNationalView"
          class="back-button"
        >
          返回全国视图
        </button>
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
  selectedRegion: {
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

const emit = defineEmits(['region-select']);

const chartContainer = ref(null);
let chartInstance = null;

// 视图模式
const viewMode = ref('current');
const weightMode = ref('equal');

// 污染物配置
const pollutants = [
  { name: 'pm25', label: 'PM2.5', standard: 35, weight: 1.0 },
  { name: 'pm10', label: 'PM10', standard: 50, weight: 0.8 },
  { name: 'so2', label: 'SO₂', standard: 150, weight: 0.6 },
  { name: 'no2', label: 'NO₂', standard: 100, weight: 0.7 },
  { name: 'co', label: 'CO', standard: 4, weight: 0.5 },
  { name: 'o3', label: 'O₃₃', standard: 160, weight: 0.9 }
];


// 更新颜色尺度定义
const colorScale = [
  '#00C800', '#FFD700', '#FF8C00', '#FF4500', '#9932CC', '#8B0000'
];

// 新增：层级状态控制
const currentLevel = ref('national'); // national, province
const currentProvince = ref(''); // 当前选中的省份

// 选中的节点
const selectedNode = ref(null);

// 计算当前指标标签
const currentMetricLabel = computed(() => {
  const metricMap = {
    pm25: 'PM2.5', pm10: 'PM10', so2: 'SO₂',
    no2: 'NO₂', co: 'CO', o3: 'O₃₃'
  };
  return metricMap[props.metric] || props.metric.toUpperCase();
});

// 修正：正确的污染指数计算
const computePollutionIndex = (value, pollutant, mode = 'current') => {
  if (mode === 'current') {
    const standards = {
      pm25: 35, pm10: 50, so2: 150, no2: 100, co: 4, o3: 160
    };
    const standard = standards[pollutant] || 35;
    return Math.min(value / standard, 5);
  } else {
    return value;
  }
};

// 修正：正确的综合污染指数计算
const computeComprehensiveIndex = (averages, mode = 'equal') => {
  let weights = {};

  if (mode === 'equal') {
    pollutants.forEach(p => { weights[p.name] = 1; });
  } else {
    pollutants.forEach(p => { weights[p.name] = p.weight; });
  }

  let totalWeight = 0;
  let weightedSum = 0;

  pollutants.forEach(pollutant => {
    const value = averages[pollutant.name] || 0;
    if (value > 0) {
      const normalized = Math.min(value / pollutant.standard, 5);
      weightedSum += normalized * weights[pollutant.name];
      totalWeight += weights[pollutant.name];
    }
  });

  return totalWeight > 0 ? weightedSum / totalWeight : 0;
};

// 修正：按照AQI标准的颜色映射函数（提高对比度）
const getColorByValue = (value) => {
  // AQI标准分级 - 使用更鲜明的颜色
  const aqiLevels = [
    { max: 1.0, color: '#00C800', label: '优' },      // 更亮的绿色
    { max: 2.0, color: '#FFD700', label: '良' },      // 更亮的黄色
    { max: 3.0, color: '#FF8C00', label: '轻度污染' }, // 更亮的橙色
    { max: 4.0, color: '#FF4500', label: '中度污染' }, // 更亮的红色
    { max: 5.0, color: '#9932CC', label: '重度污染' }, // 更亮的紫色
    { max: Infinity, color: '#8B0000', label: '严重污染' } // 更深的红色
  ];

  for (let i = 0; i < aqiLevels.length; i++) {
    if (value <= aqiLevels[i].max) {
      return aqiLevels[i].color;
    }
  }

  return aqiLevels[aqiLevels.length - 1].color;
};

// 颜色插值函数
const interpolateColor = (color1, color2, ratio) => {
  const r1 = parseInt(color1.substr(1, 2), 16);
  const g1 = parseInt(color1.substr(3, 2), 16);
  const b1 = parseInt(color1.substr(5, 2), 16);

  const r2 = parseInt(color2.substr(1, 2), 16);
  const g2 = parseInt(color2.substr(3, 2), 16);
  const b2 = parseInt(color2.substr(5, 2), 16);

  const r = Math.round(r1 + (r2 - r1) * ratio);
  const g = Math.round(g1 + (g2 - g1) * ratio);
  const b = Math.round(b1 + (b2 - b1) * ratio);

  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
};

// 修改：构建正确的矩阵式冰柱图数据
const icicleData = computed(() => {
  if (!props.data.length) return null;

  // 1. 按城市聚合数据 - 保持不变
  const cityData = {};
  props.data.forEach(item => {
    if (!item.city || !item.province) return;

    const cityKey = `${item.province}-${item.city}`;
    if (!cityData[cityKey]) {
      cityData[cityKey] = {
        province: item.province,
        city: item.city,
        values: {},
        count: 0
      };
    }

    const city = cityData[cityKey];
    pollutants.forEach(pollutant => {
      const value = item[pollutant.name] || item[`${pollutant.name}_mean`] || 0;
      const numValue = Number(value);
      if (!isNaN(numValue) && numValue > 0) {
        if (!city.values[pollutant.name]) {
          city.values[pollutant.name] = [];
        }
        city.values[pollutant.name].push(numValue);
      }
    });
    city.count++;
  });

  // 2. 计算城市平均值和污染指数 - 保持不变
  const cities = Object.values(cityData)
    .filter(city => city.count > 0)
    .map(city => {
      const averages = {};
      pollutants.forEach(pollutant => {
        const values = city.values[pollutant.name] || [];
        averages[pollutant.name] = values.length > 0
          ? values.reduce((a, b) => a + b) / values.length
          : 0;
      });

      const pollutionValue = viewMode.value === 'current'
        ? computePollutionIndex(averages[props.metric] || 0, props.metric)
        : computeComprehensiveIndex(averages, weightMode.value);

      return {
        ...city,
        averages,
        value: pollutionValue,
        color: getColorByValue(pollutionValue)
      };
    });

  // 3. 按省份聚合城市数据 - 修改为计算平均值而不是总和
  const provinceData = {};
  cities.forEach(city => {
    if (!provinceData[city.province]) {
      provinceData[city.province] = {
        province: city.province,
        cities: [],
        totalValue: 0,
        count: 0
      };
    }
    provinceData[city.province].cities.push(city);
    provinceData[city.province].totalValue += city.value;
    provinceData[city.province].count++;
  });

  // 4. 计算全国平均值 - 修改为平均值
  const allProvinceValues = Object.values(provinceData).map(province =>
    province.count > 0 ? province.totalValue / province.count : 0
  );
  const nationalAvgValue = allProvinceValues.length > 0
    ? allProvinceValues.reduce((a, b) => a + b) / allProvinceValues.length
    : 0;

  // 构建基础数据项 - 修改为使用平均值
  const nationalItem = {
    name: '全国',
    value: nationalAvgValue,
    color: getColorByValue(nationalAvgValue),
    level: 0
  };

  const provinceItems = Object.values(provinceData).map(province => ({
    name: province.province,
    value: province.count > 0 ? province.totalValue / province.count : 0,
    color: getColorByValue(province.count > 0 ? province.totalValue / province.count : 0),
    level: 1,
    cityCount: province.count
  }));

  const cityItems = cities.map(city => ({
    name: city.city,
    value: city.value,
    color: city.color,
    level: 2,
    province: city.province,
    averages: city.averages
  }));

  // 5. 根据当前层级构建不同的数据结构 - 修改为使用平均值
  if (currentLevel.value === 'province' && currentProvince.value) {
    const provinceItem = provinceItems.find(p => p.name === currentProvince.value);
    if (!provinceItem) {
      return {
        national: nationalItem,
        provinces: provinceItems,
        cities: cityItems,
        stats: {
          nationalValue: nationalAvgValue,
          provinceCount: provinceItems.length,
          cityCount: cityItems.length,
          maxValue: Math.max(...cityItems.map(c => c.value), ...provinceItems.map(p => p.value), nationalAvgValue)
        }
      };
    }

    const provinceCities = cityItems.filter(city => city.province === currentProvince.value);
    const provinceCityAvg = provinceCities.length > 0
      ? provinceCities.reduce((sum, city) => sum + city.value, 0) / provinceCities.length
      : 0;

    return {
      national: {
        ...provinceItem,
        name: currentProvince.value,
        level: 0,
        value: provinceItem.value
      },
      provinces: provinceCities.map(city => ({
        ...city,
        level: 1
      })),
      cities: [],
      stats: {
        nationalValue: provinceItem.value,
        provinceCount: provinceCities.length,
        cityCount: 0,
        maxValue: Math.max(...provinceCities.map(c => c.value), provinceItem.value)
      }
    };
  } else {
    return {
      national: nationalItem,
      provinces: provinceItems,
      cities: cityItems,
      stats: {
        nationalValue: nationalAvgValue,
        provinceCount: provinceItems.length,
        cityCount: cityItems.length,
        maxValue: Math.max(...cityItems.map(c => c.value), ...provinceItems.map(p => p.value), nationalAvgValue)
      }
    };
  }
});

// 选中的节点值
const selectedNodeValue = computed(() => {
  if (!selectedNode.value) return icicleData.value?.national.value || 0;
  return selectedNode.value.value || 0;
});

// 新增：处理省份选择
const handleProvinceSelect = (provinceName) => {
  if (currentLevel.value === 'national') {
    currentLevel.value = 'province';
    currentProvince.value = provinceName;
    selectedNode.value = { name: provinceName, level: 1 };
    emit('region-select', provinceName);
  }
};

// 新增：返回全国视图
const backToNationalView = () => {
  currentLevel.value = 'national';
  currentProvince.value = '';
  selectedNode.value = null;
  emit('region-select', '');
};

// 处理视图模式变化
const handleViewModeChange = () => {
  renderChart();
};

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return;

  if (chartInstance) {
    chartInstance.dispose();
  }

  chartInstance = echarts.init(chartContainer.value);

  // 设置点击事件监听器
  chartInstance.off('click');
  chartInstance.on('click', (params) => {
    if (params.data) {
      selectedNode.value = params.data;

      if (params.data.level === 1 && currentLevel.value === 'national') {
        // 在全国视图下点击省份，切换到省份视图
        handleProvinceSelect(params.data.name);
      } else if (params.data.level === 0 && currentLevel.value === 'province') {
        // 在省份视图下点击省份名称，返回全国视图
        backToNationalView();
      } else if (params.data.level === 2) {
        // 点击城市（在省份视图下）
        emit('region-select', params.data.name);
      } else if (params.data.level === 0 && currentLevel.value === 'national') {
        // 点击全国，重置选择
        emit('region-select', '');
      }
    }
  });

  renderChart();
};

// 修正：使用矩阵式布局渲染图表
const renderChart = () => {
  if (!chartInstance || !icicleData.value) return;

  const { national, provinces, cities, stats } = icicleData.value;

  // 修改：调整布局参数
  const ROW_HEIGHT = 100;
  const ROW_GAP = 2;

  // 修正：根据层级动态计算高度
  const CHART_HEIGHT = currentLevel.value === 'national'
    ? ROW_HEIGHT * 2 + ROW_GAP
    : ROW_HEIGHT * 3 + ROW_GAP * 2;

  // 构建矩阵数据
  const matrixData = [
    {
      name: national.name,
      value: national.value,
      itemStyle: { color: national.color },
      layout: {
        x: 0,
        y: 0,
        width: 100,
        height: ROW_HEIGHT,
        level: 0
      }
    }
  ];

  // 修正：第二层布局计算 - 使用正确的宽度计算
  let currentX = 0;
  const totalValue = provinces.reduce((sum, province) => sum + province.value, 0);

  provinces.forEach((province) => {
    // 修正：使用相对于总值的比例计算宽度
    const width = totalValue > 0 ? (province.value / totalValue) * 100 : 0;

    const item = {
      ...province,
      layout: {
        x: currentX,
        y: ROW_HEIGHT + ROW_GAP,
        width: Math.max(width, 3), // 确保最小宽度，便于显示
        height: ROW_HEIGHT,
        level: 1
      }
    };

    matrixData.push(item);
    currentX += width;
  });

  // 修正：省份视图的城市层布局计算
  if (currentLevel.value === 'province' && cities.length > 0) {
    const provinceCities = cities.filter(city => city.province === currentProvince.value);

    if (provinceCities.length > 0) {
      const provinceTotalValue = provinceCities.reduce((sum, city) => sum + city.value, 0);
      let cityX = 0;

      provinceCities.forEach((city) => {
        // 修正：城市宽度相对于省份总值计算
        const cityWidth = provinceTotalValue > 0 ? (city.value / provinceTotalValue) * 100 : 0;

        matrixData.push({
          ...city,
          layout: {
            x: cityX,
            y: (ROW_HEIGHT + ROW_GAP) * 2,
            width: Math.max(cityWidth, 10), // 确保最小宽度
            height: ROW_HEIGHT,
            level: 2
          }
        });

        cityX += cityWidth;
      });
    }
  }

  // 修正：文字颜色根据背景色自动调整
  const getTextColor = (backgroundColor) => {
    // 将十六进制颜色转换为RGB
    const hex = backgroundColor.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);

    // 计算亮度（YIQ公式）
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;

    // 根据亮度返回黑色或白色
    return brightness > 128 ? '#000000' : '#ffffff';
  };

  // 修正：获取AQI等级函数
  const getAQILevel = (value) => {
    if (value <= 1.0) return '优';
    if (value <= 2.0) return '良';
    if (value <= 3.0) return '轻度污染';
    if (value <= 4.0) return '中度污染';
    if (value <= 5.0) return '重度污染';
    return '严重污染';
  };

  const option = {
    title: {
      text: currentLevel.value === 'national'
        ? `全国污染程度冰柱图 - ${getAQILevel(national.value)}`
        : `${currentProvince.value}污染程度冰柱图 - ${getAQILevel(national.value)}`,
      subtext: currentLevel.value === 'national'
        ? `显示 ${provinces.length} 个省份 | 平均指数: ${national.value.toFixed(2)}`
        : `显示 ${cities.filter(c => c.province === currentProvince.value).length} 个城市 | 平均指数: ${national.value.toFixed(2)}`,
      left: 'center',
      top: 10,
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#2c3e50'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(info) {
        const value = info.data.value || 0;
        const aqiLevel = getAQILevel(value);
        let tooltip = `
          <div style="text-align: left; padding: 8px; min-width: 200px;">
            <div style="font-size: 14px; font-weight: bold; color: #2c3e50; margin-bottom: 8px;">
              ${info.data.name}
            </div>
            <div style="font-size: 12px; color: #7f8c8d; margin-bottom: 6px;">
              污染指数: <span style="font-weight: bold; color: #e74c3c;">${value.toFixed(2)}</span>
              <span style="margin-left: 8px; padding: 2px 6px; background: ${info.data.color || '#ccc'}; color: ${getTextColor(info.data.color || '#ccc')}; border-radius: 3px; font-size: 10px;">
                ${aqiLevel}
              </span>
            </div>
        `;

        if (info.data.averages) {
          tooltip += `<div style="border-top: 1px solid #ecf0f1; margin: 6px 0; padding-top: 6px;">`;

          if (viewMode.value === 'current') {
            const currentValue = info.data.averages[props.metric] || 0;
            tooltip += `
              <div style="margin: 4px 0; display: flex; justify-content: space-between;">
                <span>${currentMetricLabel.value}:</span>
                <span style="font-weight: bold;">${currentValue.toFixed(1)} μg/m³</span>
              </div>
            `;
          } else {
            pollutants.forEach(pollutant => {
              const val = info.data.averages[pollutant.name] || 0;
              if (val > 0) {
                tooltip += `
                  <div style="margin: 2px 0; display: flex; justify-content: space-between;">
                    <span>${pollutant.label}:</span>
                    <span style="font-weight: bold;">${val.toFixed(1)}</span>
                  </div>
                `;
              }
            });
          }

          tooltip += `</div>`;
        }

        tooltip += `</div>`;
        return tooltip;
      }
    },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      show: false
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: CHART_HEIGHT,
      show: false
    },
    grid: {
      left: 10,
      right: 10,
      bottom: 50,
      top: 60,
      containLabel: false
    },
    series: [{
      type: 'custom',
      renderItem: function(params, api) {
        const item = matrixData[params.dataIndex];
        if (!item || !item.layout) return;

        const x = api.coord([item.layout.x, 0])[0];
        const y = api.coord([0, item.layout.y])[1];
        const width = api.coord([item.layout.width, 0])[0] - api.coord([0, 0])[0];
        const height = item.layout.height;

        // 修正：根据背景色动态计算文字颜色
        const backgroundColor = item.color || item.itemStyle?.color || '#ccc';
        const textColor = getTextColor(backgroundColor);

        return {
          type: 'rect',
          shape: {
            x: x,
            y: y,
            width: Math.max(width, 2), // 确保最小宽度
            height: height
          },
          style: {
            fill: backgroundColor,
            stroke: '#fff',
            lineWidth: 1
          },
          textConfig: {
            position: 'inside'
          },
          textContent: {
            type: 'text',
            style: {
              text: item.name,
              fill: textColor, // 使用动态计算的颜色
              fontSize: item.layout.level === 0 ? 12 : item.layout.level === 1 ? 10 : 8,
              fontWeight: item.layout.level === 0 ? 'bold' : 'normal',
              textShadowColor: 'rgba(0,0,0,0.8)',
              textShadowBlur: 3,
              textShadowOffsetX: 1,
              textShadowOffsetY: 1
            }
          }
        };
      },
      data: matrixData,
      universalTransition: true
    }]
  };

  chartInstance.setOption(option, true);
};

// 监听数据变化
watch(() => [icicleData.value, props.metric, viewMode.value, weightMode.value], () => {
  if (chartInstance) {
    renderChart();
  }
}, { deep: true });

// 新增：监听外部选中的区域变化
watch(() => props.selectedRegion, (newRegion) => {
  if (newRegion && currentLevel.value === 'national') {
    // 如果外部选择了某个省份，且当前是全国视图，则切换到该省份视图
    const provinceData = icicleData.value?.provinces.find(p => p.name === newRegion);
    if (provinceData) {
      currentLevel.value = 'province';
      currentProvince.value = newRegion;
      selectedNode.value = provinceData;
    }
  } else if (!newRegion && currentLevel.value === 'province') {
    // 如果外部重置了选择，且当前是省份视图，则返回全国视图
    backToNationalView();
  }
}, { immediate: true });

// 监听数据变化时重置视图
watch(() => [props.data, props.metric, props.selectedYear, props.selectedMonth], () => {
  // 当数据源变化时，重置为全国视图
  if (currentLevel.value === 'province') {
    backToNationalView();
  }
});

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
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>
.icicle-chart {
  width: 100%;
  height: 600px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border: 1px solid #e0e0e0;
}

.chart-container {
  flex: 1;
  min-height: 450px;
}

.chart-controls {
  display: flex;
  gap: 20px;
  margin: 15px 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.control-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.control-group label {
  font-size: 12px;
  font-weight: 600;
  color: #2c3e50;
}

.control-group select {
  padding: 6px 10px;
  border: 1px solid #bdc3c7;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  color: #2c3e50;
}

.chart-legend {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  padding: 10px;
  background: #ecf0f1;
  border-radius: 4px;
}

.legend-scale {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
  color: #7f8c8d;
}

.scale-bar {
  display: flex;
  width: 150px;
  height: 12px;
  border-radius: 2px;
  overflow: hidden;
}

.scale-segment {
  flex: 1;
}

.legend-stats {
  display: flex;
  gap: 15px;
  font-size: 12px;
  color: #2c3e50;
  align-items: center;
  flex-wrap: wrap;
}

.legend-stats span:last-child {
  font-weight: bold;
  color: #e74c3c;
}

.back-button {
  background: #3498db;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-left: 10px;
  transition: background-color 0.3s;
}

.back-button:hover {
  background: #2980b9;
}
</style>