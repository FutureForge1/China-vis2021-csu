<template>
  <div class="month-view" :class="{ embedded: isEmbedded }">
    <!-- Header (Hidden if embedded) -->
    <div class="section-heading" v-if="!isEmbedded">
      <div class="section-badge">MONTH VIEW</div>
      <div class="section-meta">MONTHLY DATA · ANNUAL TREND · SPATIAL DISTRIBUTION</div>
    </div>

    <!-- Time Controls -->
    <div class="time-bar">
      <div class="year-selector">
        <label>YEAR:</label>
        <select :value="currentYear" @change="e => $emit('update:currentYear', e.target.value)">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>
      <div class="month-selector">
        <label>MONTH:</label>
        <div class="month-chips">
          <button 
            v-for="m in 12" 
            :key="m" 
            :class="['month-chip', { active: m === currentMonth }]"
            @click="handleMonthSelect(m)"
          >
            {{ m }}
          </button>
        </div>
      </div>
    </div>

    <!-- Control Panel (Hidden/Integrated logic, kept for functionality) -->
    <ControlPanel
      class="pane control-pane"
      :date="`${currentYear}-${String(currentMonth).padStart(2, '0')}`"
      :region="selectedRegion || 'NATIONWIDE'"
      :rows="currentMonthDailyData"
      :metric="metric"
      :map-mode="mapMode"
      @select-metric="$emit('update:metric', $event)"
      @toggle-map-mode="mapMode = $event"
      @reset-region="$emit('update:region', '')"
    />

    <!-- Row 1: Map & Monthly Stats -->
    <section class="layout">
      <div class="pane map-pane">
        <div class="map-switch">
          <div class="mode-group">
            <button :class="{ active: mapMode === 'pollution' }" @click="mapMode = 'pollution'">POLLUTION</button>
            <button :class="{ active: mapMode === 'weather' }" @click="mapMode = 'weather'">WEATHER</button>
            <button :class="{ active: mapMode === 'type' }" @click="mapMode = 'type'">TYPE</button>
          </div>
          
          <div class="divider" v-if="mapMode !== 'type'" style="display:none"></div>

          <div v-if="mapMode === 'pollution'" class="metric-toggle">
            <button 
              v-for="m in ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3']" 
              :key="m"
              :class="{ active: metric === m }" 
              @click="$emit('update:metric', m)"
            >
              {{ m.toUpperCase() }}
            </button>
          </div>

          <div v-if="mapMode === 'weather'" class="weather-toggle">
            <button :class="{ active: weatherMetric === 'wind' }" @click="weatherMetric = 'wind'">WIND</button>
            <button :class="{ active: weatherMetric === 'temp' }" @click="weatherMetric = 'temp'">TEMP</button>
            <button :class="{ active: weatherMetric === 'rh' }" @click="weatherMetric = 'rh'">RH</button>
            <button :class="{ active: weatherMetric === 'psfc' }" @click="weatherMetric = 'psfc'">PSFC</button>
          </div>
        </div>

        <MapPanel
          v-if="mapMode === 'pollution' && monthMapSeries.length > 0"
          :data="monthMapSeries"
          :metric="metric"
          :title="`MONTHLY DIST: ${metric.toUpperCase()}`"
          :selected-name="selectedRegion"
          :show-value="true"
          @select="handleMapSelect"
        />
        
        <MapPanel
          v-else-if="mapMode === 'weather' && (weatherMapSeries.length > 0 || monthWindVectors.length > 0)"
          :data="weatherMapSeries"
          :metric="weatherMetricLabel"
          :title="`WEATHER DIST: ${weatherMetricLabel}`"
          mode="weather"
          :selected-name="selectedRegion"
          :wind="monthWindVectors" 
          :show-value="true"
          @select="handleMapSelect"
        />

        <div v-else-if="!isMonthDetailLoading && monthMapSeries.length === 0" class="placeholder-map">
          LOADING OR NO DATA...
        </div>
        
        <TypeMap
          v-else-if="mapMode === 'type' && typeMapData.length > 0"
          :key="`typ-${currentYear}-${currentMonth}`"
          :data="typeMapData"
          title="DOMINANT POLLUTION TYPE"
          :selected-name="selectedRegion"
          :map-name="currentMapName" 
        />
      </div>

      <div class="pane side-pane">
        <LevelBar :levels="monthLevelStats" />
        <TrendLine
          class="mt"
          :metric="metric"
          :series="monthTrendSeries"
          :dates="monthTrendDates"
        />
        <RadialPollutant class="mt" :data="monthRadialVector" />
      </div>
    </section>

    <!-- Row 2: BoxPlot & Seasonal Stack -->
    <section class="layout secondary">
      <div class="pane">
        <MonthlyBoxPlot
          :data="monthlyBoxData"
          :metric="metric"
          :title="`${metric.toUpperCase()} MONTHLY RANGE`"
        />
      </div>
      <div class="pane">
        <SeasonalLevelStack
          :dates="monthlyLevelTimeline.dates"
          :series="monthlyLevelTimeline.series"
          :metric="metric"
          :mode="'monthly'"
          @select-date="handleMonthSelect"
        />
      </div>
    </section>

    <!-- Row 3: City Analysis -->
    <section class="layout secondary">
      <div class="pane">
        <CityStackedPie
          :city="selectedCity"
          :day-values="monthCityValues"
          :month-stats="monthCityStats"
          :month="currentMonth.toString()"
        />
      </div>
      <div class="pane">
        <CityTypeRibbon
          v-if="monthCityTypeRibbon.dates && monthCityTypeRibbon.dates.length > 0"
          :dates="monthCityTypeRibbon.dates"
          :series="monthCityTypeRibbon.series"
          :type-order="monthCityTypeRibbon.typeOrder"
          :province="selectedRegion"
        />
        <div v-else class="placeholder-pane">
          <div class="placeholder-content">
            <h4>CITY TYPE EVOLUTION</h4>
            <p>NO DATA OR LOADING</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Row 4: Ranking & Ring -->
    <section class="layout secondary">
      <div class="pane">
        <AQIRanking :items="monthAQIRanking" @select="handleRankingSelect" />
      </div>
      <div class="pane">
        <MonthlyRing :items="monthlyRings" />
      </div>
    </section>

    <!-- Row 5: Wind & Comparison -->
    <section class="layout tertiary">
      <div class="pane">
        <WindCompass :data="monthWindRose" />
      </div>
      <div class="pane">
        <AQICompareLine :days="monthAQICompare.days" :series="monthAQICompare.series" :mode="'monthly'" />
      </div>
      <div class="pane">
        <div class="placeholder-pane">
          <div class="placeholder-content">
            <h4>MONTHLY COMPARISON</h4>
            <p>ANNUAL COMPARISON OR OTHER ANALYSIS</p>
          </div>
        </div>
      </div>
      <div class="pane">
        <div class="placeholder-pane">
          <div class="placeholder-content">
            <h4>EXTENDED CHART</h4>
            <p>RESERVED FOR FUTURE USE</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import {
    buildMonthlyWindVectors,
    classifyLevels,
    computeAQIRankingMonthly,
    computeCityMonthStats,
    computeCityTypeTrajectory,
    computeLevelTimelineByGranularity,
    computeMonthlyBoxDataForView,
    computeMonthlyRingMonthly,
    computeRadialVectorByMonthly,
    computeTrendSeriesByGranularity,
    computeTypeByRegion,
    computeWindRose,
    loadDataByGranularity,
    loadOneMonth,
    loadRegionIndex,
    matchGeoName,
    normalizeProvince
} from "../utils/dataLoader";
import AQICompareLine from "./AQICompareLine.vue";
import AQIRanking from "./AQIRanking.vue";
import CityStackedPie from "./CityStackedPie.vue";
import CityTypeRibbon from "./CityTypeRibbon.vue";
import ControlPanel from "./ControlPanel.vue";
import LevelBar from "./LevelBar.vue";
import MapPanel from "./MapPanel.vue";
import MonthlyBoxPlot from "./MonthlyBoxPlot.vue";
import MonthlyRing from "./MonthlyRing.vue";
import RadialPollutant from "./RadialPollutant.vue";
import SeasonalLevelStack from "./SeasonalLevelStack.vue";
import TrendLine from "./TrendLine.vue";
import TypeMap from "./TypeMap.vue";
import WindCompass from "./WindCompass.vue";

