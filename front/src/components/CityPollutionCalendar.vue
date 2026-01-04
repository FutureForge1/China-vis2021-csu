<template>
  <div class="city-calendar-wrap">
    <div class="section-heading">
      <div class="section-badge">城市污染日历</div>
      <div class="section-meta">全年每日 AQI 热力图</div>
    </div>

    <!-- 选择器区域 -->
    <div class="selectors">
      <div class="selector-group">
        <label>年份：</label>
        <select v-model="selectedYear" @change="onYearChange">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>省份：</label>
        <select v-model="selectedProvince" @change="onProvinceChange">
          <option value="">请选择省份</option>
          <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>城市：</label>
        <select v-model="selectedCity" @change="onCityChange" :disabled="!selectedProvince">
          <option value="">请选择城市</option>
          <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <span>正在加载数据...</span>
    </div>

    <!-- 日历图表 -->
    <div v-else-if="calendarData.length > 0" class="chart-container">
      <VChart :option="chartOption" autoresize class="calendar-chart" />
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>请选择年份、省份和城市查看污染日历</p>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="legend-title">AQI等级：</span>
      <span class="legend-item" style="--color: #22c55e">■ 优(0-50)</span>
      <span class="legend-item" style="--color: #a3e635">■ 良(51-100)</span>
      <span class="legend-item" style="--color: #facc15">■ 轻度(101-150)</span>
      <span class="legend-item" style="--color: #f97316">■ 中度(151-200)</span>
      <span class="legend-item" style="--color: #ef4444">■ 重度(201-300)</span>
      <span class="legend-item" style="--color: #7f1d1d">■ 严重(>300)</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue";
import {
  loadAvailableYears,
  getCitiesByProvince,
  computeCityYearCalendar,
} from "../utils/dataLoader";

// 响应式状态
const availableYears = ref([]);
const provinceCityMap = ref({});
const selectedYear = ref("");
const selectedProvince = ref("");
const selectedCity = ref("");
const calendarData = ref([]);
const loading = ref(false);

// 计算属性
const provinces = computed(() => Object.keys(provinceCityMap.value).sort());
const cities = computed(() => {
  if (!selectedProvince.value) return [];
  return provinceCityMap.value[selectedProvince.value] || [];
});

// 图表配置
const chartOption = computed(() => {
  if (!calendarData.value.length || !selectedYear.value) return {};

  const year = selectedYear.value;
  
  // 转换数据为 ECharts 日历格式: [日期, AQI值]
  const heatmapData = calendarData.value.map((d) => [d.date, d.aqi]);

  return {
    backgroundColor: "transparent",
    tooltip: {
      formatter: (params) => {
        const date = params.data[0];
        const dayData = calendarData.value.find((d) => d.date === date);
        if (!dayData) return "";

        const dateObj = new Date(date);
        const dateStr = `${dateObj.getFullYear()}年${dateObj.getMonth() + 1}月${dateObj.getDate()}日`;

        return `
          <div style="font-weight: bold; margin-bottom: 8px;">${dateStr}</div>
          <div style="color: ${dayData.color}; font-size: 16px; margin-bottom: 8px;">
            AQI: ${dayData.aqi} (${dayData.level})
          </div>
          <div style="font-size: 12px; color: #999; margin-bottom: 4px;">首要污染物: ${dayData.primaryPollutant}</div>
          <hr style="border: none; border-top: 1px solid #444; margin: 8px 0;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 12px;">
            <span>PM2.5: ${dayData.pm25} µg/m³</span>
            <span>PM10: ${dayData.pm10} µg/m³</span>
            <span>SO₂: ${dayData.so2} µg/m³</span>
            <span>NO₂: ${dayData.no2} µg/m³</span>
            <span>CO: ${dayData.co} mg/m³</span>
            <span>O₃: ${dayData.o3} µg/m³</span>
          </div>
        `;
      },
    },
    visualMap: {
      min: 0,
      max: 300,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 10,
      inRange: {
        color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
      },
      textStyle: { color: "#374151" },
    },
    calendar: {
      top: 60,
      left: 40,
      right: 40,
      cellSize: ["auto", 16],
      range: year,
      itemStyle: {
        borderWidth: 1,
        borderColor: "#e5e7eb",
      },
      splitLine: {
        lineStyle: { color: "#d1d5db", width: 2 },
      },
      yearLabel: { show: true, color: "#374151" },
      monthLabel: { color: "#6b7280", nameMap: "cn" },
      dayLabel: { 
        color: "#6b7280", 
        firstDay: 1,
        nameMap: ["日", "一", "二", "三", "四", "五", "六"]
      },
    },
    series: [
      {
        type: "heatmap",
        coordinateSystem: "calendar",
        data: heatmapData,
      },
    ],
  };
});

// 事件处理
async function onYearChange() {
  selectedProvince.value = "";
  selectedCity.value = "";
  calendarData.value = [];
  
  if (selectedYear.value) {
    loading.value = true;
    try {
      provinceCityMap.value = await getCitiesByProvince(selectedYear.value);
    } catch (e) {
      console.error("加载省份城市列表失败:", e);
    }
    loading.value = false;
  }
}

function onProvinceChange() {
  selectedCity.value = "";
  calendarData.value = [];
}

async function onCityChange() {
  if (!selectedYear.value || !selectedCity.value) return;

  loading.value = true;
  try {
    calendarData.value = await computeCityYearCalendar(
      selectedYear.value,
      selectedCity.value
    );
  } catch (e) {
    console.error("加载日历数据失败:", e);
    calendarData.value = [];
  }
  loading.value = false;
}

// 初始化
onMounted(async () => {
  try {
    availableYears.value = await loadAvailableYears();
    if (availableYears.value.length > 0) {
      selectedYear.value = availableYears.value[0];
      await onYearChange();
    }
  } catch (e) {
    console.error("初始化失败:", e);
  }
});
</script>

<style scoped>
.city-calendar-wrap {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border: 1px solid #e2e8f0;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-badge {
  background: linear-gradient(135deg, #238636, #2ea043);
  color: #fff;
  padding: 4px 12px;
  border-radius: 16px;
  font-weight: 600;
  font-size: 14px;
}

.section-meta {
  color: #6b7280;
  font-size: 13px;
}

.selectors {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selector-group label {
  color: #374151;
  font-size: 13px;
  white-space: nowrap;
}

.selector-group select {
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  min-width: 140px;
  cursor: pointer;
}

.selector-group select:focus {
  outline: none;
  border-color: #388bfd;
}

.selector-group select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 60px;
  color: #6b7280;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid #e5e7eb;
  border-top-color: #2f7e57;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.chart-container {
  background: #ffffff;
  border-radius: 8px;
  padding: 12px;
  border: 1px solid #e5e7eb;
}

.calendar-chart {
  height: 220px;
  width: 100%;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px;
  color: #9ca3af;
  font-size: 14px;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: #ffffff;
  border-radius: 8px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
}

.legend-title {
  color: #374151;
  font-weight: 500;
}

.legend-item {
  color: var(--color);
}
</style>
