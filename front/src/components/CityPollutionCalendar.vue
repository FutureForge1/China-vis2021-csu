<template>
  <div class="city-calendar-wrap" :class="{ 'full-width': autoLoad }">
    <div class="section-heading" v-if="!autoLoad">
      <div class="section-badge">CITY CALENDAR</div>
      <div class="section-meta">YEARLY AQI HEATMAP</div>
    </div>
    
    <!-- Title for embedded mode -->
    <div class="embedded-header" v-if="autoLoad">
      <h4>YEARLY AQI HEATMAP · {{ displayTitle }}</h4>
    </div>

    <!-- Selectors (Hidden in auto-load mode) -->
    <div class="selectors" v-if="!autoLoad">
      <div class="selector-group">
        <label>YEAR:</label>
        <select v-model="internalSelectedYear" @change="onYearChange">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>PROVINCE:</label>
        <select v-model="internalSelectedProvince" @change="onProvinceChange">
          <option value="">SELECT PROVINCE</option>
          <option v-for="p in provinces" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
      
      <div class="selector-group">
        <label>CITY:</label>
        <select v-model="internalSelectedCity" @change="onCityChange" :disabled="!internalSelectedProvince">
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
      <p>{{ emptyMessage }}</p>
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
import { computed, onMounted, ref, watch } from "vue";
import {
    computeCityYearCalendar,
    getCitiesByProvince,
    loadAvailableYears,
} from "../utils/dataLoader";

const props = defineProps({
  year: { type: String, default: "" },
  province: { type: String, default: "" },
  city: { type: String, default: "" },
  autoLoad: { type: Boolean, default: false }
});

// State
const availableYears = ref([]);
const provinceCityMap = ref({});
const internalSelectedYear = ref("");
const internalSelectedProvince = ref("");
const internalSelectedCity = ref("");
const calendarData = ref([]);
const loading = ref(false);

const displayTitle = computed(() => {
  if (props.city) return props.city;
  if (props.province) return props.province;
  return "NATIONWIDE (Select a region)";
});

const emptyMessage = computed(() => {
  if (props.autoLoad) return "SELECT A CITY OR PROVINCE TO VIEW CALENDAR";
  return "SELECT YEAR, PROVINCE AND CITY TO VIEW CALENDAR";
});

// Computed
const provinces = computed(() => Object.keys(provinceCityMap.value).sort());
const cities = computed(() => {
  if (!internalSelectedProvince.value) return [];
  return provinceCityMap.value[internalSelectedProvince.value] || [];
});

// Chart Option
const chartOption = computed(() => {
  if (!calendarData.value.length) return {};
  
  const y = props.autoLoad ? props.year : internalSelectedYear.value; 
  if (!y) return {};

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
      show: false 
    },
    calendar: {
      top: 30,
      left: 30,
      right: 30,
      cellSize: ["auto", 13],
      range: y,
      itemStyle: {
        borderWidth: 0.5,
        borderColor: "#1a1a1a",
        color: "transparent"
      },
      splitLine: {
        lineStyle: { color: "#ddd", width: 1 },
      },
      yearLabel: { show: false },
      monthLabel: { nameMap: "en", color: "#666", fontSize: 10 },
      dayLabel: { firstDay: 1, nameMap: "en", color: "#666", fontSize: 10 },
    },
    series: [
      {
        type: "heatmap",
        coordinateSystem: "calendar",
        data: heatmapData,
        itemStyle: {
          borderRadius: 2
        }
      },
    ],
  };
});

async function loadData() {
  const y = props.autoLoad ? props.year : internalSelectedYear.value;
  // If city is provided, use it. If not, if province is provided, use it.
  const target = props.autoLoad 
      ? (props.city || props.province) 
      : (internalSelectedCity.value || internalSelectedProvince.value);

  if (!y || (!target && !props.autoLoad)) {
    calendarData.value = [];
    return;
  }

  loading.value = true;
  try {
     calendarData.value = await computeCityYearCalendar(y, target);
  } catch (e) {
    console.error(e);
    calendarData.value = [];
  } finally {
    loading.value = false;
  }
}

// Watchers for auto-load
watch(
  () => [props.year, props.province, props.city],
  () => {
    if (props.autoLoad) {
      loadData();
    }
  },
  { immediate: true }
);

// Standalone mode handlers
async function loadStandaloneData() {
  const year = internalSelectedYear.value;
  if (!year) return;

  const target = internalSelectedCity.value || internalSelectedProvince.value || "";
  
  loading.value = true;
  try {
     calendarData.value = await computeCityYearCalendar(year, target);
  } catch (e) {
    console.error(e);
  } finally {
    loading.value = false;
  }
}

async function onYearChange() {
  internalSelectedCity.value = "";
  internalSelectedProvince.value = "";
  
  if (internalSelectedYear.value) {
     try {
       provinceCityMap.value = await getCitiesByProvince(internalSelectedYear.value);
     } catch (e) { console.error(e); }
     
     // Default load Nationwide data
     await loadStandaloneData();
  } else {
     calendarData.value = [];
  }
}

function onProvinceChange() {
  internalSelectedCity.value = "";
  loadStandaloneData();
}

async function onCityChange() {
  loadStandaloneData();
}

onMounted(async () => {
  if (!props.autoLoad) {
    try {
      availableYears.value = await loadAvailableYears();
      if (availableYears.value.length > 0) {
        internalSelectedYear.value = availableYears.value[0];
        await onYearChange();
      }
    } catch (e) {
      console.error(e);
    }
  }
});
</script>

<style scoped>
.city-calendar-wrap {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(255, 255, 255, 0.95); /* Ensure background for standalone */
  border: 1px solid #ddd;
  padding: 10px;
  height: 100%;
}

.city-calendar-wrap.full-width {
  width: 100%;
  border: none;
  background: transparent;
  padding: 0;
  gap: 5px;
}

.embedded-header h4 {
  font-family: "Oswald", sans-serif;
  color: #0a0a0a;
  margin: 0 0 5px 0;
  font-size: 14px;
  text-transform: uppercase;
  border-left: 3px solid #f97316;
  padding-left: 8px;
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
  height: auto !important; /* Override global fixed height */
  margin: 0 !important;    /* Remove global default margins */
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
  margin-top: -5px; /* Pull closer to chart */
}

.legend-title {
  color: var(--c-gray);
  font-weight: bold;
}

.legend-item {
  color: var(--c-white);
}
</style>
