<template>
  <div class="city-calendar-wrap">
    <div class="section-heading">
      <div class="section-badge">CITY CALENDAR</div>
      <div class="section-meta">YEARLY AQI HEATMAP</div>
    </div>

    <!-- Selectors -->
    <div class="selectors">
      <div class="selector-group">
        <label>YEAR:</label>
        <select v-model="selectedYear" @change="onYearChange">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>PROVINCE:</label>
        <select v-model="selectedProvince" @change="onProvinceChange">
          <option value="">SELECT PROVINCE</option>
          <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>CITY:</label>
        <select v-model="selectedCity" @change="onCityChange" :disabled="!selectedProvince">
          <option value="">SELECT CITY</option>
          <option v-for="c in cities" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading">
      <span class="spinner"></span>
      <span>LOADING DATA...</span>
    </div>

    <!-- Chart -->
    <div v-else-if="calendarData.length > 0" class="chart-container">
      <VChart :option="chartOption" autoresize class="calendar-chart" />
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>SELECT YEAR, PROVINCE AND CITY TO VIEW CALENDAR</p>
    </div>

    <!-- Legend -->
    <div class="legend">
      <span class="legend-title">AQI LEVEL:</span>
      <span class="legend-item" style="--color: #22c55e">■ EXCELLENT</span>
      <span class="legend-item" style="--color: #a3e635">■ GOOD</span>
      <span class="legend-item" style="--color: #facc15">■ LIGHT</span>
      <span class="legend-item" style="--color: #f97316">■ MODERATE</span>
      <span class="legend-item" style="--color: #ef4444">■ HEAVY</span>
      <span class="legend-item" style="--color: #7f1d1d">■ SEVERE</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import {
    computeCityYearCalendar,
    getCitiesByProvince,
    loadAvailableYears,
} from "../utils/dataLoader";

// State
const availableYears = ref([]);
const provinceCityMap = ref({});
const selectedYear = ref("");
const selectedProvince = ref("");
const selectedCity = ref("");
const calendarData = ref([]);
const loading = ref(false);

// Computed
const provinces = computed(() => Object.keys(provinceCityMap.value).sort());
const cities = computed(() => {
  if (!selectedProvince.value) return [];
  return provinceCityMap.value[selectedProvince.value] || [];
});

// Chart Option
const chartOption = computed(() => {
  if (!calendarData.value.length || !selectedYear.value) return {};

  const year = selectedYear.value;
  const heatmapData = calendarData.value.map((d) => [d.date, d.aqi]);

  return {
    backgroundColor: "transparent",
    tooltip: {
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (params) => {
        const date = params.data[0];
        const dayData = calendarData.value.find((d) => d.date === date);
        if (!dayData) return "";

        const dateObj = new Date(date);
        const dateStr = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}-${String(dateObj.getDate()).padStart(2, '0')}`;

        return `
          <div style="font-weight: bold; margin-bottom: 8px; font-family: 'Oswald'">${dateStr}</div>
          <div style="color: ${dayData.color}; font-size: 16px; margin-bottom: 8px;">
            AQI: ${dayData.aqi} (${dayData.level})
          </div>
          <div style="font-size: 12px; color: #666; margin-bottom: 4px;">PRIMARY: ${dayData.primaryPollutant}</div>
          <hr style="border: none; border-top: 1px solid #444; margin: 8px 0;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 12px;">
            <span>PM2.5: ${dayData.pm25}</span>
            <span>PM10: ${dayData.pm10}</span>
            <span>SO₂: ${dayData.so2}</span>
            <span>NO₂: ${dayData.no2}</span>
            <span>CO: ${dayData.co}</span>
            <span>O₃: ${dayData.o3}</span>
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
      bottom: 0,
      inRange: {
        color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
      },
      textStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
    },
    calendar: {
      top: 40,
      left: 30,
      right: 30,
      cellSize: ["auto", 16],
      range: year,
      itemStyle: {
        borderWidth: 1,
        borderColor: "#1a1a1a",
        color: "transparent"
      },
      splitLine: {
        lineStyle: { color: "#ddd", width: 1 },
      },
      yearLabel: { show: true, color: "#0a0a0a", fontFamily: 'Oswald' },
      monthLabel: { color: "#666", fontFamily: 'JetBrains Mono', nameMap: 'en' },
      dayLabel: { 
        color: "#666", 
        firstDay: 1,
        fontFamily: 'JetBrains Mono',
        nameMap: 'en'
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

// Handlers
async function onYearChange() {
  selectedProvince.value = "";
  selectedCity.value = "";
  calendarData.value = [];
  
  if (selectedYear.value) {
    loading.value = true;
    try {
      provinceCityMap.value = await getCitiesByProvince(selectedYear.value);
    } catch (e) {
      console.error("Failed to load cities:", e);
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
    console.error("Failed to load calendar data:", e);
    calendarData.value = [];
  }
  loading.value = false;
}

// Init
onMounted(async () => {
  try {
    availableYears.value = await loadAvailableYears();
    if (availableYears.value.length > 0) {
      selectedYear.value = availableYears.value[0];
      await onYearChange();
    }
  } catch (e) {
    console.error("Init failed:", e);
  }
});
</script>

<style scoped>
.city-calendar-wrap {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 10px;
}

.section-badge {
  background: var(--c-yellow);
  color: var(--c-black);
  padding: 4px 12px;
  font-weight: 700;
  font-size: 14px;
  font-family: var(--font-display);
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}

.section-meta {
  color: var(--c-gray);
  font-size: 12px;
  font-family: var(--font-mono);
  text-transform: uppercase;
}

.selectors {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.selector-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.selector-group label {
  color: var(--c-gray);
  font-size: 12px;
  font-family: var(--font-mono);
}

.selector-group select {
  background: rgba(0, 0, 0, 0.3);
  color: var(--c-white);
  border: 1px solid var(--c-border);
  padding: 4px 8px;
  font-size: 12px;
  font-family: var(--font-mono);
  min-width: 120px;
  cursor: pointer;
}

.selector-group select:focus {
  outline: none;
  border-color: var(--c-yellow);
}

.loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--c-gray);
  font-family: var(--font-mono);
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--c-yellow);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.chart-container {
  border: 1px solid var(--c-border);
  padding: 10px;
  background: rgba(0, 0, 0, 0.2);
}

.calendar-chart {
  height: 220px;
  width: 100%;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: var(--c-gray);
  font-size: 12px;
  font-family: var(--font-mono);
  border: 1px dashed var(--c-border);
}

.legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
  font-size: 10px;
  font-family: var(--font-mono);
}

.legend-title {
  color: var(--c-gray);
  font-weight: bold;
}

.legend-item {
  color: var(--c-white);
}
</style>
