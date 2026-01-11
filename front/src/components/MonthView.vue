<template>
  <div class="month-view" :class="{ embedded: isEmbedded }">
    <!-- Header (Hidden if embedded) -->
    <div class="section-heading" v-if="!isEmbedded">
      <div class="section-badge">MONTHLY ANALYTICS</div>
      <!-- Fixed label -->
      <div class="section-meta">
        MONTHLY DATA · ANNUAL TREND · SPATIAL DISTRIBUTION
      </div>
    </div>

    <!-- Time Controls -->
    <div class="time-bar">
      <div class="year-selector">
        <label>YEAR:</label>
        <select
          :value="currentYear"
          @change="(e) => $emit('update:currentYear', e.target.value)"
        >
          <option v-for="y in availableYears" :key="y" :value="y">
            {{ y }}
          </option>
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
            <button
              :class="{ active: mapMode === 'pollution' }"
              @click="mapMode = 'pollution'"
            >
              POLLUTION
            </button>
            <button
              :class="{ active: mapMode === 'weather' }"
              @click="mapMode = 'weather'"
            >
              WEATHER
            </button>
            <button
              :class="{ active: mapMode === 'type' }"
              @click="mapMode = 'type'"
            >
              TYPE
            </button>
          </div>

          <div
            class="divider"
            v-if="mapMode !== 'type'"
            style="display: none"
          ></div>

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
            <button
              :class="{ active: weatherMetric === 'wind' }"
              @click="weatherMetric = 'wind'"
            >
              WIND
            </button>
            <button
              :class="{ active: weatherMetric === 'temp' }"
              @click="weatherMetric = 'temp'"
            >
              TEMP
            </button>
            <button
              :class="{ active: weatherMetric === 'rh' }"
              @click="weatherMetric = 'rh'"
            >
              RH
            </button>
            <button
              :class="{ active: weatherMetric === 'psfc' }"
              @click="weatherMetric = 'psfc'"
            >
              PSFC
            </button>
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
          v-else-if="
            mapMode === 'weather' &&
            (weatherMapSeries.length > 0 || monthWindVectors.length > 0)
          "
          :data="weatherMapSeries"
          :metric="weatherMetricLabel"
          :title="`WEATHER DIST: ${weatherMetricLabel}`"
          mode="weather"
          :selected-name="selectedRegion"
          :wind="monthWindVectors"
          :show-value="true"
          @select="handleMapSelect"
        />

        <div
          v-else-if="!isMonthDetailLoading && monthMapSeries.length === 0"
          class="placeholder-map"
        >
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
          v-if="
            monthCityTypeRibbon.dates && monthCityTypeRibbon.dates.length > 0
          "
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
      <!-- 左侧面板：降维图 -->
      <div class="pane">
        <h3>省份污染特征降维分析</h3>
        <!-- 文档2中应该这样使用 -->
        <!-- 在月度分析部分，修改ProvinceDimensionChart的调用 -->
        <ProvinceDimensionChart
          :data="monthlyData"
          :metric="monthlyMetric"
          :selected-province="selectedRegion"
          :selected-year="selectedYear"
          :selected-month="selectedMonth"
          @province-select="handleMapSelect"
          v-if="monthlyData.length > 0"
        />
      </div>

      <!-- 右侧面板：聚类分析说明 -->
      <div class="pane">
        <h3>聚类分析说明</h3>
        <p class="scope-indicator">当前颗粒度：{{ scopeLabel }}</p>
        <div class="cluster-info">
          <div v-if="selectedRegion" class="cluster-details">
            <h4>当前选中：{{ selectedRegion }}</h4>
            <div class="cluster-stats">
              <div class="stat">
                <span class="label">污染特征：</span>
                <span class="value">{{
                  selectedClusterInfo.clusterType || "低污染区域"
                }}</span>
              </div>
              <div class="stat">
                <span class="label">主要污染物：</span>
                <span class="value">{{
                  selectedClusterInfo.primaryPollutant || "PM2.5"
                }}</span>
              </div>
              <div class="stat">
                <span class="label">相似省份：</span>
                <div class="similar-provinces">
                  <span
                    v-for="province in selectedClusterInfo.similarProvinces || [
                      '台湾省',
                      '青海省',
                      '内蒙古自治区',
                    ]"
                    :key="province"
                    class="province-tag"
                  >
                    {{ province }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="no-selection">
            <p>点击地图或降维图中的点查看详细信息</p>
            <p class="hint">
              降维图展示了各省份在污染特征空间中的相对位置，距离越近的省份污染特征越相似
            </p>
          </div>
        </div>
      </div>
    </section>

    <section class="layout secondary">
      <div class="pane">
        <h3>省份污染物径向分析</h3>
        <ProvinceRadarChart
          :data="monthlyData"
          :metric="monthlyMetric"
          :selected-province="selectedRegion"
          :year="selectedYear"
          :month="selectedMonth"
        />
      </div>
      <div class="pane">
        <!--            <h3>分析说明</h3>-->
        <div class="radar-explanation">
          <p>此图展示了各省份在6个主要污染物维度上的分布情况：</p>
          <ul>
            <li>每个轴代表一种污染物浓度</li>
            <li>省份距离中心越远，该污染物浓度越高</li>
            <li>图形面积越大，综合污染水平越高</li>
            <li>红色高亮显示当前选中省份</li>
          </ul>
        </div>
      </div>
    </section>

    <!-- 在月度分析模板的合适位置添加 -->
    <section class="layout single">
      <div class="pane">
        <h3>污染程度冰柱图分析</h3>
        <div class="chart-description">
          <p>
            通过冰柱图展示全国-省份-城市的污染层级结构，条形长度表示污染程度
          </p>
        </div>

        <IcicleChart
          :data="monthlyData"
          :metric="monthlyMetric"
          :selected-region="selectedRegion"
          :selected-year="selectedYear"
          :selected-month="selectedMonth"
          @region-select="handleMapSelect"
          v-if="monthlyData.length > 0"
        />

        <div class="icicle-explanation">
          <h4>图表解读说明</h4>
          <ul>
            <li>
              <strong>全国层级</strong>：最顶层的条形，表示全国总体污染程度
            </li>
            <li>
              <strong>省份层级</strong
              >：第二层条形，各省份条形长度之和等于全国条形长度
            </li>
            <li>
              <strong>城市层级</strong
              >：最底层条形，各城市条形长度之和等于所属省份条形长度
            </li>
            <li>
              <strong>颜色编码</strong
              >：从绿色（低污染）到红色（高污染）表示污染程度
            </li>
            <li>
              <strong>交互功能</strong
              >：点击任一区域可选中该区域，与其他图表联动
            </li>
          </ul>

          <div class="view-mode-info">
            <h5>视图模式说明：</h5>
            <p>
              <strong>当前污染物模式</strong>：显示当前选中污染物（{{
                monthlyMetric.toUpperCase()
              }}）的浓度分布
            </p>
            <p>
              <strong>综合污染指数模式</strong
              >：基于6种污染物的加权平均值，更全面反映污染状况
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- Row 5: Wind & Comparison -->
    <section class="layout secondary">
      <div class="pane">
        <WindCompass :data="monthWindRose" />
      </div>
      <div class="pane">
        <AQICompareLine
          :days="monthAQICompare.days"
          :series="monthAQICompare.series"
          :mode="'monthly'"
        />
      </div>
    </section>

    <!-- Row 6: Correlation -->
    <div class="pane full-width-pane" style="height: 320px">
      <CorrHeatmap
        v-if="monthCorrMatrix && monthCorrMatrix.length > 0"
        :matrix="monthCorrMatrix"
        title="FACTOR CORRELATION (MONTHLY)"
      />
      <div v-else class="placeholder-pane" style="height: 100%">
        <div class="placeholder-content">
          <h4>FACTOR CORRELATION</h4>
          <p>LOADING OR INSUFFICIENT DATA</p>
        </div>
      </div>
    </div>

    <!-- Row 7: Meteorology-Pollution Scatter -->
    <section class="layout secondary">
      <div class="pane">
        <MeteoScatter
          :data="currentMonthDailyData"
          xMetric="temp"
          yMetric="pm25"
        />
      </div>
      <div class="pane">
        <MultiCityTrend
          :monthlyData="monthlyAggregatedData"
          :metric="metric"
          :year="currentYear"
        />
      </div>
    </section>

    <!-- Row 8: Province Yearly Heatmap -->
    <section class="layout single">
      <div class="pane">
        <ProvinceYearlyHeatmap
          :monthlyData="monthlyAggregatedData"
          :metric="metric"
          :year="currentYear"
        />
      </div>
    </section>

    <!-- City Calendar (Full Width) -->
    <div class="pane full-width-pane">
      <CityPollutionCalendar
        :year="currentYear"
        :province="selectedRegion"
        :city="selectedCity"
        :auto-load="true"
      />
    </div>
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
  computeCorrMatrix,
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
  normalizeProvince,
} from "../utils/dataLoader";
import AQICompareLine from "./AQICompareLine.vue";
import CityPollutionCalendar from "./CityPollutionCalendar.vue";
import CityStackedPie from "./CityStackedPie.vue";
import CityTypeRibbon from "./CityTypeRibbon.vue";
import ControlPanel from "./ControlPanel.vue";
import CorrHeatmap from "./CorrHeatmap.vue";
import IcicleChart from "./IcicleChart.vue";
import LevelBar from "./LevelBar.vue";
import MapPanel from "./MapPanel.vue";
import MonthlyBoxPlot from "./MonthlyBoxPlot.vue";
import ProvinceDimensionChart from "./ProvinceDimensionChart.vue";
import ProvinceRadarChart from "./ProvinceRadarChart.vue";
import RadialPollutant from "./RadialPollutant.vue";
import SeasonalLevelStack from "./SeasonalLevelStack.vue";
import TrendLine from "./TrendLine.vue";
import TypeMap from "./TypeMap.vue";
import WindCompass from "./WindCompass.vue";
import MeteoScatter from "./MeteoScatter.vue";
import MultiCityTrend from "./MultiCityTrend.vue";
import ProvinceYearlyHeatmap from "./ProvinceYearlyHeatmap.vue";

