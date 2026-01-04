<template>
  <div class="bg">
    <div class="bg-layer"></div>
    <div class="page">
      <header class="topbar">
        <div class="title-block">
          <h1>污染与气象 · 可视分析</h1>
          <p class="subtitle">2013 年日均数据 · 多视角洞察</p>
        </div>
        <div class="controls-block">
          <nav class="tabs">
            <RouterLink to="/overview" :class="{ active: isOverview }">概览</RouterLink>
            <RouterLink to="/story" :class="{ active: isStory }">感知</RouterLink>
            <RouterLink to="/types" :class="{ active: isTypes }">类型分析</RouterLink>
            <RouterLink to="/trends" :class="{ active: isTrends }">趋势对比</RouterLink>
            <RouterLink to="/monthly" :class="{ active: isMonthly }">月度分析补充</RouterLink>
          </nav>
          <div class="view-controls">
            <div class="view-toggle">
              <button :class="{ active: viewMode === 'daily' }" @click="viewMode = 'daily'">日均视图</button>
              <button :class="{ active: viewMode === 'monthly' }" @click="viewMode = 'monthly'">月份视图</button>
            </div>
          </div>
          <YearControls
            :current-year="viewMode === 'daily' ? currentYear : monthViewYear"
            :available-years="availableYears"
            @update:year="handleYearChange"
          />
          <TimeControls
            v-if="viewMode === 'daily'"
            :granularity="granularity"
            :metric="metric"
            :date-options="availableDates"
            :current-date="currentDate"
            @update:granularity="handleGranularityChange"
            @update:metric="metric = $event"
            @update:date="handleDateChange"
          />
        </div>
      </header>

      <template v-if="isOverview">
        <!-- 日均视图 -->
        <template v-if="viewMode === 'daily'">
          <ControlPanel
            class="pane"
            :date="currentDate"
            :region="selectedRegion || '全国'"
            :rows="dayData"
            :metric="metric"
            :map-mode="mapMode"
            @select-metric="metric = $event"
            @toggle-map-mode="mapMode = $event"
            @reset-region="selectedRegion = ''"
          />
          <section class="layout">
            <div class="pane map-pane">
              <div class="map-switch">
                <button :class="{ active: mapMode === 'pollution' }" @click="mapMode = 'pollution'">污染</button>
                <button :class="{ active: mapMode === 'weather' }" @click="mapMode = 'weather'">气象</button>
                <button :class="{ active: mapMode === 'type' }" @click="mapMode = 'type'">类型</button>
                <div v-if="mapMode === 'weather'" class="weather-toggle">
                  <button :class="{ active: weatherMetric === 'wind' }" @click="weatherMetric = 'wind'">风速</button>
                  <button :class="{ active: weatherMetric === 'temp' }" @click="weatherMetric = 'temp'">气温</button>
                  <button :class="{ active: weatherMetric === 'rh' }" @click="weatherMetric = 'rh'">湿度</button>
                  <button :class="{ active: weatherMetric === 'psfc' }" @click="weatherMetric = 'psfc'">气压</button>
                </div>
              </div>
              <MapPanel
                v-if="mapMode === 'pollution'"
                :data="mapSeries"
                :metric="metric"
                :title="`地图：${metric}`"
                :scatter="scatterPoints"
                :heatmap="heatmapPoints"
                :selected-name="selectedRegion"
                @select="handleMapSelect"
              />
              <MapPanel
                v-else-if="mapMode === 'weather'"
                :data="weatherMapSeries"
                :metric="weatherMetricLabel"
                :title="`气象：${weatherMetricLabel}`"
                mode="weather"
                :scatter="scatterPoints"
                :wind="windVectors"
                :flow="windFlow"
                :selected-name="selectedRegion"
                @select="handleMapSelect"
              />
              <TypeMap v-else :items="typeMapData" :selected-name="selectedRegion" />
            </div>
            <div class="pane side-pane">
              <LevelBar :levels="levelStats" />
              <TrendLine
                class="mt"
                :metric="metric"
                :series="trendSeries"
                :dates="trendDates"
              />
              <RadialPollutant class="mt" :data="radialVector" />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <SeasonalLevelStack
                :dates="levelTimeline.dates"
                :series="levelTimeline.series"
                :metric="metric"
                @select-date="handleDateChange"
              />
            </div>
            <div class="pane">
              <CorrHeatmap :matrix="corrMatrix" />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <ParallelAQI :rows="parallelRows" @select="handleParallelSelect" />
              <div class="parallel-actions">
                <span>当前维度：{{ parallelLevel === "province" ? "省均值" : `城市（${parallelProvince || "未选"}` }} </span>
                <button @click="resetParallel">重置到省</button>
              </div>
            </div>
            <div class="pane">
              <AQIRanking :items="aqiRanking" @select="handleRankingSelect" />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <CityStackedPie
                :city="selectedCity"
                :day-values="cityDayValues"
                :month-stats="cityMonthStats"
                :month="currentDate.slice(0, 7)"
              />
            </div>
            <div class="pane">
              <CityTypeRibbon
                :dates="cityTypeRibbon.dates"
                :series="cityTypeRibbon.series"
                :type-order="cityTypeRibbon.typeOrder"
                :province="selectedRegion"
              />
            </div>
          </section>

          <!-- 城市污染日历 -->
          <section class="layout single">
            <div class="pane">
              <CityPollutionCalendar />
            </div>
          </section>
        </template>

        <!-- 月份视图 -->
        <template v-else-if="viewMode === 'monthly'">
          <MonthView
            :current-year="monthViewYear"
            :available-years="availableYears"
            :metric="monthViewMetric"
            :selected-region="selectedRegion"
            @update:region="handleMapSelect"
            @select-month="handleMonthSelect"
            @update:metric="monthViewMetric = $event"
            @update:currentYear="monthViewYear = $event"
          />
        </template>
      </template>

      <template v-else-if="isStory">
        <div class="section-heading">
          <div class="section-badge">感知模式</div>
          <div class="section-meta">时间自动推进 · 观感优先</div>
        </div>
        <ControlPanel
          class="pane"
          :date="storyDate"
          :region="selectedRegion || '全国'"
          :rows="storyDayData"
          :metric="metric"
          :map-mode="mapMode"
          @select-metric="metric = $event"
          @toggle-map-mode="mapMode = $event"
          @reset-region="selectedRegion = ''"
        />
        <section class="story-hero">
          <div class="story-visual">
            <div
              class="story-glow"
              :style="{ background: `radial-gradient(circle at 30% 30%, ${storyMood.color}33, transparent 50%)` }"
            ></div>
            <MapPanel
              :data="storyMapSeries"
              :metric="metric"
              :title="`时间流动 · ${storyDate || '加载中'}`"
              :scatter="storyScatter"
              :selected-name="selectedRegion"
              @select="handleMapSelect"
            />
            <div class="story-overlay">
              <div class="story-chip">感知模式 · 自动播放</div>
              <div class="story-date">{{ storyDate || "…" }}</div>
              <div class="story-mood" :style="{ color: storyMood.color }">{{ storyMood.label }}</div>
              <div class="story-progress">
                <div class="story-progress-bar" :style="{ width: `${storyProgress}%` }"></div>
              </div>
            </div>
          </div>
          <div class="story-side pane">
            <div class="story-side-header">
              <span class="story-chip alt">感受污染节律</span>
              <div class="story-note">时间自动推进 · 颜色与密度随日均值渐变</div>
            </div>
            <RadialPollutant :data="storyRadial" />
          </div>
        </section>
      </template>

      <template v-else-if="isTypes">
        <div class="section-heading">
          <div class="section-badge">类型分析</div>
          <div class="section-meta">类型地图 · 聚类散点 · 类型演化</div>
        </div>

        <ControlPanel
          class="pane"
          :date="currentDate"
          :region="selectedRegion || '全国'"
          :rows="dayData"
          :metric="metric"
          :map-mode="mapMode"
          @select-metric="metric = $event"
          @toggle-map-mode="mapMode = $event"
          @reset-region="selectedRegion = ''"
        />

        <section class="layout secondary">
          <div class="pane map-pane">
            <TypeMap :items="typeMapData" :selected-name="selectedRegion" />
          </div>
          <div class="pane">
            <TypeScatter :points="typeScatter" @select="handleTypeSelect" />
          </div>
        </section>

        <section class="layout secondary">
          <div class="pane">
            <TypeBump :dates="typeTimeline.dates" :series="typeTimeline.series" />
          </div>
          <div class="pane">
            <CityTypeRibbon
              :dates="cityTypeRibbon.dates"
              :series="cityTypeRibbon.series"
              :type-order="cityTypeRibbon.typeOrder"
              :province="selectedRegion"
            />
          </div>
        </section>

        <section class="layout secondary">
          <div class="pane">
            <WindCompass :data="windRose" />
          </div>
          <div class="pane">
            <TypeScatter :points="tsneScatter" @select="handleTypeSelect" />
          </div>
        </section>

        <section class="layout single">
          <div class="pane">
            <PollutantRingGrid :items="ringGrid" :metric="metric" />
          </div>
        </section>
      </template>

      <template v-else-if="isTrends">
        <div class="section-heading">
          <div class="section-badge">趋势对比</div>
          <div class="section-meta">跨年雷达 · 月均 · 晴雨图 · 折线</div>
        </div>
        <section class="layout tertiary">
          <div class="pane">
            <MultiYearRing :items="yearlyRings" />
          </div>
          <div class="pane">
            <MonthlyRing :items="monthlyRings" />
          </div>
          <div class="pane">
            <AQIRain :matrix="aqiRain" />
          </div>
          <div class="pane">
            <AQICompareLine :days="aqiCompare.days" :series="aqiCompare.series" />
          </div>
        </section>
      </template>

      <!-- 在现有的模板块之后添加 -->
      <template v-else-if="isMonthly">
        <div class="section-heading">
          <div class="section-badge">月度分析补充</div>
          <div class="section-meta">补充</div>
        </div>

        <!-- 时间选择控件 -->
        <div class="monthly-controls">
          <div class="time-selector">
            <label>年份：</label>
            <select v-model="selectedYear" @change="handleMonthlyYearChange">
              <option v-for="year in monthlyAvailableYears" :key="year" :value="year">{{ year }}年</option>
            </select>

            <label>月份：</label>
            <select v-model="selectedMonth" @change="handleMonthChange">
              <option v-for="month in availableMonths" :key="month" :value="month">{{ month }}月</option>
            </select>
          </div>

          <div class="metric-selector">
            <label>指标：</label>
            <select v-model="monthlyMetric">
              <option value="pm25">PM2.5</option>
              <option value="pm10">PM10</option>
              <option value="so2">SO₂</option>
              <option value="no2">NO₂</option>
              <option value="co">CO</option>
              <option value="o3">O₃</option>
            </select>
          </div>
        </div>

        <!-- 月度分析内容 -->
        <ControlPanel
          class="pane"
          :date="currentMonthlyPeriod"
          :region="selectedRegion || '全国'"
          :rows="monthlyData"
          :metric="monthlyMetric"
          :map-mode="mapMode"
          @select-metric="monthlyMetric = $event"
          @toggle-map-mode="mapMode = $event"
        />

        <section class="layout">
