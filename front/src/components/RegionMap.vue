<template>
  <div class="region-map-container">
    <div class="map-controls">
      <button
        v-for="level in adminLevels"
        :key="level.value"
        :class="{ active: currentLevel === level.value }"
        @click="currentLevel = level.value"
      >
        {{ level.label }}
      </button>
    </div>

    <div ref="mapContainer" class="map-area"></div>

    <div class="region-info-panel" v-if="selectedRegion">
      <h3>{{ selectedRegion.name }}</h3>
      <div class="region-details">
        <p><strong>行政区划代码:</strong> {{ selectedRegion.code }}</p>
        <p><strong>经纬度:</strong> {{ selectedRegion.longitude }}, {{ selectedRegion.latitude }}</p>
        <p><strong>邮政编码:</strong> {{ selectedRegion.zipCode }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  regionData: {
    type: Array,
    default: () => []
  },
  selectedMetric: {
    type: String,
    default: 'pm25'
  }
})

const mapContainer = ref(null)
const currentLevel = ref('province')
const selectedRegion = ref(null)
let chart = null

const adminLevels = [
  { value: 'province', label: '省级' },
  { value: 'city', label: '市级' },
  { value: 'county', label: '县级' }
]

// 处理区域数据，按行政级别分组
const processedData = computed(() => {
  const grouped = {
    province: new Map(),
    city: new Map(),
    county: new Map()
  }

  props.regionData.forEach(item => {
    // 省级数据
    if (item.province && !item.city && !item.county) {
      const key = item.province
      if (!grouped.province.has(key)) {
        grouped.province.set(key, {
          name: item.province,
          value: 1,
          longitude: parseFloat(item.longitude),
          latitude: parseFloat(item.latitude),
          code: item.code || '',
          zipCode: item.zipCode || ''
        })
      }
    }

    // 市级数据
    if (item.province && item.city && !item.county) {
      const key = `${item.province}-${item.city}`
      if (!grouped.city.has(key)) {
        grouped.city.set(key, {
          name: item.city,
          province: item.province,
          value: 1,
          longitude: parseFloat(item.longitude),
          latitude: parseFloat(item.latitude),
          code: item.code || '',
          zipCode: item.zipCode || ''
        })
      }
    }

    // 县级数据
    if (item.province && item.city && item.county) {
      const key = `${item.province}-${item.city}-${item.county}`
      if (!grouped.county.has(key)) {
        grouped.county.set(key, {
          name: item.county,
          province: item.province,
          city: item.city,
          value: 1,
          longitude: parseFloat(item.longitude),
          latitude: parseFloat(item.latitude),
          code: item.code || '',
          zipCode: item.zipCode || ''
        })
      }
    }
  })

  return grouped
})

const initMap = () => {
  if (!mapContainer.value) return

  chart = echarts.init(mapContainer.value)

  const currentData = Array.from(processedData.value[currentLevel.value].values())

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: function (params) {
        return `
          <div style="font-weight: bold;">${params.name}</div>
          <div>经度: ${params.data.longitude}</div>
          <div>纬度: ${params.data.latitude}</div>
          <div>邮编: ${params.data.zipCode}</div>
        `
      }
    },
    visualMap: {
      type: 'continuous',
      min: 0,
      max: 100,
      left: 'left',
      top: 'bottom',
      text: ['高', '低'],
      calculable: true,
      inRange: {
        color: ['#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#fee090', '#fdae61', '#f46d43', '#d73027']
      }
    },
    series: [{
      name: '行政区划',
      type: 'scatter',
      coordinateSystem: 'geo',
      data: currentData,
      symbolSize: function (val) {
        return Math.sqrt(val[2]) * 4
      },
      encode: {
        value: 2,
        lng: 'longitude',
        lat: 'latitude'
      },
      label: {
        show: true,
        formatter: '{b}',
        position: 'right'
      },
      emphasis: {
        focus: 'series',
        label: {
          show: true
        }
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
      }
    }],
    geo: {
      map: 'China',
      roam: true,
      emphasis: {
        areaColor: '#fbb03b'
      },
      itemStyle: {
        areaColor: '#323c48',
        borderColor: '#111'
      }
    }
  }

  chart.setOption(option)

  // 添加点击事件
  chart.on('click', (params) => {
    selectedRegion.value = params.data
  })
}

onMounted(() => {
  initMap()
})

watch([() => currentLevel.value, () => props.regionData], () => {
  if (chart) {
    initMap()
  }
})

// 响应窗口大小变化
const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

// 清理
import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (chart) {
    chart.dispose()
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.region-map-container {
  position: relative;
  width: 100%;
  height: 600px;
  background: #1a1a1a;
  border-radius: 8px;
  overflow: hidden;
}

.map-controls {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 100;
  background: rgba(0, 0, 0, 0.7);
  padding: 10px;
  border-radius: 4px;
}

.map-controls button {
  background: #333;
  color: white;
  border: none;
  padding: 5px 10px;
  margin: 0 2px;
  border-radius: 3px;
  cursor: pointer;
}

.map-controls button.active {
  background: #1890ff;
}

.map-area {
  width: 100%;
  height: 100%;
}

.region-info-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 15px;
  border-radius: 4px;
  max-width: 300px;
  z-index: 100;
}

.region-info-panel h3 {
  margin: 0 0 10px 0;
  color: #1890ff;
}

.region-details p {
  margin: 5px 0;
  font-size: 12px;
}
</style>