const pollutantKeys = ["pm25", "pm10", "so2", "no2", "co", "o3"];
const pollutantStandards = {
  pm25: 35,
  pm10: 50,
  so2: 150,
  no2: 100,
  co: 4,
  o3: 160,
};

const emptyClusterInfo = {
  clusterType: "",
  primaryPollutant: "",
  similarProvinces: [],
  pollutantLevels: [],
};

// Props
const props = defineProps({
  currentYear: {
    type: String,
    default: "2015",
  },
  metric: {
    type: String,
    default: "pm25",
  },
  selectedRegion: {
    type: String,
    default: "",
  },
  availableYears: {
    type: Array,
    default: () => ["2013"],
  },
  isEmbedded: {
    type: Boolean,
    default: false,
  },
  scopeLevel: {
    type: String,
    default: "national",
  },
});

// Emits
const emit = defineEmits([
  "update:region",
  "select-month",
  "update:metric",
  "update:currentYear",
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
const selectedCity = computed(() =>
  props.scopeLevel === "national" ? "" : props.selectedRegion || ""
);

const selectedYear = computed(() => props.currentYear);
const selectedMonth = computed(() =>
  String(currentMonth.value).padStart(2, "0")
);
const monthlyMetric = computed(() => props.metric);
const scopeLabel = computed(() =>
  props.scopeLevel === "national" ? "全国" : "省份"
);

const monthlyData = computed(() => {
  if (!monthlyAggregatedData.value || monthlyAggregatedData.value.length === 0)
    return [];
  const entry = monthlyAggregatedData.value.find(
    (m) => m.month === currentMonth.value
  );
  return entry && Array.isArray(entry.data) ? entry.data : [];
});

const selectedClusterInfo = computed(() => {
  if (!props.selectedRegion) {
    return emptyClusterInfo;
  }
  const info = computeClusterInfo(
    currentMonthDailyData.value,
    props.selectedRegion
  );
  return info || emptyClusterInfo;
});

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

  console.log(
    `[MonthView] monthMapSeries: ${result.length} regions with valid data for metric ${props.metric}`
  );
  return result;
});