<!--          <div class="pane map-pane">-->
<!--            <div class="map-switch">-->
<!--              <button :class="{ active: mapMode === 'pollution' }" @click="mapMode = 'pollution'">污染</button>-->
<!--              <button :class="{ active: mapMode === 'weather' }" @click="mapMode = 'weather'">气象</button>-->
<!--              <button :class="{ active: mapMode === 'type' }" @click="mapMode = 'type'">类型</button>-->
<!--            </div>-->

<!--            <MapPanel-->
<!--              v-if="mapMode === 'pollution'"-->
<!--              :data="monthlyMapSeries"-->
<!--              :metric="monthlyMetric"-->
<!--              :title="`${currentMonthlyPeriod} ${monthlyMetric.toUpperCase()} 月均分布`"-->
<!--              :selected-name="selectedRegion"-->
<!--              @select="handleMapSelect"-->
<!--            />-->

<!--            <MapPanel-->
<!--              v-else-if="mapMode === 'weather'"-->
<!--              :data="monthlyWeatherMapSeries"-->
<!--              :metric="weatherMetricLabel"-->
<!--              :title="`${currentMonthlyPeriod} ${weatherMetricLabel} 月均分布`"-->
<!--              mode="weather"-->
<!--              :selected-name="selectedRegion"-->
<!--              @select="handleMapSelect"-->
<!--            />-->

