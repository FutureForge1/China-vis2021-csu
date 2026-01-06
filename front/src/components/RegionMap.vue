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
        <div class="info-row">
          <span class="label">CODE</span>
          <span class="val">{{ selectedRegion.code }}</span>
        </div>
        <div class="info-row">
          <span class="label">COORDINATES</span>
          <span class="val">{{ selectedRegion.longitude }}, {{ selectedRegion.latitude }}</span>
        </div>
        <div class="info-row">
          <span class="label">ZIP CODE</span>
          <span class="val">{{ selectedRegion.zipCode }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import * as echarts from 'echarts'
import { computed, onMounted, ref, watch } from 'vue'

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
  { value: 'province', label: 'PROVINCE' },
  { value: 'city', label: 'CITY' },
  { value: 'county', label: 'COUNTY' }
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
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#FFE600',
      borderWidth: 1,
      textStyle: { color: '#0a0a0a', fontFamily: 'JetBrains Mono' },
      formatter: function (params) {
        return `
          <div style="font-weight: bold; color: #FFE600; border-bottom: 1px solid #ddd; margin-bottom: 4px;">${params.name}</div>
          <div>LNG: ${params.data.longitude}</div>
          <div>LAT: ${params.data.latitude}</div>
          <div>ZIP: ${params.data.zipCode}</div>
        `
      }
    },
    visualMap: {
      type: 'continuous',
      min: 0,
      max: 100,
      left: 'left',
      top: 'bottom',
      text: ['HIGH', 'LOW'],
      calculable: true,
      textStyle: { color: '#666', fontFamily: 'JetBrains Mono' },
      inRange: {
        color: ['#ddd333', '#4d4500', '#665c00', '#998a00', '#ccb800', '#FFE600']
      }
    },
    series: [{
      name: 'REGION',
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
        position: 'right',
        color: '#0a0a0a',
        fontFamily: 'JetBrains Mono'
      },
      emphasis: {
        focus: 'series',
        label: {
          show: true
        }
      },
      itemStyle: {
        borderColor: '#000',
        borderWidth: 1
      }
    }],
    geo: {
      map: 'China',
      roam: true,
      emphasis: {
        areaColor: '#FFE600',
        label: { color: '#000' }
      },
      itemStyle: {
        areaColor: '#1a1a1a',
        borderColor: '#ddd'
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
  background: transparent;
  overflow: hidden;
}

.map-controls {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 100;
  background: rgba(0, 0, 0, 0.8);
  padding: 4px;
  border: 1px solid #ddd;
}

.map-controls button {
  background: transparent;
  color: #666;
  border: none;
  padding: 4px 12px;
  margin: 0 2px;
  cursor: pointer;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  transition: all 0.2s;
}

.map-controls button:hover {
  color: #0a0a0a;
  background: rgba(0,0,0,0.1);
}

.map-controls button.active {
  background: #FFE600;
  color: #000;
  font-weight: bold;
}

.map-area {
  width: 100%;
  height: 100%;
}

.region-info-panel {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.9);
  color: white;
  padding: 12px;
  border: 1px solid #ddd;
  max-width: 300px;
  z-index: 100;
}

.region-info-panel h3 {
  margin: 0 0 8px 0;
  color: #FFE600;
  font-family: "Oswald", sans-serif;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
  text-transform: uppercase;
}

.region-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
}

.label {
  color: #666;
}

.val {
  color: #0a0a0a;
  font-weight: bold;
}
</style>