const currentMapName = computed(() => "china");

const weatherMapSeries = computed(() => {
  if (weatherMetric.value === "wind") {
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
    console.warn("[MonthView] typeMapData: mapGeoNames is empty");
    return [];
  }

  if (
    !monthlyAggregatedData.value ||
    monthlyAggregatedData.value.length === 0
  ) {
    console.warn("[MonthView] typeMapData: monthlyAggregatedData is empty");
    return [];
  }

  const monthEntry = monthlyAggregatedData.value.find(
    (m) => m.month === currentMonth.value
  );
  if (!monthEntry) {
    console.warn(
      "[MonthView] typeMapData: no entry for month",
      currentMonth.value
    );
    return [];
  }

  if (!monthEntry.data || monthEntry.data.length === 0) {
    console.warn(
      "[MonthView] typeMapData: month entry has no data",
      currentMonth.value
    );
    return [];
  }

  const rawList = computeTypeByRegion(monthEntry.data, "city", "month");
  console.log(
    "[MonthView] typeMapData: computed rawList length:",
    rawList.length
  );

  const validList = [];
  for (const item of rawList) {
    const mappedName = matchGeoName(item.name, mapGeoNames.value);
    if (mappedName) {
      validList.push({
        ...item,
        name: mappedName,
      });
    }
  }

  console.log("[MonthView] typeMapData: validList length:", validList.length);
  return validList;
});

