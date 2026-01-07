<template>
  <div class="force-layout-chart">
    <div ref="chartContainer" class="chart-container"></div>
    <div class="chart-legend">
      <div class="legend-item" v-for="pollutant in pollutants" :key="pollutant.name">
        <span class="legend-color" :style="{ backgroundColor: pollutant.color }"></span>
        <span>{{ pollutant.label }}</span>
        <span class="legend-value" v-if="selectedProvince">
          {{ getPollutantValue(selectedProvince, pollutant.name) }}
        </span>
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

const pollutants = [
  { name: 'pm25', label: 'PM2.5', color: '#ff6b6b' },
  { name: 'pm10', label: 'PM10', color: '#4ecdc4' },
  { name: 'so2', label: 'SO₂', color: '#45b7d1' },
  { name: 'no2', label: 'NO₂', color: '#96ceb4' },
  { name: 'co', label: 'CO', color: '#feca57' },
  { name: 'o3', label: 'O₃', color: '#ff9ff3' }
];

const initializeChart = () => {
  if (!chartContainer.value) return;

  chartInstance = echarts.init(chartContainer.value);

  const nodes = props.data.map((item, index) => ({
    id: item.province,
    name: item.province,
    value: pollutants.map(p => item[p.name] || 0),
    symbolSize: 10 + Math.random() * 20,
  }));

  const edges = [];
  nodes.forEach((source, i) => {
    nodes.forEach((target, j) => {
      if (i !== j) {
        edges.push({
          source: source.id,
          target: target.id,
          value: Math.random(),
        });
      }
    });
  });

  const option = {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: edges,
        roam: true,
        label: {
          show: true,
          position: 'right',
          formatter: '{b}'
        },
        force: {
          repulsion: 100,
          gravity: 0.1,
          edgeLength: [50, 100]
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3
        }
      }
    ]
  };

  chartInstance.setOption(option);
};

onMounted(() => {
  initializeChart();
});

onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose();
  }
});
</script>

<style scoped>
.force-layout-chart {
  width: 100%;
  height: 700px;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  border: 1px solid #e0e0e0;
  position: relative;
}

.chart-container {
  flex: 1;
  min-height: 550px;
  background: #fff;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}

.chart-legend {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 15px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
  font-size: 11px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.legend-color {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  display: inline-block;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.legend-value {
  font-weight: bold;
  color: #2f7e57;
  margin-left: auto;
  font-family: 'Courier New', monospace;
}
</style>