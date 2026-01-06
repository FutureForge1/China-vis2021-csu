<template>
  <div ref="chartEl" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { onMounted, onUnmounted, watch, ref } from 'vue';
import * as echarts from 'echarts';

const props = defineProps({
  data: Array,
  metric: String,
  selectedProvince: String,
  year: String,
  month: String
});

const chartEl = ref(null);
let chart = null;

// 污染物维度配置
const pollutants = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3'];
const pollutantNames = {
  pm25: 'PM2.5', pm10: 'PM10', so2: 'SO₂',
  no2: 'NO₂', co: 'CO', o3: 'O₃'
};

onMounted(() => {
  chart = echarts.init(chartEl.value);
  renderChart();
});

onUnmounted(() => {
  if (chart) {
    chart.dispose();
  }
});

watch(() => [props.data, props.metric, props.selectedProvince], () => {
  renderChart();
}, { deep: true });

function renderChart() {
  if (!chart || !props.data || props.data.length === 0) return;

  // 按省份聚合数据
  const provinceData = aggregateByProvince(props.data);

  // 计算每个维度的最大值，用于归一化
  const maxValues = calculateMaxValues(provinceData);

  // 生成雷达图指标
  const indicators = pollutants.map(pollutant => ({
    name: pollutantNames[pollutant],
    max: maxValues[pollutant] > 0 ? maxValues[pollutant] * 1.2 : 100 // 留20%余量
  }));

  // 生成系列数据
  const seriesData = generateSeriesData(provinceData, maxValues);

  const option = {
    title: {
      text: `省份污染物径向分析 ${props.year}年${props.month}月`,
      left: 'center',
      textStyle: {
        fontSize: 14,
        color: '#333'
      }
    },
    tooltip: {
      trigger: 'item',
      formatter: function(params) {
        const values = params.data.value.map((v, i) =>
          `${pollutants[i].toUpperCase()}: ${v.toFixed(1)}`
        ).join('<br/>');
        return `${params.name}<br/>${values}`;
      }
    },
    legend: {
      type: 'scroll',
      bottom: 10,
      data: seriesData.map(item => item.name)
    },
    radar: {
      indicator: indicators,
      shape: 'circle',
      splitNumber: 5,
      axisName: {
        color: '#666',
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: ['rgba(0,0,0,0.1)']
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(255,255,255,0.5)', 'rgba(200,200,200,0.1)']
        }
      }
    },
    series: [{
      type: 'radar',
      emphasis: {
        lineStyle: {
          width: 4
        }
      },
      data: seriesData
    }]
  };

  chart.setOption(option);
}

// 按省份聚合数据
function aggregateByProvince(data) {
  const provinceMap = new Map();

  data.forEach(item => {
    const province = item.province;
    if (!provinceMap.has(province)) {
      provinceMap.set(province, {
        province,
        counts: { pm25: 0, pm10: 0, so2: 0, no2: 0, co: 0, o3: 0 },
        sums: { pm25: 0, pm10: 0, so2: 0, no2: 0, co: 0, o3: 0 }
      });
    }

    const provinceData = provinceMap.get(province);
    pollutants.forEach(pollutant => {
      const value = Number(item[pollutant] || item[`${pollutant}_mean`] || 0);
      if (!isNaN(value) && value > 0) {
        provinceData.sums[pollutant] += value;
        provinceData.counts[pollutant]++;
      }
    });
  });

  // 计算平均值
  const result = Array.from(provinceMap.values()).map(provinceData => {
    const averages = {};
    pollutants.forEach(pollutant => {
      averages[pollutant] = provinceData.counts[pollutant] > 0
        ? provinceData.sums[pollutant] / provinceData.counts[pollutant]
        : 0;
    });
    return {
      province: provinceData.province,
      ...averages
    };
  });

  return result;
}

// 计算每个污染物的最大值
function calculateMaxValues(provinceData) {
  const maxValues = {};
  pollutants.forEach(pollutant => {
    const values = provinceData.map(item => item[pollutant]).filter(v => v > 0);
    maxValues[pollutant] = values.length > 0 ? Math.max(...values) : 100;
  });
  return maxValues;
}

// 生成系列数据
function generateSeriesData(provinceData, maxValues) {
  return provinceData.map(province => {
    const values = pollutants.map(pollutant => {
      const value = province[pollutant] || 0;
      return value;
    });

    // 高亮选中的省份
    const isSelected = province.province === props.selectedProvince;

    return {
      name: province.province,
      value: values,
      lineStyle: {
        width: isSelected ? 3 : 1
      },
      itemStyle: {
        color: isSelected ? '#ff6b6b' : null
      },
      areaStyle: isSelected ? {
        color: 'rgba(255, 107, 107, 0.2)'
      } : null
    };
  });
}
</script>