const tsneScatter = computed(() => {
  return buildFeatureScatterTSNE(currentMonthDailyData.value, "city");
});

const monthLevelStats = computed(() => {
  if (selectedCity.value) {
    const target = selectedCity.value;
    const cityData = currentMonthDailyData.value.filter(
      (r) =>
        (r.city && r.city.includes(target)) ||
        (r.province && r.province.includes(target))
    );
    return classifyLevels(cityData, props.metric);
  } else {
    // 当前月份的数据
    const statsData = currentMonthDailyData.value.map((row) => ({
      [props.metric]: row[`${props.metric}_mean`],
    }));
    return classifyLevels(statsData, props.metric);
  }
});

const monthRadialVector = computed(() => {
  return computeRadialVectorByMonthly(currentMonthDailyData.value);
});

const monthTrendSeries = computed(() => {
  return computeTrendSeriesByGranularity(
    monthlyAggregatedData.value,
    props.metric,
    "month"
  );
});

const monthTrendDates = computed(() => {
  return monthlyAggregatedData.value.map((entry) => entry.date);
});

const monthlyBoxData = computed(() => {
  return computeMonthlyBoxDataForView(
    monthlyAggregatedData.value,
    props.metric
  );
});

const monthlyLevelTimeline = computed(() => {
  return computeLevelTimelineByGranularity(
    monthlyAggregatedData.value,
    props.metric,
    "month"
  );
});

const monthCityValues = computed(() => {
  if (!selectedCity.value) return {};
  const target = normalizeProvince(selectedCity.value);
  const monthEntry = monthlyAggregatedData.value.find(
    (m) => m.month === currentMonth.value
  );
  if (!monthEntry) return {};

  const row = monthEntry.data.find(
    (r) =>
      normalizeProvince(r.city) === target ||
      normalizeProvince(r.province) === target
  );
  if (!row) return {};

  return {
    pm25: row.pm25_mean,
    pm10: row.pm10_mean,
    so2: row.so2_mean,
    no2: row.no2_mean,
    co: row.co_mean,
    o3: row.o3_mean,
  };
});