// Props
const props = defineProps({
  currentYear: {
    type: String,
    default: "2015"
  },
  metric: {
    type: String,
    default: "pm25"
  },
  selectedRegion: {
    type: String,
    default: ""
  },
  availableYears: {
    type: Array,
    default: () => ["2013"]
  },
  isEmbedded: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits([
  "update:region", 
  "select-month", 
  "update:metric",      
  "update:currentYear"  
]);

// Reactive State
const mapMode = ref("pollution");
const weatherMetric = ref("wind");
const regionIndex = ref(null);
const currentMonth = ref(1);
const monthlyAggregatedData = ref([]); 
const currentMonthDailyData = ref([]); 
const isMonthDetailLoading = ref(false); 
const mapGeoNames = ref([]);

// Computed
const selectedCity = computed(() => props.selectedRegion || "");

const monthMapSeries = computed(() => {
  if (currentMonthDailyData.value.length === 0) {
    console.warn(`[MonthView] monthMapSeries: currentMonthDailyData is empty`);
    return [];
  }

  // 使用与 App.vue aggregateMap 相同的逻辑
  const sums = new Map();
  const counts = new Map();
  const metricName = props.metric;
  
  for (const row of currentMonthDailyData.value) {
    const actualField = `${metricName}_mean`;
    const val = Number(row[actualField] ?? 0);
    
    if (Number.isNaN(val)) continue;

    // 1. 聚合省份
    const prov = normalizeProvince(row.province);
    if (prov) {
      sums.set(prov, (sums.get(prov) || 0) + val);
      counts.set(prov, (counts.get(prov) || 0) + 1);
    }

    // 2. 聚合城市 (如果存在)
    if (row.city) {
      sums.set(row.city, (sums.get(row.city) || 0) + val);
      counts.set(row.city, (counts.get(row.city) || 0) + 1);
    }
  }

  const result = Array.from(sums.entries()).map(([name, sum]) => ({
    name: name,
    value: sum / (counts.get(name) || 1),
  }));
  
  console.log(`[MonthView] monthMapSeries: ${result.length} regions with valid data for metric ${props.metric}`);
  return result;
});

const currentMapName = computed(() => 'china');


const weatherMapSeries = computed(() => {
  if (weatherMetric.value === 'wind') {
    return []; 
  }

  if (currentMonthDailyData.value.length === 0) return [];
  
  // 使用与 App.vue aggregateMap 相同的逻辑
  const sums = new Map();
  const counts = new Map();
  const metricName = weatherMetric.value;
  
  for (const row of currentMonthDailyData.value) {
    const actualField = `${metricName}_mean`;
    const val = Number(row[actualField] ?? 0);
    
    if (Number.isNaN(val)) continue;

    // 1. 聚合省份
    const prov = normalizeProvince(row.province);
    if (prov) {
      sums.set(prov, (sums.get(prov) || 0) + val);
      counts.set(prov, (counts.get(prov) || 0) + 1);
    }

    // 2. 聚合城市 (如果存在)
    if (row.city) {
      sums.set(row.city, (sums.get(row.city) || 0) + val);
      counts.set(row.city, (counts.get(row.city) || 0) + 1);
    }
  }

  const result = Array.from(sums.entries()).map(([name, sum]) => ({
    name: name,
    value: sum / (counts.get(name) || 1),
  }));
  
  return result;
});

const weatherMetricLabel = computed(() => {
  const map = { wind: "WIND", temp: "TEMP", rh: "RH", psfc: "PSFC" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

const typeMapData = computed(() => {
  if (mapGeoNames.value.length === 0) {
    console.warn('[MonthView] typeMapData: mapGeoNames is empty');
    return [];
  }

  if (!monthlyAggregatedData.value || monthlyAggregatedData.value.length === 0) {
    console.warn('[MonthView] typeMapData: monthlyAggregatedData is empty');
    return [];
  }

  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry) {
    console.warn('[MonthView] typeMapData: no entry for month', currentMonth.value);
    return [];
  }
  
  if (!monthEntry.data || monthEntry.data.length === 0) {
    console.warn('[MonthView] typeMapData: month entry has no data', currentMonth.value);
    return [];
  }

  const rawList = computeTypeByRegion(monthEntry.data, "city", "month");
  console.log('[MonthView] typeMapData: computed rawList length:', rawList.length);
  
  const validList = [];
  for (const item of rawList) {
    const mappedName = matchGeoName(item.name, mapGeoNames.value);
    if (mappedName) {
      validList.push({
        ...item,
        name: mappedName 
      });
    }
  }
  
  console.log('[MonthView] typeMapData: validList length:', validList.length);
  return validList;
});

const monthLevelStats = computed(() => {
  if (selectedCity.value) {
    const target = selectedCity.value;
    const cityData = currentMonthDailyData.value.filter(r =>
      (r.city && r.city.includes(target)) ||
      (r.province && r.province.includes(target))
    );
    return classifyLevels(cityData, props.metric);
  } else {
    // 当前月份的数据
    const statsData = currentMonthDailyData.value.map(row => ({
      [props.metric]: row[`${props.metric}_mean`] 
    }));
    return classifyLevels(statsData, props.metric);
  }
});

const monthRadialVector = computed(() => {
  return computeRadialVectorByMonthly(currentMonthDailyData.value);
});

const monthTrendSeries = computed(() => {
  return computeTrendSeriesByGranularity(monthlyAggregatedData.value, props.metric, "month");
});

const monthTrendDates = computed(() => {
  return monthlyAggregatedData.value.map(entry => entry.date);
});

const monthlyBoxData = computed(() => {
  return computeMonthlyBoxDataForView(monthlyAggregatedData.value, props.metric);
});

const monthlyLevelTimeline = computed(() => {
  return computeLevelTimelineByGranularity(monthlyAggregatedData.value, props.metric, "month");
});

const monthCityValues = computed(() => {
  if (!selectedCity.value) return {};
  const target = normalizeProvince(selectedCity.value);
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry) return {};
  
  const row = monthEntry.data.find(r => 
    normalizeProvince(r.city) === target || 
    normalizeProvince(r.province) === target
  );
  if (!row) return {};
  
  return {
    pm25: row.pm25_mean, pm10: row.pm10_mean, so2: row.so2_mean,
    no2: row.no2_mean, co: row.co_mean, o3: row.o3_mean,
  };
});

const monthCityStats = computed(() => {
  return computeCityMonthStats(currentMonthDailyData.value, selectedCity.value, currentMonth.value);
});

const monthCityTypeRibbon = computed(() => {
  if (!currentMonthDailyData.value || currentMonthDailyData.value.length === 0) {
    return { dates: [], series: [], typeOrder: [] };
  }
  // 包装成 computeCityTypeTrajectory 期望的格式：[{date, data}]
  const wrapped = [{
    date: `${props.currentYear}-${String(currentMonth.value).padStart(2, '0')}-01`,
    data: currentMonthDailyData.value
  }];
  return computeCityTypeTrajectory(wrapped, props.selectedRegion || null, currentMonth.value);
});

const monthAQIRanking = computed(() => {
  return computeAQIRankingMonthly(currentMonthDailyData.value, "province", 15);
});

const monthlyRings = computed(() => {
  return computeMonthlyRingMonthly(monthlyAggregatedData.value);
});

const monthWindRose = computed(() => {
  // currentMonthDailyData现在是整月的数据数组
  return computeWindRose(currentMonthDailyData.value);
});

const monthAQICompare = computed(() => {
  const currentYearData = monthlyAggregatedData.value.map(entry => {
    if (entry.data && entry.data.length > 0) {
      const sum = entry.data.reduce((acc, r) => acc + (Number(r[`${props.metric}_mean`]) || 0), 0);
      return sum / entry.data.length;
    }
    return 0;
  });

  return {
    days: monthlyAggregatedData.value.map(m => `${m.month}`),
    series: [{ name: props.currentYear, data: currentYearData }]
  };
});

const monthWindVectors = computed(() => {
  if (mapMode.value === 'weather' && weatherMetric.value === 'wind') {
    if (!currentMonthDailyData.value || !regionIndex.value) return [];
    return buildMonthlyWindVectors(currentMonthDailyData.value, regionIndex.value, 0.15);
  }
  return [];
});

function handleMapSelect(name) {
  emit('update:region', name);
}

function handleRankingSelect(name) {
  emit('update:region', name);
}

async function loadMonthlyAggregatedData() {
  try {
    if (!regionIndex.value) {
      regionIndex.value = await loadRegionIndex();
    }

    const months = Array.from({ length: 12 }, (_, i) => `${props.currentYear}-${String(i + 1).padStart(2, '0')}`);
    const promises = months.map(m => loadOneMonth(m));
    const results = await Promise.all(promises);

    monthlyAggregatedData.value = results.map((data, index) => ({
      date: months[index],
      month: index + 1,
      data: data || []
    }));
    
    await loadMonthDetail(currentMonth.value);
  } catch (err) {
    console.error("[MonthView] Failed to load aggregated data:", err);
  }
}

async function loadMonthDetail(monthNum) {
  isMonthDetailLoading.value = true;
  currentMonthDailyData.value = []; 

  const year = props.currentYear;
  const monthStr = String(monthNum).padStart(2, '0');
  const dateStr = `${year}-${monthStr}`;
  
  try {
    // 加载月度数据
    const monthlyData = await loadDataByGranularity("month", year, dateStr);
    
    if (monthlyData && monthlyData.length > 0) {
      currentMonthDailyData.value = monthlyData;
      console.log(`[MonthView] Loaded monthly data for ${dateStr}:`, monthlyData.length, 'records');
    } else {
      console.warn(`[MonthView] No monthly data for ${dateStr}`);
      currentMonthDailyData.value = [];
    }
  } catch (error) {
    console.error(`[MonthView] Error loading monthly data for ${dateStr}:`, error);
    currentMonthDailyData.value = [];
  }
  
  isMonthDetailLoading.value = false;
}

function handleMonthSelect(month) {
  const m = typeof month === 'string' ? parseInt(month.split('-')[1]) : month;
  if (currentMonth.value !== m) {
    currentMonth.value = m;
    loadMonthDetail(m);
    emit('select-month', m);
  }
}

async function initMapData() {
  if (!regionIndex.value) {
    regionIndex.value = await loadRegionIndex();
    // 从 regionIndex 中提取所有地名作为 mapGeoNames
    if (regionIndex.value) {
      mapGeoNames.value = Array.from(regionIndex.value.keys());
      console.log(`[MonthView] Loaded ${mapGeoNames.value.length} geo names from region index`);
    }
  }
}

watch(() => props.currentYear, async () => {
  console.log(`[MonthView] Watch currentYear triggered for year: ${props.currentYear}`);
  await initMapData(); 
  console.log(`[MonthView] initMapData done`);
  
  await loadMonthlyAggregatedData();
  console.log(`[MonthView] loadMonthlyAggregatedData done, data length: ${monthlyAggregatedData.value.length}`);
  
  // 已经在 loadMonthlyAggregatedData 中调用了 loadMonthDetail，无需重复
}, { immediate: true });

watch(() => props.metric, async () => {
  // 指标改变时，重新加载数据
  if (monthlyAggregatedData.value.length === 0) {
    console.log(`[MonthView] Watch metric triggered, but monthlyAggregatedData empty, loading...`);
    await loadMonthlyAggregatedData();
  }
});
</script>

<style scoped>
.month-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--c-bg);
  color: var(--c-black);
  padding: 24px;
  box-sizing: border-box;
  overflow-y: auto;
  font-size: 14px;
}

.month-view.embedded {
  height: auto;
  overflow-y: visible;
  padding: 0;
  background: transparent;
}

.section-heading {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.section-badge {
  background: #FFE600;
  color: #000;
  padding: 2px 8px;
  font-family: "Oswald", sans-serif;
  font-weight: bold;
  font-size: 18px;
  letter-spacing: 1px;
}

.section-meta {
  color: #444;
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
}

.time-bar {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-bottom: 20px;
  background: transparent;
  padding: 0;
  border: none;
}

.year-selector, .month-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.year-selector label, .month-selector label {
  color: #FFE600;
  font-family: "Oswald", sans-serif;
  font-size: 14px;
  font-weight: normal;
}

.year-selector select {
  background: #fff;
  border: 1px solid #ddd;
  color: #0a0a0a;
  padding: 4px 8px;
  font-family: "JetBrains Mono", monospace;
  outline: none;
  border-radius: 0;
}

.month-chips {
  display: flex;
  gap: 2px;
}

.month-chip {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  border: 1px solid #ddd;
  color: #666;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
  border-radius: 0;
}

.month-chip:hover {
  border-color: #FFE600;
  color: #0a0a0a;
  background: transparent;
}

.month-chip.active {
  background: #FFE600;
  color: #000;
  font-weight: bold;
  border-color: #FFE600;
  box-shadow: none;
}

.layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.layout.secondary {
  grid-template-columns: 1fr 1fr;
}

.layout.tertiary {
  grid-template-columns: 1fr 1fr 1fr 1fr;
}

.pane {
  background: rgba(255,255,255,0.95);
  border: 1px solid #ddd;
  padding: 12px;
  display: flex;
  flex-direction: column;
  min-height: 300px;
}

.map-pane {
  position: relative;
  padding: 0;
  border: 1px solid #ddd;
  background: rgba(255,255,255,0.95);
}

.side-pane {
  gap: 12px;
}

.map-switch {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  background: rgba(0,0,0,0.8);
  padding: 8px;
  border: 1px solid #ddd;
}

.mode-group {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
  width: 100%;
}

.mode-group button {
  background: transparent;
  border: none;
  color: #666;
  padding: 4px 8px;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  cursor: pointer;
}

.mode-group button.active {
  background: #FFE600;
  color: #000;
  font-weight: bold;
}

.divider {
  width: 1px;
  height: 16px;
  background: #ddd;
  margin: 0 4px;
}

.metric-toggle, .weather-toggle {
  display: flex;
  gap: 2px;
}

.metric-toggle button, .weather-toggle button {
  background: #fff;
  border: 1px solid #ddd;
  color: #444;
  padding: 2px 6px;
  font-family: "JetBrains Mono", monospace;
  font-size: 11px;
  cursor: pointer;
  border-radius: 0;
}

.metric-toggle button:hover, .weather-toggle button:hover {
  color: #0a0a0a;
  border-color: #666;
}

.metric-toggle button.active, .weather-toggle button.active {
  background: #FFE600;
  color: #000;
  border-color: #FFE600;
  font-weight: bold;
}

.placeholder-map {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  font-family: "JetBrains Mono", monospace;
  font-size: 14px;
  background: transparent;
}

.placeholder-pane {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: rgba(0,0,0,0.02);
}

.placeholder-content {
  text-align: center;
}

.placeholder-content h4 {
  color: #FFE600;
  font-family: "Oswald", sans-serif;
  font-size: 14px;
  margin: 0 0 8px 0;
  letter-spacing: 1px;
}

.placeholder-content p {
  color: #666;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  margin: 0;
}

.mt {
  margin-top: 12px;
}

.control-pane {
  margin-bottom: 20px;
  min-height: auto;
}
</style>