<!--            <TypeMap v-else :items="monthlyTypeMapData" />-->
<!--          </div>-->

          <div class="pane side-pane">
            <div class="stats-panel">
              <h3>月度统计</h3>
              <div class="stat-item">
                <span class="stat-label">数据点数：</span>
                <span class="stat-value">{{ monthlyData.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">{{ monthlyMetric.toUpperCase() }} 均值：</span>
                <span class="stat-value">{{ monthlyAvgValue.toFixed(2) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最高值：</span>
                <span class="stat-value">{{ monthlyMaxValue.toFixed(2) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最低值：</span>
                <span class="stat-value">{{ monthlyMinValue.toFixed(2) }}</span>
              </div>
            </div>

            <MonthlyRadar class="mt" :data="monthlyRadarData" />
          </div>
        </section>

<!--        <section class="layout secondary">-->
<!--          <div class="pane">-->
<!--            <h3>月度趋势对比</h3>-->
<!--            <MonthlyTrendChart-->
<!--              :year="selectedYear"-->
<!--              :metric="monthlyMetric"-->
<!--              :data="multiYearMonthlyData"-->
<!--            />-->
<!--          </div>-->
<!--          <div class="pane">-->
<!--            <h3>污染物比例</h3>-->
<!--            <PollutantPie :data="monthlyPollutantShares" />-->
<!--          </div>-->
<!--        </section>-->

        <!-- 在现有的月度分析模板中，在第二个section后添加以下内容 -->

<!--        <section class="layout secondary">-->
<!--          <div class="pane">-->
<!--            <h3>月度等级分布</h3>-->
<!--            <LevelBar :levels="monthlyLevelStats" />-->
<!--          </div>-->
<!--          <div class="pane">-->
<!--            <h3>月度趋势</h3>-->
<!--            <TrendLine-->
<!--              :metric="monthlyMetric"-->
<!--              :series="monthlyTrendSeries"-->
<!--              :dates="monthlyTrendDates"-->
<!--            />-->
<!--          </div>-->
<!--        </section>-->

        <section class="layout secondary">
          <div class="pane">
            <h3>污染物径向图</h3>
            <RadialPollutant :data="monthlyRadialVector" />
          </div>
          <div class="pane">
            <h3>相关性分析</h3>
            <CorrHeatmap :matrix="monthlyCorrMatrix" />
          </div>
        </section>

        <section class="layout secondary">
          <div class="pane">
            <h3>城市排名</h3>
            <AQIRanking :items="monthlyAQIRanking" @select="handleRankingSelect" />
          </div>
          <div class="pane">
            <h3>平行坐标</h3>
            <ParallelAQI :rows="monthlyParallelRows" @select="handleParallelSelect" />
          </div>
        </section>

<!--        <section class="layout secondary">-->
<!--          <div class="pane">-->
<!--            <h3>城市详细分析</h3>-->
<!--            <CityStackedPie-->
<!--              :city="selectedRegion"-->
<!--              :day-values="monthlyCityValues"-->
<!--              :month-stats="monthlyCityStats"-->
<!--              :month="currentMonthlyPeriod"-->
<!--            />-->
<!--          </div>-->
<!--          <div class="pane">-->
<!--            <h3>类型演变</h3>-->
<!--            <CityTypeRibbon-->
<!--              :dates="monthlyTypeRibbon.dates"-->
<!--              :series="monthlyTypeRibbon.series"-->
<!--              :type-order="monthlyTypeRibbon.typeOrder"-->
<!--              :province="selectedRegion"-->
<!--            />-->
<!--          </div>-->
<!--        </section>-->

      </template>

    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, provide } from "vue";
import { useRoute, useRouter } from "vue-router";
import TimeControls from "./components/TimeControls.vue";
import YearControls from "./components/YearControls.vue";
import MapPanel from "./components/MapPanel.vue";
import ControlPanel from "./components/ControlPanel.vue";
import TrendLine from "./components/TrendLine.vue";
import LevelBar from "./components/LevelBar.vue";
import RadialPollutant from "./components/RadialPollutant.vue";
import SeasonalLevelStack from "./components/SeasonalLevelStack.vue";
import CorrHeatmap from "./components/CorrHeatmap.vue";
import AQIRanking from "./components/AQIRanking.vue";
import ParallelAQI from "./components/ParallelAQI.vue";
import TypeMap from "./components/TypeMap.vue";
import TypeScatter from "./components/TypeScatter.vue";
import TypeBump from "./components/TypeBump.vue";
import MultiYearRing from "./components/MultiYearRing.vue";
import MonthlyRing from "./components/MonthlyRing.vue";
import AQIRain from "./components/AQIRain.vue";
import AQICompareLine from "./components/AQICompareLine.vue";
import WindCompass from "./components/WindCompass.vue";
import PollutantRingGrid from "./components/PollutantRingGrid.vue";
import CityStackedPie from "./components/CityStackedPie.vue";
import CityTypeRibbon from "./components/CityTypeRibbon.vue";
import MonthView from "./components/MonthView.vue";
import CityPollutionCalendar from "./components/CityPollutionCalendar.vue";
import {
  classifyLevels,
  computeRadialVector,
  computeTrendSeries,
  computeLevelTimeline,
  computeCorrMatrix,
  loadIndex,
  loadOneDay,
  loadRegionIndex,
  rowsToScatter,
  buildWindVectors,
  attachAQI,
  computeAQIRanking,
  buildParallelData,
  computeTypeByRegion,
  buildTypeScatter,
  computeTypeTimeline,
  computeYearlyRadial,
  computeAQIRain,
  computeAQICompareLines,
  computeMonthlyRing,
  buildFeatureScatterTSNE,
  computeWindRose,
  buildWindFlow,
  computeMonthlyRingGrid,
  computeCityMonthStats,
  computeCityTypeTrajectory,
  loadAvailableYears,
  loadDataByGranularity,
  getAvailableDatesByGranularity,
  computeTrendSeriesByGranularity,
  computeLevelTimelineByGranularity,
  loadGridData,     // <--- 确保引入
  gridToScatter,    // <--- 确保引入
  normalizeProvince,
} from "./utils/dataLoader";

const granularity = ref("day");
const metric = ref("pm25");
const availableDates = ref([]);
const currentDate = ref("");
const dayData = ref([]);
const allDays = ref([]);
const route = useRoute();
const router = useRouter();
const regionIndex = ref(null);
const gridData = ref([]);

// 视图模式：daily 或 monthly
const viewMode = ref("daily");

const monthViewYear = ref("2013");
const monthViewMetric = ref("pm25");

// 新增年份相关变量
const currentYear = ref("2013");
const availableYears = ref(["2013"]);



function aggregateMap(rows, metricName, granularity = "day") {
  console.log(`[DataDebug] 聚合地图数据: metricName=${metricName}, granularity=${granularity}, rows.length=${rows.length}`);
  const sums = new Map();
  const counts = new Map();
  for (const row of rows) {
    const prov = normalizeProvince(row.province);
    // 使用新的字段适配逻辑
    const actualField = granularity === "day" ? metricName :
                       granularity === "month" ? `${metricName}_mean` :
                       granularity === "year" ? `${metricName}_yearly_mean` : metricName;
    const val = Number(row[actualField] ?? 0);
    // console.log(`[DataDebug] 聚合行: province=${row.province}, normalized=${prov}, field=${actualField}, value=${val}`);
    if (!prov || Number.isNaN(val)) continue;
    sums.set(prov, (sums.get(prov) || 0) + val);
    counts.set(prov, (counts.get(prov) || 0) + 1);
  }
  const result = Array.from(sums.entries()).map(([prov, sum]) => ({
    name: prov,
    value: sum / (counts.get(prov) || 1),
  }));
  console.log(`[DataDebug] 聚合结果:`, result);
  return result;
}

const mapSeries = computed(() => aggregateMap(dayData.value, metric.value, granularity.value));

const levelStats = computed(() =>
  classifyLevels(dayData.value, metric.value)
);

const radialVector = computed(() => computeRadialVector(dayData.value));

const trendSeries = computed(() =>
  computeTrendSeriesByGranularity(allDays.value, metric.value, granularity.value)
);

const trendDates = computed(() => allDays.value.map((item) => item.date));

const levelTimeline = computed(() =>
  computeLevelTimelineByGranularity(allDays.value, metric.value, granularity.value)
);

const corrMatrix = computed(() =>
  computeCorrMatrix(
    allDays.value,
    ["pm25", "pm10", "so2", "no2", "o3"],
    ["temp", "rh", "psfc"]
  )
);

const aqiRanking = computed(() =>
  computeAQIRanking(dayData.value, "province", 15)
);
const ringGrid = computed(() =>
  computeMonthlyRingGrid(
    allDays.value,
    metric.value,
    aqiRanking.value.map((i) => i.name),
    12
  )
);
const currentMonth = computed(() => Number((currentDate.value || "2013-01-01").split("-")[1]));
const selectedCity = computed(() => selectedRegion.value || aqiRanking.value[0]?.name || "");
const cityMonthStats = computed(() =>
  computeCityMonthStats(allDays.value, selectedCity.value, currentMonth.value)
);
const cityDayValues = computed(() => {
  console.log(`[DataDebug] 计算城市日均值: selectedCity=${selectedCity.value}, granularity=${granularity.value}, data.length=${dayData.value.length}`);
  if (!selectedCity.value && !dayData.value.length) return {};
  const target = normalizeProvince(selectedCity.value) || normalizeProvince(dayData.value[0]?.city) || "";
  const row =
    dayData.value.find(
      (r) =>
        normalizeProvince(r.city) === target ||
        normalizeProvince(r.province) === target
    ) || dayData.value[0] || {};

  console.log(`[DataDebug] 找到的目标行:`, row);

  // 根据粒度获取正确的字段
  const getFieldValue = (field) => {
    if (granularity.value === "day") return row[field];
    if (granularity.value === "month") return row[`${field}_mean`];
    if (granularity.value === "year") return row[`${field}_yearly_mean`];
    return row[field];
  };

  const result = {
    pm25: getFieldValue("pm25"),
    pm10: getFieldValue("pm10"),
    so2: getFieldValue("so2"),
    no2: getFieldValue("no2"),
    co: getFieldValue("co"),
    o3: getFieldValue("o3"),
  };

  console.log(`[DataDebug] 城市日均值结果:`, result);
  return result;
});

const cityTypeRibbon = computed(() =>
  computeCityTypeTrajectory(allDays.value, selectedRegion.value || null, currentMonth.value)
);

const parallelRows = computed(() =>
  buildParallelData(
    dayData.value,
    parallelLevel.value === "province" ? "province" : "city",
    30,
    parallelLevel.value === "city" ? parallelProvince.value : null
  )
);

// 地图使用省级底图，按省聚合类型。
const typeMapData = computed(() =>
  computeTypeByRegion(dayData.value, "province").map((item) => ({
    ...item,
    name: normalizeProvince(item.name),
    type: item.type || "未知",
    primary: item.primary || "-",
  }))
);
const typeScatter = computed(() => buildTypeScatter(dayData.value, "city"));
const typeTimeline = computed(() => computeTypeTimeline(allDays.value, "city", selectedRegion.value || null));

const weatherMetric = ref("wind");
const weatherMapSeries = computed(() => aggregateMap(dayData.value, weatherMetric.value, granularity.value));
const weatherMetricLabel = computed(() => {
  const map = { wind: "风速", temp: "气温", rh: "湿度", psfc: "气压" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

const scatterPoints = computed(() => {
  // 如果有网格数据，优先使用网格数据进行渲染
  if (gridData.value && gridData.value.length > 0) {
    const targetMetric = mapMode.value === "weather" ? weatherMetric.value : metric.value;
    // 如果是风速模式，通常不画散点，画箭头；但如果想看风速点也可以保留
    if (mapMode.value === "weather" && weatherMetric.value === "wind") return []; 
    return gridToScatter(gridData.value, targetMetric);
  }

  // 降级回退到城市数据 (旧逻辑)
  if (!regionIndex.value) return [];
  if (mapMode.value === "weather" && weatherMetric.value === "wind") return [];
  return rowsToScatter(
    dayData.value,
    mapMode.value === "weather" ? weatherMetric.value : metric.value,
    regionIndex.value
  );
});

// 风场箭头 (Wind Vectors)
const windVectors = computed(() => {
  if (mapMode.value === "weather" && weatherMetric.value === "wind") {
    // 优先使用网格数据
    const source = (gridData.value && gridData.value.length > 0) ? gridData.value : dayData.value;
    const index = (gridData.value && gridData.value.length > 0) ? null : regionIndex.value; // 网格数据不需要 index
    return buildWindVectors(source, index, 0.10);
  }
  return [];
});

// 风场流线 (Wind Flow)
const windFlow = computed(() => {
  if (mapMode.value === "weather" && weatherMetric.value === "wind") {
    // 优先使用网格数据
    const source = (gridData.value && gridData.value.length > 0) ? gridData.value : dayData.value;
    const index = (gridData.value && gridData.value.length > 0) ? null : regionIndex.value;
    // 网格数据较密，流线密度参数(density)可以适当调低，这里设为 1 或 2
    return buildWindFlow(source, index, 0.35, 2);
  }
  return [];
});

// 热力图数据 (Heatmap)
const heatmapPoints = computed(() => {
  if (mapMode.value === "pollution") {
    // 优先使用网格数据
    if (gridData.value && gridData.value.length > 0) {
      // 复用 gridToScatter 逻辑并转换格式 [lon, lat, value]
      return gridToScatter(gridData.value, metric.value).map(p => [p.coord[0], p.coord[1], p.value]);
    }
    
    // 回退旧逻辑
    if (regionIndex.value) {
      return rowsToScatter(dayData.value, metric.value, regionIndex.value).map((d) => [
        d.coord[0],
        d.coord[1],
        d.value,
      ]);
    }
  }
  return [];
});

const yearlyRings = computed(() => computeYearlyRadial(allDays.value));
const monthlyRings = computed(() => computeMonthlyRing(allDays.value));
const aqiRain = computed(() => computeAQIRain(allDays.value, 1));
const aqiCompare = computed(() => computeAQICompareLines(allDays.value, 1));

const tsneScatter = computed(() => buildFeatureScatterTSNE(dayData.value, "city"));
const windRose = computed(() => computeWindRose(dayData.value));
const windSummary = computed(() => {
  const arr = windRose.value || [];
  if (!arr.length) return { maxDir: "-", maxVal: 0, avg: 0 };
  const max = arr.reduce((a, b) => (b.value > a.value ? b : a), arr[0]);
  const avg = arr.reduce((s, d) => s + (d.value || 0), 0) / arr.length;
  return {
    maxDir: max.dir || "-",
    maxVal: Number((max.value || 0).toFixed(2)),
    avg: Number(avg.toFixed(2)),
  };
});

const mapMode = ref("pollution"); // pollution | weather | type
const selectedRegion = ref("");
const parallelLevel = ref("province");
const parallelProvince = ref(null);

const isOverview = computed(() => route.name === "overview");
const isStory = computed(() => route.name === "story");
const isTypes = computed(() => route.name === "types");
const isTrends = computed(() => route.name === "trends");

const storyIndex = ref(0);
const storyRunning = ref(true);
let storyTimer = null;

const storyDate = computed(() => allDays.value[storyIndex.value]?.date || "");
const storyDayData = computed(() => allDays.value[storyIndex.value]?.data || []);
const storyMapSeries = computed(() => aggregateMap(storyDayData.value, metric.value));
const storyScatter = computed(() =>
  regionIndex.value ? rowsToScatter(storyDayData.value, mapMode.value === "weather" ? weatherMetric.value : metric.value, regionIndex.value) : []
);
const storyProgress = computed(() =>
  allDays.value.length ? Math.round((storyIndex.value / Math.max(allDays.value.length - 1, 1)) * 100) : 0
);
const storyRadial = computed(() => computeRadialVector(storyDayData.value));
const storyMood = computed(() => {
  const m = Number(storyDate.value.slice(5, 7) || 1);
  if ([12, 1, 2].includes(m)) return { label: "冬季 · 污染高发", color: "#eab308" };
  if ([3, 4, 5].includes(m)) return { label: "春季 · 回暖扩散", color: "#22c55e" };
  if ([6, 7, 8].includes(m)) return { label: "夏季 · 相对清透", color: "#38bdf8" };
  return { label: "秋季 · 渐冷积聚", color: "#f97316" };
});

async function bootstrap() {
  // 初始化默认选中区域
  if (viewMode.value === 'monthly') {
    selectedRegion.value = "长沙市";
  } else {
    selectedRegion.value = ""; // 日均视图默认全国
  }

  // 加载可用年份
  const years = await loadAvailableYears();
  availableYears.value = years;
  if (!years.includes(currentYear.value)) {
    currentYear.value = years[0] || "2013";
  }

  // 加载当前年份的数据
  await loadDataForCurrentGranularity();

  regionIndex.value = await loadRegionIndex();

  startStoryLoop();
}

// 加载当前粒度的数据
async function loadDataForCurrentGranularity() {
  try {
    // 获取当前粒度的可用日期
    const dates = await getAvailableDatesByGranularity(granularity.value, currentYear.value);
    availableDates.value = dates;

    // 设置默认日期
    if (!currentDate.value || !dates.includes(currentDate.value)) {
      currentDate.value = dates[0] || `${currentYear.value}-01-01`;
    }

    // 加载当前日期的数据
    if (granularity.value === "day") {
      const data = await loadDataByGranularity("day", currentYear.value, currentDate.value);
      dayData.value = data;

      // (2) 【新增】并发加载网格数据 (用于地图展示)
      // 注意：网格数据量大，加载可能稍慢
      console.log(`[App] Loading grid data for ${currentDate.value}...`);
      const grid = await loadGridData(currentDate.value);
      gridData.value = grid; // 保存网格数据

      // 预加载所有天的数据用于趋势线
      const loadedAll = [];
      for (const day of dates) {
        const dayData = await loadDataByGranularity("day", currentYear.value, day);
        if (dayData.length) {
          loadedAll.push({ date: day, data: dayData });
        }
      }
      allDays.value = loadedAll;
    } else {
      // 非日粒度时，清空网格数据 (假设目前只有日粒度有网格)
      gridData.value = [];
      // 对于月度和年度数据，直接加载当前选择的数据
      const data = await loadDataByGranularity(granularity.value, currentYear.value, currentDate.value);
      dayData.value = data;

      // 对于月度，加载全年所有月份用于趋势
      if (granularity.value === "month") {
        const loadedAll = [];
        for (const month of dates) {
          const monthData = await loadDataByGranularity("month", currentYear.value, month);
          if (monthData.length) {
            loadedAll.push({ date: month, data: monthData });
          }
        }
        allDays.value = loadedAll;
      } else {
        // 年粒度只有一个数据点
        allDays.value = [{ date: currentYear.value, data }];
      }
    }
  } catch (error) {
    console.error("Failed to load data:", error);
    dayData.value = [];
    allDays.value = [];
  }
}

async function handleDateChange(value) {
  currentDate.value = value;
  if (granularity.value === "day") {
    const data = await loadDataByGranularity("day", currentYear.value, value);
    dayData.value = data;
  } else {
    // 对于月度和年度，直接重新加载
    await loadDataForCurrentGranularity();
  }
}

async function handleYearChange(value) {
  if (viewMode.value === 'daily') {
    // 日均视图模式：更新 currentYear 并重新加载数据
    currentYear.value = value;
    await loadDataForCurrentGranularity();
  } else {
    // 月份视图模式：只更新 monthViewYear，MonthView 组件内部会监听并自动刷新
    monthViewYear.value = value;
  }
}

async function handleGranularityChange(value) {
  granularity.value = value;
  await loadDataForCurrentGranularity();
}

function handleRankingSelect(name) {
  selectedRegion.value = name;
}

function handleMapSelect(name) {
  selectedRegion.value = name;
}

function handleParallelSelect(name) {
  if (parallelLevel.value === "province") {
    parallelLevel.value = "city";
    parallelProvince.value = name;
  }
}

function resetParallel() {
  parallelLevel.value = "province";
  parallelProvince.value = null;
}

function handleTypeSelect(name) {
  selectedRegion.value = name;
}

function handleMonthSelect(month) {
  // 可以在这里处理月份选择逻辑
  console.log(`Selected month: ${month}`);
}

function startStoryLoop() {
  if (storyTimer || !allDays.value.length) return;
  storyTimer = setInterval(() => {
    storyIndex.value = (storyIndex.value + 1) % allDays.value.length;
  }, 1200);
}

function stopStoryLoop() {
  if (storyTimer) {
    clearInterval(storyTimer);
    storyTimer = null;
  }
}

watch(
  () => route.name,
  (name) => {
    if (name === "story") {
      startStoryLoop();
    } else {
      stopStoryLoop();
    }
  }
);

onBeforeUnmount(() => {
  stopStoryLoop();
});

// 【新增】提供一个修改方法给后代组件使用
const setSelectedRegion = (name) => {
  console.log("更新选中区域:", name); // 方便调试
  selectedRegion.value = name;
};
provide('setSelectedRegion', setSelectedRegion);

// 【新增】监听路由变化，实现视图状态隔离
watch(() => route.path, (newPath, oldPath) => {
  // 只要切换了顶层导航（路由），就重置选中区域
  if (newPath !== oldPath) {
    // 月视图默认长沙市，其他视图（包括日视图和类型分析视图）默认全国
    if (viewMode.value === 'monthly') {
      selectedRegion.value = "长沙市";
    } else {
      selectedRegion.value = ""; // 日视图和类型分析视图都默认全国
    }
    console.log("视图切换，设置 selectedRegion:", selectedRegion.value);
  }
});

watch(viewMode, () => {
  // 切换到月视图时，设置默认选中长沙市
  if (viewMode.value === 'monthly') {
    selectedRegion.value = "长沙市";
  } else {
    selectedRegion.value = "";
  }
  console.log("视图模式切换(日/月)，设置 selectedRegion:", selectedRegion.value);
});

watch(metric, () => {
  // Metric change just reuses loaded data; computed props react automatically.
});

onMounted(() => {
  bootstrap();
});



import {
  loadMonthlyData,
  getAvailableYears,
  getAvailableMonths,
  getAvailableMonthlyPeriods
} from "./utils/dataLoader";

// 月度分析相关状态
const isMonthly = computed(() => route.name === "monthly");

// 月度选择相关
const selectedYear = ref("2013");
const selectedMonth = ref("01");
const monthlyMetric = ref("pm25");
const monthlyData = ref([]);
const monthlyAvailableYears = getAvailableYears();
const availableMonths = getAvailableMonths();

// 计算属性
const currentMonthlyPeriod = computed(() => `${selectedYear.value}-${selectedMonth.value}`);
const monthlyMapSeries = computed(() => aggregateMap(monthlyData.value, monthlyMetric.value));
const monthlyWeatherMapSeries = computed(() => aggregateMap(monthlyData.value, weatherMetric.value));

// 月度统计信息
const monthlyStats = computed(() => {
  const metric = monthlyMetric.value;
  const values = monthlyData.value
    .map(row => {
      // 尝试多种可能的字段名
      const val = row[metric] ||
                  row[`${metric}_mean`] ||
                  (metric === 'aqi' ? (row[metric] || row['aqi_mean']) : 0);
      return Number(val);
    })
    .filter(v => !isNaN(v) && v !== 0); // 过滤掉0值，因为0可能是缺失值

  if (values.length === 0) {
    console.warn(`月度数据中未找到指标 ${metric} 的有效值，数据示例:`,
      monthlyData.value.slice(0, 3));
  }

  return {
    count: values.length,
    avg: values.length ? values.reduce((a, b) => a + b) / values.length : 0,
    max: values.length ? Math.max(...values) : 0,
    min: values.length ? Math.min(...values) : 0
  };
});

const monthlyAvgValue = computed(() => monthlyStats.value.avg);
const monthlyMaxValue = computed(() => monthlyStats.value.max);
const monthlyMinValue = computed(() => monthlyStats.value.min);

// 月度雷达图数据
const monthlyRadarData = computed(() => {
  const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const averages = {};

  pollutants.forEach(pollutant => {
    const values = monthlyData.value
      .map(row => Number(row[pollutant]))
      .filter(v => !isNaN(v));
    averages[pollutant] = values.length ? values.reduce((a, b) => a + b) / values.length : 0;
  });

  return {
    indicators: pollutants.map(p => ({
      name: p.toUpperCase(),
      max: Math.max(100, averages[p] * 1.5)
    })),
    values: pollutants.map(p => averages[p])
  };
});

// 事件处理
async function handleMonthlyYearChange() {
  await loadCurrentMonthlyData();
}

async function handleMonthChange() {
  await loadCurrentMonthlyData();
}

// 加载月度数据
async function loadCurrentMonthlyData() {
  try {
    const data = await loadMonthlyData(selectedYear.value, selectedMonth.value);
    monthlyData.value = data || [];
  } catch (error) {
    console.error("加载月度数据失败:", error);
    monthlyData.value = [];
  }
}

// 路由切换时加载数据
watch(() => route.name, async (newName) => {
  if (newName === "monthly") {
    await loadCurrentMonthlyData();
  }
});

// 初始化时如果是月度页面则加载数据
onMounted(async () => {
  if (route.name === "monthly") {
    await loadCurrentMonthlyData();
  }
});


// 月度分析计算属性
const monthlyLevelStats = computed(() =>
  classifyLevels(monthlyData.value, monthlyMetric.value)
);

const monthlyRadialVector = computed(() =>
  computeRadialVector(monthlyData.value)
);

// 月度趋势数据（假设有跨月数据）
const monthlyTrendSeries = computed(() => {
  // 这里需要根据实际数据结构调整
  if (!multiYearMonthlyData.value.length) return [];
  return multiYearMonthlyData.value.map(item => ({
    date: item.period,
    value: item.avgValue || 0
  }));
});

const monthlyTrendDates = computed(() =>
  monthlyTrendSeries.value.map(item => item.date)
);

const monthlyCorrMatrix = computed(() =>
  computeCorrMatrix(
    [{ data: monthlyData.value }], // 包装成与allDays相同的结构
    ["pm25", "pm10", "so2", "no2", "o3"],
    ["temp", "rh", "psfc"]
  )
);

const monthlyAQIRanking = computed(() =>
  computeAQIRanking(monthlyData.value, "province", 15)
);

const monthlyParallelRows = computed(() =>
  buildParallelData(monthlyData.value, "province", 30)
);

const monthlyCityValues = computed(() => {
  if (!selectedRegion.value && !monthlyData.value.length) return {};
  const target = normalizeProvince(selectedRegion.value);
  const row = monthlyData.value.find(r =>
    normalizeProvince(r.city) === target ||
    normalizeProvince(r.province) === target
  ) || monthlyData.value[0] || {};

  return {
    pm25: row.pm25,
    pm10: row.pm10,
    so2: row.so2,
    no2: row.no2,
    co: row.co,
    o3: row.o3
  };
});

const monthlyCityStats = computed(() =>
  computeCityMonthStats([{ data: monthlyData.value }], selectedRegion.value, parseInt(selectedMonth.value))
);

const monthlyTypeRibbon = computed(() =>
  computeCityTypeTrajectory([{ data: monthlyData.value }], selectedRegion.value, parseInt(selectedMonth.value))
);

// 多年度月度数据（需要根据实际数据源调整）
const multiYearMonthlyData = ref([]);
const monthlyPollutantShares = computed(() => {
  const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const totals = {};
  let total = 0;

  pollutants.forEach(p => {
    const values = monthlyData.value
      .map(row => Number(row[p]))
      .filter(v => !isNaN(v) && v > 0);
    totals[p] = values.length ? values.reduce((a, b) => a + b) / values.length : 0;
    total += totals[p];
  });

  return pollutants.map(p => ({
    name: p.toUpperCase(),
    value: total > 0 ? (totals[p] / total) * 100 : 0
  }));
});

// 加载多年度数据
async function loadMultiYearMonthlyData() {
  const years = ["2013", "2014", "2015"];
  const allData = [];

  for (const year of years) {
    try {
      const data = await loadMonthlyData(year, selectedMonth.value);
      if (data && data.length) {
        const avgValue = data.reduce((sum, row) => {
          const val = Number(row[monthlyMetric.value]);
          return sum + (isNaN(val) ? 0 : val);
        }, 0) / data.length;

        allData.push({
          year,
          period: `${year}-${selectedMonth.value}`,
          avgValue
        });
      }
    } catch (error) {
      console.warn(`加载${year}年数据失败:`, error);
    }
  }

  multiYearMonthlyData.value = allData;
}

</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
  color: #16202d;
  background: #fefdfb;
}

:root {
  --card: rgba(255, 255, 255, 0.92);
  --card-border: rgba(18, 24, 40, 0.08);
  --muted: #617083;
  --primary: #2f7e57;
  --primary-strong: #25684a;
  --accent: #e0952c;
  --surface: #fefdfb;
}

.bg {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.bg-layer {
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 15% 25%, rgba(255, 200, 128, 0.25), transparent 40%),
    radial-gradient(circle at 80% 20%, rgba(130, 196, 170, 0.25), transparent 45%),
    radial-gradient(circle at 50% 80%, rgba(80, 142, 212, 0.2), transparent 35%),
    linear-gradient(180deg, #fdf8f3, #f1f5f9);
  filter: blur(12px);
  opacity: 0.95;
}

.page {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  padding: 20px;
  gap: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(249, 252, 255, 0.92));
  color: #0f172a;
  backdrop-filter: blur(10px);
  box-shadow: 0 18px 40px rgba(22, 30, 45, 0.08);
  border: 1px solid rgba(18, 24, 40, 0.05);
  border-radius: 18px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h1 {
  margin: 0;
  font-size: 22px;
  letter-spacing: 0.2px;
}

.subtitle {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.1px;
}

.title-block {
  display: flex;
  flex-direction: column;
}

.controls-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.view-controls {
  display: flex;
  justify-content: flex-end;
}

.view-toggle {
  display: inline-flex;
  gap: 4px;
  background: rgba(47, 126, 87, 0.08);
  padding: 4px;
  border-radius: 10px;
  border: 1px solid rgba(47, 126, 87, 0.16);
}

.view-toggle button {
  background: transparent;
  color: var(--muted);
  border: none;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
}

.view-toggle button.active {
  color: #0f172a;
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  box-shadow: 0 6px 14px rgba(47, 126, 87, 0.18);
}

.tabs {
  display: inline-flex;
  gap: 10px;
  padding: 6px;
  background: rgba(47, 126, 87, 0.08);
  border-radius: 12px;
  border: 1px solid rgba(47, 126, 87, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.tabs a {
  color: var(--muted);
  text-decoration: none;
  padding: 7px 14px;
  border-radius: 10px;
  transition: all 0.2s ease;
}

.tabs a.active {
  color: #0b1220;
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  box-shadow: 0 8px 20px rgba(47, 126, 87, 0.18);
}

.layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.secondary {
  grid-template-columns: 1fr 1fr;
}

.single {
  grid-template-columns: 1fr;
}

.tertiary {
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
}

.pane {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 14px;
  padding: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8), 0 14px 24px rgba(79, 114, 143, 0.12);
  min-height: 0;
}

.map-pane {
  display: flex;
  flex-direction: column;
}

.side-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.map-switch {
  display: inline-flex;
  gap: 8px;
  margin-bottom: 8px;
  background: rgba(47, 126, 87, 0.08);
  padding: 4px;
  border-radius: 10px;
  border: 1px solid rgba(47, 126, 87, 0.16);
  align-self: flex-start;
  align-items: center;
  flex-wrap: wrap;
}

.map-switch button {
  background: transparent;
  color: #1f2937;
  border: none;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.map-switch button.active {
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  color: #0f172a;
  box-shadow: 0 8px 16px rgba(47, 126, 87, 0.2);
}

.weather-toggle {
  display: inline-flex;
  gap: 6px;
  margin-left: 8px;
}

.weather-toggle button {
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid rgba(47, 126, 87, 0.2);
  color: #1f2937;
  padding: 4px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.weather-toggle button.active {
  background: rgba(47, 126, 87, 0.15);
  border-color: rgba(47, 126, 87, 0.4);
  color: #0f172a;
}

.parallel-actions {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 8px;
}

.parallel-actions button {
  background: rgba(47, 126, 87, 0.08);
  border: 1px solid rgba(47, 126, 87, 0.2);
  color: #1f2937;
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.parallel-actions button:hover {
  border-color: var(--primary);
  color: #0b1220;
  background: rgba(47, 126, 87, 0.18);
}

.mt {
  margin-top: 6px;
}

.layout.tertiary {
  grid-template-columns: repeat(4, 1fr);
}

.placeholder-pane {
  display: flex;
  align-items: center;
  justify-content: center;
}
.wind-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.06), rgba(130, 196, 170, 0.06));
  border: 1px solid rgba(15, 23, 42, 0.06);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 16px rgba(15, 23, 42, 0.05);
}
.summary-row .label {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.1px;
}
.summary-row .value {
  font-weight: 700;
  color: #0f172a;
  font-size: 16px;
}
.note {
  margin: 0;
  font-size: 12px;
  color: #5b6b7b;
}

.muted {
  color: var(--muted);
}

.story-hero {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.story-visual {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(18, 24, 40, 0.08);
  box-shadow: 0 16px 40px rgba(18, 24, 40, 0.12);
}

.story-visual .chart,
.story-visual .pane {
  height: 100%;
}

.story-overlay {
  position: absolute;
  left: 14px;
  bottom: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(18, 24, 40, 0.08);
}

.story-glow {
  position: absolute;
  inset: 0;
  filter: blur(30px);
  opacity: 0.8;
  pointer-events: none;
}

.story-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(18, 24, 40, 0.08);
  color: #1f2937;
  border: 1px solid rgba(18, 24, 40, 0.12);
}

.story-chip.alt {
  background: rgba(47, 126, 87, 0.12);
  border-color: rgba(47, 126, 87, 0.3);
  color: #14532d;
}

.story-date {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.2px;
}

.story-mood {
  font-size: 13px;
  font-weight: 600;
}

.story-progress {
  width: 100%;
  height: 6px;
  background: rgba(18, 24, 40, 0.08);
  border-radius: 999px;
  overflow: hidden;
  border: 1px solid rgba(18, 24, 40, 0.06);
}

.story-progress-bar {
  height: 100%;
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  border-radius: 999px;
  transition: width 0.3s ease;
}

.story-side {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.story-side-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.story-note {
  font-size: 12px;
  color: var(--muted);
}

.section-heading {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin: 4px 4px 8px;
}

.section-badge {
  background: linear-gradient(120deg, #2f7e57, #8bbf5f);
  color: #0f172a;
  padding: 6px 12px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 12px;
  box-shadow: 0 6px 16px rgba(47, 126, 87, 0.2);
}

.section-meta {
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0.1px;
}

@media (max-width: 960px) {
  .layout,
  .tertiary {
    grid-template-columns: 1fr;
  }
  .controls-block {
    align-items: flex-start;
  }
  .page {
    padding: 14px;
  }
  .story-hero {
    grid-template-columns: 1fr;
  }
}

.monthly-controls {
  display: flex;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: var(--card);
  border-radius: 8px;
  border: 1px solid var(--card-border);
}

.time-selector, .metric-selector {
  display: flex;
  align-items: center;
  gap: 10px;
}

.time-selector label, .metric-selector label {
  font-weight: 600;
  color: var(--muted);
}

.time-selector select, .metric-selector select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: white;
}

.stats-panel {
  padding: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-label {
  color: var(--muted);
}

.stat-value {
  font-weight: 600;
  color: var(--primary);
}

.monthly-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin: 20px 0;
}

.monthly-card {
  background: var(--card);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-top: 15px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.chart-container {
  width: 100%;
  height: 300px;
  margin: 15px 0;
}

</style>