const monthCityStats = computed(() => {
  if (!currentMonthDailyData.value) return {};
  // Wrap into dayEntries format for computeCityMonthStats
  const wrapped = [
    {
      date: `${props.currentYear}-${String(currentMonth.value).padStart(
        2,
        "0"
      )}-01`,
      data: currentMonthDailyData.value,
    },
  ];
  return computeCityMonthStats(wrapped, selectedCity.value, currentMonth.value);
});

const monthCityTypeRibbon = computed(() => {
  if (
    !monthlyAggregatedData.value ||
    monthlyAggregatedData.value.length === 0
  ) {
    return { dates: [], series: [], typeOrder: [] };
  }
  // Use all monthly data for trajectory (Yearly evolution)
  return computeCityTypeTrajectory(
    monthlyAggregatedData.value,
    props.selectedRegion || null,
    null,
    "month"
  );
});

const monthAQIRanking = computed(() => {
  // If a region (province) is selected, rank cities within that province
  if (props.selectedRegion) {
    // Determine if selectedRegion is a province.
    // Usually if selectedRegion is set, we want to see cities inside it.
    // Filter data for this province
    const target = normalizeProvince(props.selectedRegion);
    const provinceData = currentMonthDailyData.value.filter(
      (r) => normalizeProvince(r.province) === target
    );

    // Rank by city (using 'city' field)
    return computeAQIRankingMonthly(provinceData, "city", 15);
  }
  // Default: Rank provinces nationwide
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
  const currentYearData = monthlyAggregatedData.value.map((entry) => {
    if (entry.data && entry.data.length > 0) {
      const sum = entry.data.reduce(
        (acc, r) => acc + (Number(r[`${props.metric}_mean`]) || 0),
        0
      );
      return sum / entry.data.length;
    }
    return 0;
  });

  return {
    days: monthlyAggregatedData.value.map((m) => `${m.month}`),
    series: [{ name: props.currentYear, data: currentYearData }],
  };
});

const monthCorrMatrix = computed(() => {
  // Use current month daily data for correlation
  if (!currentMonthDailyData.value || currentMonthDailyData.value.length === 0)
    return [];

  // Helper to get raw rows for correlation check
  const rawRows = currentMonthDailyData.value.map((r) => {
    return {
      pm25: Number(r.pm25_mean),
      pm10: Number(r.pm10_mean),
      so2: Number(r.so2_mean),
      no2: Number(r.no2_mean),
      co: Number(r.co_mean),
      o3: Number(r.o3_mean),
      temp: Number(r.temp_mean),
      rh: Number(r.rh_mean),
      psfc: Number(r.psfc_mean),
      wind: Number(
        r.wind_mean ||
          Math.sqrt((Number(r.u_mean) || 0) ** 2 + (Number(r.v_mean) || 0) ** 2)
      ),
    };
  });

  // computeCorrMatrix expects structure [{data: entries}]
  const wrappedData = [{ data: rawRows }];

  return computeCorrMatrix(
    wrappedData,
    ["pm25", "pm10", "so2", "no2", "co", "o3"],
    ["temp", "rh", "psfc", "wind"]
  );
});

const monthWindVectors = computed(() => {
  if (mapMode.value === "weather" && weatherMetric.value === "wind") {
    if (!currentMonthDailyData.value || !regionIndex.value) return [];
    return buildMonthlyWindVectors(
      currentMonthDailyData.value,
      regionIndex.value,
      0.15
    );
  }
  return [];
});

function handleMapSelect(name) {
  emit("update:region", name);
}

function handleRankingSelect(name) {
  emit("update:region", name);
}

async function loadMonthlyAggregatedData() {
  try {
    if (!regionIndex.value) {
      regionIndex.value = await loadRegionIndex();
    }

    const months = Array.from(
      { length: 12 },
      (_, i) => `${props.currentYear}-${String(i + 1).padStart(2, "0")}`
    );
    const promises = months.map((m) => loadOneMonth(m));
    const results = await Promise.all(promises);

    monthlyAggregatedData.value = results.map((data, index) => ({
      date: months[index],
      month: index + 1,
      data: data || [],
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
  const monthStr = String(monthNum).padStart(2, "0");
  const dateStr = `${year}-${monthStr}`;

  try {
    // 加载月度数据
    const monthlyData = await loadDataByGranularity("month", year, dateStr);

    if (monthlyData && monthlyData.length > 0) {
      currentMonthDailyData.value = monthlyData;
      console.log(
        `[MonthView] Loaded monthly data for ${dateStr}:`,
        monthlyData.length,
        "records"
      );
    } else {
      console.warn(`[MonthView] No monthly data for ${dateStr}`);
      currentMonthDailyData.value = [];
    }
  } catch (error) {
    console.error(
      `[MonthView] Error loading monthly data for ${dateStr}:`,
      error
    );
    currentMonthDailyData.value = [];
  }

  isMonthDetailLoading.value = false;
}

function handleMonthSelect(month) {
  const m = typeof month === "string" ? parseInt(month.split("-")[1]) : month;
  if (currentMonth.value !== m) {
    currentMonth.value = m;
    loadMonthDetail(m);
    emit("select-month", m);
  }
}

async function initMapData() {
  if (!regionIndex.value) {
    regionIndex.value = await loadRegionIndex();
    // 从 regionIndex 中提取所有地名作为 mapGeoNames
    if (regionIndex.value) {
      mapGeoNames.value = Array.from(regionIndex.value.keys());
      console.log(
        `[MonthView] Loaded ${mapGeoNames.value.length} geo names from region index`
      );
    }
  }
}

function computeClusterInfo(rows, provinceName) {
  if (!provinceName || !rows || rows.length === 0) {
    return null;
  }

  const normalizedTarget = normalizeProvince(provinceName);
  if (!normalizedTarget) {
    return null;
  }

  const provinceRows = rows.filter(
    (row) => normalizeProvince(row.province) === normalizedTarget
  );

  if (provinceRows.length === 0) {
    return null;
  }

  const averages = computeAverageByPollutant(provinceRows);

  const pollutantLevels = pollutantKeys.map((key) => {
    const value = averages[key] || 0;
    const standard = pollutantStandards[key] || 1;
    return {
      key,
      label: key.toUpperCase(),
      value,
      score: value / standard,
    };
  });

  const totalScore = pollutantLevels.reduce((sum, item) => sum + item.score, 0);

  let clusterType = "低污染区域";
  if (totalScore > 4) clusterType = "高污染区域";
  else if (totalScore > 2) clusterType = "中等污染区域";

  const primaryPollutantEntry = pollutantLevels.reduce((max, item) =>
    item.score > max.score ? item : max
  );

  const similarProvinces = calculateSimilarProvincesForMonth(
    rows,
    normalizedTarget
  );

  return {
    clusterType,
    primaryPollutant: primaryPollutantEntry?.label || "PM2.5",
    similarProvinces,
    pollutantLevels,
  };
}

function computeAverageByPollutant(rows) {
  const sums = Object.fromEntries(pollutantKeys.map((key) => [key, 0]));
  const counts = Object.fromEntries(pollutantKeys.map((key) => [key, 0]));

  rows.forEach((row) => {
    pollutantKeys.forEach((key) => {
      const value = getMetricValue(row, key);
      if (value > 0) {
        sums[key] += value;
        counts[key] += 1;
      }
    });
  });

  return pollutantKeys.reduce((acc, key) => {
    acc[key] = counts[key] ? sums[key] / counts[key] : 0;
    return acc;
  }, {});
}

function getMetricValue(row, key) {
  const candidates = [
    row[key],
    row[`${key}_mean`],
    row[`${key}_monthly_mean`],
    row[`${key}_avg`],
  ];

  for (const candidate of candidates) {
    const num = Number(candidate);
    if (!Number.isNaN(num) && Number.isFinite(num)) {
      return num;
    }
  }

  return 0;
}

function calculateSimilarProvincesForMonth(rows, targetProvince, topN = 3) {
  if (!rows || rows.length === 0 || !targetProvince) {
    return [];
  }

  const provinceGroups = new Map();
  rows.forEach((row) => {
    const normalized = normalizeProvince(row.province);
    if (!normalized) return;
    if (!provinceGroups.has(normalized)) {
      provinceGroups.set(normalized, []);
    }
    provinceGroups.get(normalized).push(row);
  });

  const provinceAverages = new Map();
  provinceGroups.forEach((groupRows, province) => {
    provinceAverages.set(province, computeAverageByPollutant(groupRows));
  });

  const targetAvg = provinceAverages.get(targetProvince);
  if (!targetAvg) {
    return [];
  }

  const distances = [];

  provinceAverages.forEach((averages, province) => {
    if (province === targetProvince) return;
    const distance = Math.sqrt(
      pollutantKeys.reduce((sum, key) => {
        const diff =
          normalizeForDistance(averages[key], key) -
          normalizeForDistance(targetAvg[key], key);
        return sum + diff * diff;
      }, 0)
    );
    distances.push({ province, distance });
  });

  distances.sort((a, b) => a.distance - b.distance);
  return distances.slice(0, topN).map((item) => item.province);
}

function normalizeForDistance(value, pollutant) {
  const baseline = pollutantStandards[pollutant] || 1;
  return Math.log1p(Math.max(value, 0) / baseline);
}

watch(
  () => props.currentYear,
  async () => {
    console.log(
      `[MonthView] Watch currentYear triggered for year: ${props.currentYear}`
    );
    await initMapData();
    console.log(`[MonthView] initMapData done`);

    await loadMonthlyAggregatedData();
    console.log(
      `[MonthView] loadMonthlyAggregatedData done, data length: ${monthlyAggregatedData.value.length}`
    );

    // 已经在 loadMonthlyAggregatedData 中调用了 loadMonthDetail，无需重复
  },
  { immediate: true }
);

watch(
  () => props.metric,
  async () => {
    // 指标改变时，重新加载数据
    if (monthlyAggregatedData.value.length === 0) {
      console.log(
        `[MonthView] Watch metric triggered, but monthlyAggregatedData empty, loading...`
      );
      await loadMonthlyAggregatedData();
    }
  }
);
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
  background: #ffe600;
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

.scope-indicator {
  font-size: 12px;
  color: #666;
  margin: 4px 0 12px;
  font-family: "JetBrains Mono", monospace;
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

.year-selector,
.month-selector {
  display: flex;
  align-items: center;
  gap: 12px;
}

.year-selector label,
.month-selector label {
  color: #ffe600;
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
  border-color: #ffe600;
  color: #0a0a0a;
  background: transparent;
}

.month-chip.active {
  background: #ffe600;
  color: #000;
  font-weight: bold;
  border-color: #ffe600;
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
  background: rgba(255, 255, 255, 0.95);
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
  background: rgba(255, 255, 255, 0.95);
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
  background: rgba(0, 0, 0, 0.8);
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
  background: #ffe600;
  color: #000;
  font-weight: bold;
}

.divider {
  width: 1px;
  height: 16px;
  background: #ddd;
  margin: 0 4px;
}

.metric-toggle,
.weather-toggle {
  display: flex;
  gap: 2px;
}

.metric-toggle button,
.weather-toggle button {
  background: #fff;
  border: 1px solid #ddd;
  color: #444;
  padding: 2px 6px;
  font-family: "JetBrains Mono", monospace;
  font-size: 11px;
  cursor: pointer;
  border-radius: 0;
}

.metric-toggle button:hover,
.weather-toggle button:hover {
  color: #0a0a0a;
  border-color: #666;
}

.metric-toggle button.active,
.weather-toggle button.active {
  background: #ffe600;
  color: #000;
  border-color: #ffe600;
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
  background: rgba(0, 0, 0, 0.02);
}

.placeholder-content {
  text-align: center;
}

.placeholder-content h4 {
  color: #ffe600;
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

.pane.full-width-pane {
  grid-column: 1 / -1;
  margin-bottom: 20px;
  width: 100%;
  box-sizing: border-box;
}

.single {
  grid-template-columns: 1fr;
}
</style>
