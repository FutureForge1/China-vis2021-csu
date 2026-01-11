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
            <RouterLink to="/overview" :class="{ active: isOverview }"
              >概览</RouterLink
            >
            <RouterLink to="/story" :class="{ active: isStory }"
              >感知</RouterLink
            >
            <RouterLink to="/types" :class="{ active: isTypes }"
              >类型分析</RouterLink
            >
            <RouterLink to="/trends" :class="{ active: isTrends }"
              >趋势对比</RouterLink
            >
            <RouterLink to="/monthly" :class="{ active: isMonthly }"
              >月度分析补充</RouterLink
            >
            <RouterLink to="/forecast" :class="{ active: isForecast }"
              >预测实验</RouterLink
            >
          </nav>
          <!-- <div class="view-controls">
            <div class="view-toggle">
              <button :class="{ active: viewMode === 'daily' }" @click="viewMode = 'daily'">日均视图</button>
              <button :class="{ active: viewMode === 'monthly' }" @click="viewMode = 'monthly'">月份视图</button>
              <button :class="{ active: viewMode === 'yearly' }" @click="viewMode = 'yearly'">年度视图</button>
            </div>
          </div> -->
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
        <!-- 日均视图 (Content of Overview Page) -->
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
                <button
                  :class="{ active: mapMode === 'pollution' }"
                  @click="mapMode = 'pollution'"
                >
                  污染
                </button>
                <button
                  :class="{ active: mapMode === 'weather' }"
                  @click="mapMode = 'weather'"
                >
                  气象
                </button>
                <button
                  :class="{ active: mapMode === 'type' }"
                  @click="mapMode = 'type'"
                >
                  类型
                </button>
                <div v-if="mapMode === 'weather'" class="weather-toggle">
                  <button
                    :class="{ active: weatherMetric === 'wind' }"
                    @click="weatherMetric = 'wind'"
                  >
                    风速
                  </button>
                  <button
                    :class="{ active: weatherMetric === 'temp' }"
                    @click="weatherMetric = 'temp'"
                  >
                    气温
                  </button>
                  <button
                    :class="{ active: weatherMetric === 'rh' }"
                    @click="weatherMetric = 'rh'"
                  >
                    湿度
                  </button>
                  <button
                    :class="{ active: weatherMetric === 'psfc' }"
                    @click="weatherMetric = 'psfc'"
                  >
                    气压
                  </button>
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
              <TypeMap
                v-else
                :items="typeMapData"
                :selected-name="selectedRegion"
              />
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
              <ParallelAQI
                :rows="parallelRows"
                @select="handleParallelSelect"
              />
              <div class="parallel-actions">
                <span
                  >当前维度：{{
                    parallelLevel === "province"
                      ? "省均值"
                      : `城市（${parallelProvince || "未选"}`
                  }}
                </span>
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
            <!-- <div class="pane">
              <ProvinceDimensionChart
                v-if="viewMode === 'daily'"
                :data="tsneScatter"
                :selected-name="selectedRegion"
              />
            </div> -->
          </section>

          <!-- 城市污染日历 -->
          <section class="layout single">
            <div class="pane">
              <CityPollutionCalendar />
            </div>
          </section>
        </template>

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

        <template v-else-if="viewMode === 'yearly'">
          <SectionHeading
            badge="年度视图"
            meta="年均数据 · 跨年对比 · 长期趋势"
          />
          <ControlPanel
            class="pane"
            :date="currentYear"
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
              <MapPanel
                v-if="
                  mapMode === 'pollution' ||
                  (mapMode === 'weather' && metric !== 'wind')
                "
                :data="mapSeries"
                :metric="metric"
                :title="`${currentYear}年 ${metric.toUpperCase()} 年均分布`"
                :selected-name="selectedRegion"
                :scatter="scatterPoints"
                @select="handleMapSelect"
              />
              <MapPanel
                v-else-if="mapMode === 'weather' && metric === 'wind'"
                :data="mapSeries"
                :metric="metric"
                :title="`${currentYear}年 WIND 年均向量`"
                :selected-name="selectedRegion"
                mode="weather"
                :wind="yearViewWindVectors"
                @select="handleMapSelect"
              />
            </div>
            <div class="pane side-pane">
              <div class="stats-panel">
                <h3>年度统计 - {{ selectedRegion || "全国" }}</h3>
                <div class="stat-item">
                  <span class="stat-label">年份：</span>
                  <span class="stat-value">{{ currentYear }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label"
                    >{{ metric.toUpperCase() }} 年均值：</span
                  >
                  <span class="stat-value">{{
                    (
                      dayData.reduce(
                        (s, r) =>
                          s +
                          Number(r[`${metric}_yearly_mean`] || r[metric] || 0),
                        0
                      ) / (dayData.length || 1)
                    ).toFixed(2)
                  }}</span>
                </div>
                <div class="stat-item" v-if="selectedRegion">
                  <button @click="selectedRegion = ''">重置为全国视图</button>
                </div>
              </div>
              <RadialPollutant class="mt" :data="radialVector" />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <h3>月度污染物分布 - {{ selectedRegion || "全国" }}</h3>
              <MonthlyRing :items="yearMonthlyRingData" />
            </div>
            <div class="pane">
              <h3>AQI 等级晴雨图 (月度)</h3>
              <AQIRain :matrix="yearAQIRainData" :subtitle="currentYear" />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <h3>年度城市排名 - {{ selectedRegion || "全国" }}</h3>
              <AQIRanking :items="aqiRanking" @select="handleRankingSelect" />
            </div>
            <div class="pane">
              <h3>年度平行坐标 - {{ selectedRegion || "全国" }}</h3>
              <ParallelAQI
                :rows="parallelRows"
                @select="handleParallelSelect"
              />
            </div>
          </section>

          <section class="layout secondary">
            <div class="pane">
              <h3>省份污染特征降维分析</h3>
              <ProvinceDimensionChart
                v-if="dayData.length > 0"
                :data="dayData"
                :metric="metric"
                :selected-province="selectedRegion"
                :selected-year="currentYear"
                @province-select="handleMapSelect"
              />
            </div>
            <div class="pane">
              <h3>聚类分析说明</h3>
              <div class="cluster-info">
                <div v-if="selectedRegion" class="cluster-details">
                  <h4>当前选中：{{ selectedRegion }}</h4>
                  <div class="cluster-stats">
                    <div class="stat">
                      <span class="label">污染特征：</span>
                      <span class="value">{{
                        selectedClusterInfo?.clusterType || "低污染区域"
                      }}</span>
                    </div>
                    <div class="stat">
                      <span class="label">主要污染物：</span>
                      <span class="value">{{
                        selectedClusterInfo?.primaryPollutant || "PM2.5"
                      }}</span>
                    </div>
                    <div class="stat">
                      <span class="label">相似省份：</span>
                      <div class="similar-provinces">
                        <span
                          v-for="province in selectedClusterInfo?.similarProvinces ||
                          []"
                          :key="province"
                          class="province-tag"
                          @click="handleMapSelect(province)"
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

          <section class="layout single">
            <div class="pane">
              <CityPollutionCalendar
                :year="currentYear"
                :province="selectedRegion"
                :city="selectedRegion"
                :auto-load="true"
              />
            </div>
          </section>
        </template>
      </template>

      <!-- 月份视图 (Supplement Page) -->
      <template v-else-if="isMonthly">
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

      <template v-else-if="isStory">
        <SectionHeading
          badge="IMMERSION MODE"
          meta="AUTO-ADVANCE // VISUAL PRIORITY"
        />
        <ControlPanel
          class="pane"
          :date="storyDate"
          :region="selectedRegion || 'NATIONAL'"
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
              :style="{
                background: `radial-gradient(circle at 30% 30%, ${storyMood.color}33, transparent 50%)`,
              }"
            ></div>
            <MapPanel
              :data="storyMapSeries"
              :metric="metric"
              :title="`TIME FLOW · ${storyDate || 'LOADING'}`"
              :scatter="storyScatter"
              :selected-name="selectedRegion"
              @select="handleMapSelect"
            />
            <div class="story-overlay">
              <div class="story-chip">IMMERSION MODE // AUTO-PLAY</div>
              <div class="story-date">{{ storyDate || "…" }}</div>
              <div class="story-mood" :style="{ color: storyMood.color }">
                {{ storyMood.label }}
              </div>
              <div class="story-progress">
                <div
                  class="story-progress-bar"
                  :style="{ width: `${storyProgress}%` }"
                ></div>
              </div>
            </div>
          </div>
          <div class="story-side pane">
            <div class="story-side-header">
              <span class="story-chip alt">POLLUTION RHYTHM</span>
              <div class="story-note">
                AUTO-ADVANCE // COLOR & DENSITY GRADIENTS
              </div>
            </div>
            <RadialPollutant :data="storyRadial" />
          </div>
        </section>
      </template>

      <template v-else-if="isForecast">
        <ForecastPage />
      </template>

      <template v-else-if="isTypes">
        <SectionHeading
          badge="TYPE ANALYSIS"
          meta="TYPE MAP // CLUSTER SCATTER // TYPE EVOLUTION"
        />

        <ControlPanel
          class="pane"
          :date="currentDate"
          :region="selectedRegion || 'NATIONAL'"
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
      </template>

      <template v-else-if="isTrends">
        <SectionHeading
          badge="趋势对比"
          meta="跨年雷达 · 月均 · 晴雨图 · 趋势"
        />
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
            <TrendLine
              :metric="metric"
              :series="trendSeries"
              :dates="trendDates"
            />
          </div>
        </section>

        <!--        &lt;!&ndash; 在月度分析模板的合适位置添加 &ndash;&gt;-->
        <!--        <section class="layout single"> &lt;!&ndash; 改为 single 布局 &ndash;&gt;-->
        <!--          <div class="pane">-->
        <!--            <h3>污染物力引导布局分析</h3>-->
        <!--            <div class="chart-description">-->
        <!--              <p>通过力引导布局可视化展示各省份在不同污染物维度上的分布特征</p>-->
        <!--            </div>-->

        <!--            <ProvinceForceLayoutChart-->
        <!--              :data="monthlyData"-->
        <!--              :metric="monthlyMetric"-->
        <!--              :selected-province="selectedRegion"-->
        <!--              :selected-year="selectedYear"-->
        <!--              :selected-month="selectedMonth"-->
        <!--              @province-select="handleMapSelect"-->
        <!--              v-if="monthlyData.length > 0"-->
        <!--            />-->
        <!--          </div>-->
        <!--        </section>-->
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
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import AQIRain from "./components/AQIRain.vue";
import AQIRanking from "./components/AQIRanking.vue";
import CityPollutionCalendar from "./components/CityPollutionCalendar.vue";
import CityStackedPie from "./components/CityStackedPie.vue";
import CityTypeRibbon from "./components/CityTypeRibbon.vue";
import ControlPanel from "./components/ControlPanel.vue";
import CorrHeatmap from "./components/CorrHeatmap.vue";
import ForecastPage from "./components/ForecastPage.vue";
import IcicleChart from "./components/IcicleChart.vue";
import LevelBar from "./components/LevelBar.vue";
import MapPanel from "./components/MapPanel.vue";
import MonthlyRing from "./components/MonthlyRing.vue";
import MonthView from "./components/MonthView.vue";
import MultiYearRing from "./components/MultiYearRing.vue";
import ParallelAQI from "./components/ParallelAQI.vue";
import ProvinceDimensionChart from "./components/ProvinceDimensionChart.vue";
import ProvinceRadarChart from "./components/ProvinceRadarChart.vue";
import RadialPollutant from "./components/RadialPollutant.vue";
import SeasonalLevelStack from "./components/SeasonalLevelStack.vue";
import SectionHeading from "./components/SectionHeading.vue";
import TimeControls from "./components/TimeControls.vue";
import TrendLine from "./components/TrendLine.vue";
import TypeMap from "./components/TypeMap.vue";
import TypeScatter from "./components/TypeScatter.vue";
import YearControls from "./components/YearControls.vue";

import {
  buildFeatureScatterTSNE,
  buildMonthlyWindVectors,
  buildParallelData,
  buildTypeScatter,
  buildWindFlow,
  buildWindVectors,
  classifyLevels,
  computeAQICompareLines,
  computeAQIMonthly,
  computeAQIRain,
  computeAQIRanking,
  computeCityMonthStats,
  computeCityTypeTrajectory,
  computeCorrMatrix,
  computeLevelTimelineByGranularity,
  computeMonthlyRing,
  computeMonthlyRingGrid,
  computeMonthlyRingMonthly,
  computeRadialVector,
  computeTrendSeriesByGranularity,
  computeTypeByRegion,
  computeTypeTimeline,
  computeWindRose,
  computeYearlyRadial,
  getAvailableDatesByGranularity,
  gridToScatter,
  loadAvailableYears,
  loadDataByGranularity,
  loadGridData,
  loadOneMonth,
  loadRegionIndex,
  normalizeProvince,
  rowsToScatter,
} from "./utils/dataLoader";

const granularity = ref("day");
const metric = ref("pm25");
const availableDates = ref([]);
const currentDate = ref("");
const dayData = ref([]);
const allDays = ref([]);
const allMonthsData = ref([]); // Store all months data for trends
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
const allYearsData = ref([]); // 专门存储所有年份的数据，用于跨年对比
const yearMonthlyRingData = ref([]);
const yearAQIRainData = ref({ years: [], levels: [], data: [] });

// Moved state variables to top to avoid ReferenceError
const mapMode = ref("pollution"); // pollution | weather | type
const selectedRegion = ref("");
const parallelLevel = ref("province");
const parallelProvince = ref(null);

const isOverview = computed(() => route.name === "overview");
const isStory = computed(() => route.name === "story");
const isTypes = computed(() => route.name === "types");
const isTrends = computed(() => route.name === "trends");
const isMonthly = computed(() => route.name === "monthly");
const isYearly = computed(() => route.name === "yearly");
const isForecast = computed(() => route.name === "forecast");

// Update viewMode based on route
watch(
  () => route.name,
  (name) => {
    if (name === "overview") viewMode.value = "daily";
    // Don't force viewMode on other routes to avoid conflicts
  },
  { immediate: true }
);

// Load Monthly Data for Yearly View (lazy loaded when entering yearly view)
watch(
  () => [
    isYearly.value || viewMode.value === "yearly",
    currentYear.value,
    selectedRegion.value,
  ],
  async ([isY, year, region]) => {
    if (isY && year) {
      try {
        const months = Array.from(
          { length: 12 },
          (_, i) => `${year}-${String(i + 1).padStart(2, "0")}`
        );
        // Optimize: verify if we already have this year's month data in allMonthsData
        // But for simplicity and reactivity, we reload or reuse logic
        const promises = months.map((m) => loadOneMonth(m));
        const results = await Promise.all(promises);

        let aggregated = results.map((data, index) => ({
          date: months[index],
          month: index + 1,
          data: data || [],
        }));

        // Linkage: Filter by selectedRegion if present
        if (region) {
          aggregated = aggregated.map((item) => ({
            ...item,
            data: item.data.filter((d) => d.province === region),
          }));
        }

        yearMonthlyRingData.value = computeMonthlyRingMonthly(aggregated);

        // Compute AQI Rain for Year
        const rainLevels = ["优", "良", "轻度", "中度", "重度", "严重"];
        const monthNames = [
          "Jan",
          "Feb",
          "Mar",
          "Apr",
          "May",
          "Jun",
          "Jul",
          "Aug",
          "Sep",
          "Oct",
          "Nov",
          "Dec",
        ];
        const rainData = [];

        aggregated.forEach((aggMonth, mIndex) => {
          const counts = new Map(rainLevels.map((l) => [l, 0]));
          for (const cityRow of aggMonth.data) {
            const { aqi } = computeAQIMonthly(cityRow);
            let level = "严重";
            if (aqi <= 50) level = "优";
            else if (aqi <= 100) level = "良";
            else if (aqi <= 150) level = "轻度";
            else if (aqi <= 200) level = "中度";
            else if (aqi <= 300) level = "重度";

            counts.set(level, (counts.get(level) || 0) + 1);
          }
          rainLevels.forEach((l, lIndex) => {
            rainData.push([lIndex, mIndex, counts.get(l)]);
          });
        });

        yearAQIRainData.value = {
          years: monthNames,
          levels: rainLevels,
          data: rainData,
        };
      } catch (e) {
        console.error(e);
      }
    }
  }
);

function aggregateMap(rows, metricName, granularity = "day") {
  console.log(
    `[DataDebug] 聚合地图数据: metricName=${metricName}, granularity=${granularity}, rows.length=${rows.length}`
  );
  const sums = new Map();
  const counts = new Map();

  // 同时聚合省份和城市数据，以便在下钻时显示城市数据
  for (const row of rows) {
    let val = 0;
    if (metricName === "wind") {
      // Calculate wind speed
      const uField =
        granularity === "day"
          ? "u"
          : granularity === "month"
          ? "u_mean"
          : "u_yearly_mean";
      const vField =
        granularity === "day"
          ? "v"
          : granularity === "month"
          ? "v_mean"
          : "v_yearly_mean";
      const u = Number(row[uField] ?? 0);
      const v = Number(row[vField] ?? 0);
      val = Math.sqrt(u * u + v * v);
    } else {
      // 使用新的字段适配逻辑
      const actualField =
        granularity === "day"
          ? metricName
          : granularity === "month"
          ? `${metricName}_mean`
          : granularity === "year"
          ? `${metricName}_yearly_mean`
          : metricName;
      val = Number(row[actualField] ?? 0);
    }

    if (Number.isNaN(val)) continue;

    // 1. 聚合省份
    const prov = normalizeProvince(row.province);
    if (prov) {
      sums.set(prov, (sums.get(prov) || 0) + val);
      counts.set(prov, (counts.get(prov) || 0) + 1);
    }

    // 2. 聚合城市 (如果存在)
    // 注意：这里假设 row.city 是标准名称，或者 MapPanel 能匹配到
    if (row.city) {
      sums.set(row.city, (sums.get(row.city) || 0) + val);
      counts.set(row.city, (counts.get(row.city) || 0) + 1);
    }
  }

  const result = Array.from(sums.entries()).map(([name, sum]) => ({
    name: name,
    value: sum / (counts.get(name) || 1),
  }));

  console.log(`[DataDebug] 聚合结果(前10):`, result.slice(0, 10));
  return result;
}

const yearViewWindVectors = computed(() => {
  // If map mode is weather, compute vectors from yearly data
  if (isYearly.value && mapMode.value === "weather") {
    if (!regionIndex.value) return [];

    // Reuse buildMonthlyWindVectors but pass yearly data
    // yearly data keys: u_yearly_mean, v_yearly_mean
    // buildMonthlyWindVectors checks: u_mean ?? u.
    // We need to map them or update buildMonthlyWindVectors.
    // However, dataLoader's buildMonthlyWindVectors logic is:
    // const u = Number(row.u_mean ?? row.u);
    // So we need to map yearly keys to u_mean/v_mean or just create a new computed array

    // Map yearly keys to standard keys for the function
    const mappedData = dayData.value.map((r) => ({
      ...r,
      city: r.city || r.province, // yearly data might have province/city
      u_mean: r.u_yearly_mean,
      v_mean: r.v_yearly_mean,
    }));

    return buildMonthlyWindVectors(mappedData, regionIndex.value, 0.15);
  }
  return [];
});

const mapSeries = computed(() =>
  aggregateMap(dayData.value, metric.value, granularity.value)
);

const levelStats = computed(() => classifyLevels(dayData.value, metric.value));

const radialVector = computed(() => {
  let data = dayData.value;
  if (selectedRegion.value) {
    data = data.filter((d) => d.province === selectedRegion.value);
  }
  return computeRadialVector(data);
});

const trendSeries = computed(() => {
  const filterData = (dataArray) => {
    if (!selectedRegion.value) return dataArray;
    return dataArray.map((item) => ({
      ...item,
      data: item.data.filter((d) => d.province === selectedRegion.value),
    }));
  };

  // 如果是年度视图，或者当前粒度是年
  if (isYearly.value || granularity.value === "year") {
    return computeTrendSeriesByGranularity(
      filterData(allYearsData.value),
      metric.value,
      "year"
    );
  }
  // 如果是月度
  if (granularity.value === "month") {
    return computeTrendSeriesByGranularity(
      filterData(allMonthsData.value),
      metric.value,
      "month"
    );
  }
  return computeTrendSeriesByGranularity(
    filterData(allDays.value),
    metric.value,
    granularity.value
  );
});

const trendDates = computed(() => {
  if (isYearly.value || granularity.value === "year") {
    return allYearsData.value.map((item) => item.date);
  }
  if (granularity.value === "month") {
    return allMonthsData.value.map((item) => item.date);
  }
  return allDays.value.map((item) => item.date);
});

const levelTimeline = computed(() =>
  computeLevelTimelineByGranularity(
    allDays.value,
    metric.value,
    granularity.value
  )
);

const corrMatrix = computed(() =>
  computeCorrMatrix(
    allDays.value,
    ["pm25", "pm10", "so2", "no2", "o3"],
    ["temp", "rh", "psfc"]
  )
);

const aqiRanking = computed(() => {
  if (selectedRegion.value) {
    const provinceData = dayData.value.filter(
      (d) => d.province === selectedRegion.value
    );
    if (provinceData.length > 0) {
      return computeAQIRanking(provinceData, "city", 15);
    }
  }
  return computeAQIRanking(dayData.value, "province", 15);
});
const ringGrid = computed(() =>
  computeMonthlyRingGrid(
    allDays.value,
    metric.value,
    aqiRanking.value.map((i) => i.name),
    12
  )
);
const currentMonth = computed(() =>
  Number((currentDate.value || "2013-01-01").split("-")[1])
);
const selectedCity = computed(() => selectedRegion.value || "");
const cityMonthStats = computed(() =>
  computeCityMonthStats(allDays.value, selectedCity.value, currentMonth.value)
);
const cityDayValues = computed(() => {
  console.log(
    `[DataDebug] 计算城市日均值: selectedCity=${selectedCity.value}, granularity=${granularity.value}, data.length=${dayData.value.length}`
  );
  // Allow empty selectedValue to default to first entry or handle upstream
  if (!selectedCity.value && !dayData.value.length) return {};

  const target = normalizeProvince(selectedCity.value) || ""; // Don't auto-pick a city if none selected

  if (!target) {
    // Return National Average if no city is selected
    const metrics = ["pm25", "pm10", "so2", "no2", "co", "o3"];
    const agg = {};
    metrics.forEach((m) => {
      const sum = dayData.value.reduce(
        (acc, r) => acc + (Number(r[m]) || 0),
        0
      );
      agg[m] = dayData.value.length
        ? (sum / dayData.value.length).toFixed(1)
        : 0;
    });
    return agg;
  }

  const row =
    dayData.value.find(
      (r) =>
        normalizeProvince(r.city) === target ||
        normalizeProvince(r.province) === target
    ) || {};

  console.log(`[DataDebug] 找到的目标行:`, row);

  // 根据粒度获取正确的字段
  const getFieldValue = (field) => {
    // 数据已经在 loadDataForCurrentGranularity 中标准化，直接读取即可
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
  computeCityTypeTrajectory(
    allDays.value,
    selectedRegion.value || null,
    // Fix: If granularity is month, ignore currentMonth filter to show full trend
    granularity.value === "month" ? null : currentMonth.value,
    granularity.value
  )
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
const typeTimeline = computed(() =>
  computeTypeTimeline(allDays.value, "city", selectedRegion.value || null)
);

const weatherMetric = ref("wind");
const weatherMapSeries = computed(() =>
  aggregateMap(dayData.value, weatherMetric.value, granularity.value)
);
const weatherMetricLabel = computed(() => {
  const map = { wind: "风速", temp: "气温", rh: "湿度", psfc: "气压" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

const scatterPoints = computed(() => {
  // 如果有网格数据，优先使用网格数据进行渲染
  if (gridData.value && gridData.value.length > 0) {
    const targetMetric =
      mapMode.value === "weather" ? weatherMetric.value : metric.value;
    // 如果是风速模式，通常不画散点，画箭头；但如果想看风速点也可以保留
    if (mapMode.value === "weather" && weatherMetric.value === "wind")
      return [];
    return gridToScatter(gridData.value, targetMetric);
  }

  // 降级回退到城市数据 (旧逻辑)
  if (!regionIndex.value) return [];
  if (mapMode.value === "weather" && weatherMetric.value === "wind") return [];

  const targetMetric =
    mapMode.value === "weather" ? weatherMetric.value : metric.value;
  // 根据粒度获取正确的字段
  let actualField = targetMetric;
  if (granularity.value === "month") actualField = `${targetMetric}_mean`;
  else if (granularity.value === "year")
    actualField = `${targetMetric}_yearly_mean`;

  return rowsToScatter(dayData.value, actualField, regionIndex.value);
});

// 风场箭头 (Wind Vectors)
const windVectors = computed(() => {
  if (mapMode.value === "weather" && weatherMetric.value === "wind") {
    // 优先使用网格数据
    const source =
      gridData.value && gridData.value.length > 0
        ? gridData.value
        : dayData.value;
    const index =
      gridData.value && gridData.value.length > 0 ? null : regionIndex.value; // 网格数据不需要 index

    if (granularity.value === "month" && !gridData.value.length) {
      // 月度数据使用专门的向量构建函数 (读取 u_mean, v_mean)
      return buildMonthlyWindVectors(source, index, 0.15);
    }

    return buildWindVectors(source, index, 0.1);
  }
  return [];
});

// 风场流线 (Wind Flow)
const windFlow = computed(() => {
  if (mapMode.value === "weather" && weatherMetric.value === "wind") {
    // 优先使用网格数据
    const source =
      gridData.value && gridData.value.length > 0
        ? gridData.value
        : dayData.value;
    const index =
      gridData.value && gridData.value.length > 0 ? null : regionIndex.value;
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
      return gridToScatter(gridData.value, metric.value).map((p) => [
        p.coord[0],
        p.coord[1],
        p.value,
      ]);
    }

    // 回退旧逻辑
    if (regionIndex.value) {
      // 根据粒度获取正确的字段
      let actualField = metric.value;
      if (granularity.value === "month") actualField = `${metric.value}_mean`;
      else if (granularity.value === "year")
        actualField = `${metric.value}_yearly_mean`;

      return rowsToScatter(dayData.value, actualField, regionIndex.value).map(
        (d) => [d.coord[0], d.coord[1], d.value]
      );
    }
  }
  return [];
});

const filterByRegion = (arr) => {
  if (!selectedRegion.value) return arr;
  return arr.map((item) => ({
    ...item,
    data: item.data.filter((d) => d.province === selectedRegion.value),
  }));
};

const yearlyRings = computed(() => {
  // 如果在年度视图或趋势视图，优先使用 allYearsData
  if (allYearsData.value.length > 0) {
    return computeYearlyRadial(filterByRegion(allYearsData.value));
  }
  return computeYearlyRadial(filterByRegion(allDays.value));
});
const monthlyRings = computed(() => {
  if (
    (granularity.value === "month" || granularity.value === "year") &&
    allMonthsData.value.length > 0
  ) {
    // If we are in monthly/yearly mode, use the loaded monthly data to show the annual cycle
    return computeMonthlyRingMonthly(filterByRegion(allMonthsData.value));
  }
  return computeMonthlyRing(filterByRegion(allDays.value));
});
const aqiRain = computed(() => {
  if (
    (granularity.value === "month" || granularity.value === "year") &&
    allMonthsData.value.length > 0
  ) {
    return computeAQIRain(filterByRegion(allMonthsData.value), 1);
  }
  return computeAQIRain(filterByRegion(allDays.value), 1);
});
const aqiCompare = computed(() => computeAQICompareLines(allDays.value));

const tsneScatter = computed(() =>
  buildFeatureScatterTSNE(dayData.value, "city")
);
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

const storyIndex = ref(0);
const storyRunning = ref(true);
let storyTimer = null;

const storyDate = computed(() => allDays.value[storyIndex.value]?.date || "");
const storyDayData = computed(
  () => allDays.value[storyIndex.value]?.data || []
);
const storyMapSeries = computed(() =>
  aggregateMap(storyDayData.value, metric.value)
);
const storyScatter = computed(() =>
  regionIndex.value
    ? rowsToScatter(
        storyDayData.value,
        mapMode.value === "weather" ? weatherMetric.value : metric.value,
        regionIndex.value
      )
    : []
);
const storyProgress = computed(() =>
  allDays.value.length
    ? Math.round(
        (storyIndex.value / Math.max(allDays.value.length - 1, 1)) * 100
      )
    : 0
);
const storyRadial = computed(() => computeRadialVector(storyDayData.value));
const storyMood = computed(() => {
  const m = Number(storyDate.value.slice(5, 7) || 1);
  if ([12, 1, 2].includes(m))
    return { label: "冬季 · 污染高发", color: "#eab308" };
  if ([3, 4, 5].includes(m))
    return { label: "春季 · 回暖扩散", color: "#22c55e" };
  if ([6, 7, 8].includes(m))
    return { label: "夏季 · 相对清透", color: "#38bdf8" };
  return { label: "秋季 · 渐冷积聚", color: "#f97316" };
});

async function bootstrap() {
  // 初始化默认选中区域
  if (viewMode.value === "monthly") {
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

  // 【新增】初始化 monthViewYear，保持与 currentYear 同步
  // 这里很重要！确保 monthViewYear 在 MonthView 挂载前就有值
  monthViewYear.value = currentYear.value;
  console.log(
    `[App] Bootstrap: monthViewYear=${monthViewYear.value}, currentYear=${currentYear.value}`
  );

  // 【新增】预加载所有年份的数据 (用于趋势分析和年度对比)
  loadAllYearsData();

  // 加载当前年份的数据
  await loadDataForCurrentGranularity();

  regionIndex.value = await loadRegionIndex();

  startStoryLoop();
}

// 【新增】加载所有年份数据
async function loadAllYearsData() {
  const loaded = [];
  for (const year of availableYears.value) {
    try {
      let yearData = await loadDataByGranularity("year", year);
      if (yearData && yearData.length) {
        // 标准化字段
        yearData = yearData.map((row) => {
          const newRow = { ...row };
          const pollutants = [
            "pm25",
            "pm10",
            "so2",
            "no2",
            "co",
            "o3",
            "aqi",
            "u",
            "v",
          ];
          pollutants.forEach((p) => {
            const key = `${p}_yearly_mean`;
            if (newRow[key] !== undefined) {
              newRow[p] = newRow[key];
            }
          });
          return newRow;
        });
        loaded.push({ date: year, data: yearData });
      }
    } catch (e) {
      console.warn(`Failed to load yearly data for ${year}`, e);
    }
  }
  allYearsData.value = loaded;
}

// 加载当前粒度的数据
async function loadDataForCurrentGranularity() {
  try {
    // 获取当前粒度的可用日期
    const dates = await getAvailableDatesByGranularity(
      granularity.value,
      currentYear.value
    );
    availableDates.value = dates;

    // 设置默认日期：对于年粒度，直接使用年份；对于月/日粒度，使用第一个可用日期
    if (granularity.value === "year") {
      currentDate.value = currentYear.value;
    } else {
      if (!currentDate.value || !dates.includes(currentDate.value)) {
        currentDate.value = dates[0] || `${currentYear.value}-01-01`;
      }
    }

    // 加载当前日期的数据
    if (granularity.value === "day") {
      const data = await loadDataByGranularity(
        "day",
        currentYear.value,
        currentDate.value
      );
      dayData.value = data;

      // (2) 【新增】并发加载网格数据 (用于地图展示)
      // 注意：网格数据量大，加载可能稍慢
      console.log(`[App] Loading grid data for ${currentDate.value}...`);
      const grid = await loadGridData(currentDate.value);
      gridData.value = grid; // 保存网格数据

      // 预加载所有天的数据用于趋势线
      const loadedAll = [];
      for (const day of dates) {
        const dayData = await loadDataByGranularity(
          "day",
          currentYear.value,
          day
        );
        if (dayData.length) {
          loadedAll.push({ date: day, data: dayData });
        }
      }
      allDays.value = loadedAll;
    } else if (granularity.value === "month") {
      // Month Granularity: Load all months for the current year
      const dates = Array.from(
        { length: 12 },
        (_, i) => `${currentYear.value}-${String(i + 1).padStart(2, "0")}`
      );
      const loadedAll = [];
      const pollutants = [
        "pm25",
        "pm10",
        "so2",
        "no2",
        "co",
        "o3",
        "aqi",
        "u",
        "v",
        "temp",
        "rh",
        "psfc",
      ];

      for (const m of dates) {
        try {
          let mData = await loadDataByGranularity(
            "month",
            currentYear.value,
            m
          );
          if (mData && mData.length) {
            mData = mData.map((row) => {
              const newRow = { ...row };
              pollutants.forEach((p) => {
                const key = `${p}_mean`;
                if (newRow[key] !== undefined) newRow[p] = newRow[key];
              });
              return newRow;
            });
            loadedAll.push({ date: m, data: mData });
          }
        } catch (e) {
          console.warn("Failed to load month", m);
        }
      }
      allMonthsData.value = loadedAll;
      allDays.value = loadedAll;

      gridData.value = [];
      let data = await loadDataByGranularity(
        granularity.value,
        currentYear.value,
        currentDate.value
      );

      data = data.map((row) => {
        const newRow = { ...row };
        pollutants.forEach((p) => {
          const key = `${p}_mean`;
          if (newRow[key] !== undefined) newRow[p] = newRow[key];
        });
        return newRow;
      });
      dayData.value = data;
    } else {
      // Year Granularity
      gridData.value = [];
      let data = await loadDataByGranularity(
        granularity.value,
        currentYear.value,
        currentDate.value
      );

      const pollutants = [
        "pm25",
        "pm10",
        "so2",
        "no2",
        "co",
        "o3",
        "aqi",
        "u",
        "v",
        "temp",
        "rh",
        "psfc",
      ];

      data = data.map((row) => {
        const newRow = { ...row };
        pollutants.forEach((p) => {
          const key = `${p}_yearly_mean`;
          if (newRow[key] !== undefined) newRow[p] = newRow[key];
        });
        return newRow;
      });
      dayData.value = data;

      // [Feature Fix]: Load Monthly breakdown for the current year (for MonthlyRing/Detail view)
      const dates = Array.from(
        { length: 12 },
        (_, i) => `${currentYear.value}-${String(i + 1).padStart(2, "0")}`
      );
      const loadedMonths = [];
      for (const m of dates) {
        try {
          let mData = await loadDataByGranularity(
            "month",
            currentYear.value,
            m
          );
          if (mData && mData.length) {
            mData = mData.map((row) => {
              const newRow = { ...row };
              pollutants.forEach((p) => {
                const key = `${p}_mean`;
                if (newRow[key] !== undefined) newRow[p] = newRow[key];
              });
              return newRow;
            });
            loadedMonths.push({ date: m, data: mData });
          }
        } catch (e) {}
      }
      allMonthsData.value = loadedMonths;

      // Load All Years for Trend Analysis
      const loadedAll = [];
      for (const year of availableYears.value) {
        let yearData = await loadDataByGranularity("year", year);
        if (yearData && yearData.length) {
          yearData = yearData.map((row) => {
            const newRow = { ...row };
            pollutants.forEach((p) => {
              const key = `${p}_yearly_mean`;
              if (newRow[key] !== undefined) newRow[p] = newRow[key];
            });
            return newRow;
          });
          loadedAll.push({ date: year, data: yearData });
        }
      }
      allDays.value = loadedAll;
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
  if (viewMode.value === "daily" || viewMode.value === "yearly") {
    // 日均/年度视图模式：更新 currentYear 并重新加载数据
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

import { loadCityToProvinceMap } from "./utils/dataLoader";

async function handleMapSelect(name) {
  // 尝试将城市名转换为省份名
  const map = await loadCityToProvinceMap();
  const province =
    map.get(name) || map.get(name.replace(/市|地区|自治州|盟/g, ""));

  if (province) {
    console.log(`[MapSelect] Converted ${name} to ${province}`);
    selectedRegion.value = province;
  } else {
    selectedRegion.value = name;
  }

  // 添加聚类信息更新
  if (route.name === "monthly" && isMonthly.value) {
    updateClusterInfo(name);
  }
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

watch(viewMode, async (newMode) => {
  if (newMode === "daily") {
    granularity.value = "day";
  } else if (newMode === "monthly") {
    granularity.value = "month";
    // 切换到月视图时，同步 monthViewYear 和 currentYear
    monthViewYear.value = currentYear.value;
    monthViewMetric.value = metric.value;
  } else if (newMode === "yearly") {
    granularity.value = "year";
  }
  await loadDataForCurrentGranularity();
});

watch(
  () => route.name,
  (name) => {
    if (name === "story") {
      startStoryLoop();
    } else {
      stopStoryLoop();
    }

    // 当切换到 isMonthly 路由时，确保 monthViewYear 同步
    if (name === "monthly") {
      console.log(
        `[App] Switched to monthly route, monthViewYear=${monthViewYear.value}, currentYear=${currentYear.value}`
      );
      // 保持 monthViewYear，让 MonthView 组件自行加载数据
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
provide("setSelectedRegion", setSelectedRegion);

// 【新增】监听路由变化，实现视图状态隔离
watch(
  () => route.path,
  (newPath, oldPath) => {
    // 只要切换了顶层导航（路由），就重置选中区域
    if (newPath !== oldPath) {
      // 月视图默认长沙市，其他视图（包括日视图和类型分析视图）默认全国
      if (viewMode.value === "monthly") {
        selectedRegion.value = "长沙市";
      } else {
        selectedRegion.value = ""; // 日视图和类型分析视图都默认全国
      }
      console.log("视图切换，设置 selectedRegion:", selectedRegion.value);
    }
  }
);

watch(viewMode, () => {
  // 切换到月视图时，设置默认选中长沙市
  if (viewMode.value === "monthly") {
    selectedRegion.value = "长沙市";
  } else {
    selectedRegion.value = "";
  }
  console.log(
    "视图模式切换(日/月)，设置 selectedRegion:",
    selectedRegion.value
  );
});

watch(currentYear, (newYear) => {
  // 当 currentYear 改变时，同步 monthViewYear
  monthViewYear.value = newYear;
  console.log(`[App] currentYear changed to ${newYear}, monthViewYear synced`);
});

watch(metric, () => {
  // Metric change just reuses loaded data; computed props react automatically.
});

onMounted(() => {
  bootstrap();
});

import {
  computeAQIRankingMonthly,
  getAvailableMonths,
  getAvailableYears,
  loadMonthlyData,
} from "./utils/dataLoader";

// 月度选择相关
const selectedYear = ref("2013");
const selectedMonth = ref("01");
const monthlyMetric = ref("pm25");
const monthlyData = ref([]);
const monthlyAvailableYears = getAvailableYears();
const availableMonths = getAvailableMonths();

// 根据选中区域过滤月度数据
const filteredMonthlyData = computed(() => {
  if (!selectedRegion.value) {
    return monthlyData.value;
  }

  // 使用标准化省份名称进行匹配
  const target = normalizeProvince(selectedRegion.value);
  return monthlyData.value.filter((row) => {
    const province = normalizeProvince(row.province);
    const city = normalizeProvince(row.city);
    return province === target || city === target;
  });
});

// 计算属性 - 使用过滤后的数据
const currentMonthlyPeriod = computed(
  () => `${selectedYear.value}-${selectedMonth.value}`
);
const monthlyMapSeries = computed(() =>
  aggregateMap(filteredMonthlyData.value, monthlyMetric.value, "month")
);
const monthlyWeatherMapSeries = computed(() =>
  aggregateMap(filteredMonthlyData.value, weatherMetric.value, "month")
);

// 月度类型地图数据
const monthlyTypeMapData = computed(() =>
  computeTypeByRegion(filteredMonthlyData.value, "province", "month").map(
    (item) => ({
      ...item,
      name: normalizeProvince(item.name),
      type: item.type || "未知",
      primary: item.primary || "-",
    })
  )
);

// 月度统计信息 - 使用过滤后的数据
const monthlyStats = computed(() => {
  const metric = monthlyMetric.value;
  const values = filteredMonthlyData.value
    .map((row) => {
      // 尝试多种可能的字段名
      const val =
        row[metric] ||
        row[`${metric}_mean`] ||
        (metric === "aqi" ? row[metric] || row["aqi_mean"] : 0);
      return Number(val);
    })
    .filter((v) => !isNaN(v) && v !== 0);

  if (values.length === 0) {
    console.warn(
      `月度数据中未找到指标 ${metric} 的有效值，数据示例:`,
      filteredMonthlyData.value.slice(0, 3)
    );
  }

  return {
    count: values.length,
    avg: values.length ? values.reduce((a, b) => a + b) / values.length : 0,
    max: values.length ? Math.max(...values) : 0,
    min: values.length ? Math.min(...values) : 0,
  };
});

const monthlyAvgValue = computed(() => monthlyStats.value.avg);
const monthlyMaxValue = computed(() => monthlyStats.value.max);
const monthlyMinValue = computed(() => monthlyStats.value.min);

// 月度雷达图数据 - 使用过滤后的数据
const monthlyRadarData = computed(() => {
  const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const averages = {};

  pollutants.forEach((pollutant) => {
    const values = filteredMonthlyData.value
      .map((row) => {
        const val = row[pollutant] || row[`${pollutant}_mean`] || 0;
        return Number(val);
      })
      .filter((v) => !isNaN(v) && v > 0);
    averages[pollutant] = values.length
      ? values.reduce((a, b) => a + b) / values.length
      : 0;
  });

  return {
    indicators: pollutants.map((p) => ({
      name: p.toUpperCase(),
      max: Math.max(100, averages[p] * 1.5),
    })),
    values: pollutants.map((p) => averages[p]),
  };
});

// 其他月度分析计算属性 - 使用过滤后的数据
const monthlyLevelStats = computed(() =>
  classifyLevels(filteredMonthlyData.value, monthlyMetric.value)
);

const monthlyRadialVector = computed(() =>
  computeRadialVector(filteredMonthlyData.value)
);

const monthlyCorrMatrix = computed(() =>
  computeCorrMatrix(
    [{ data: filteredMonthlyData.value }],
    ["pm25", "pm10", "so2", "no2", "o3"],
    ["temp", "rh", "psfc"]
  )
);

const monthlyAQIRanking = computed(() =>
  computeAQIRankingMonthly(filteredMonthlyData.value, "city", 15)
);

const monthlyParallelRows = computed(() =>
  buildParallelData(filteredMonthlyData.value, "city", 30)
);

const monthlyCityValues = computed(() => {
  if (!selectedRegion.value && !filteredMonthlyData.value.length) return {};
  const target = normalizeProvince(selectedRegion.value);
  const row =
    filteredMonthlyData.value.find(
      (r) =>
        normalizeProvince(r.city) === target ||
        normalizeProvince(r.province) === target
    ) ||
    filteredMonthlyData.value[0] ||
    {};

  return {
    pm25: row.pm25,
    pm10: row.pm10,
    so2: row.so2,
    no2: row.no2,
    co: row.co,
    o3: row.o3,
  };
});

const monthlyCityStats = computed(() =>
  computeCityMonthStats(
    [{ data: filteredMonthlyData.value }],
    selectedRegion.value,
    parseInt(selectedMonth.value)
  )
);

const monthlyTypeRibbon = computed(() =>
  computeCityTypeTrajectory(
    [{ data: filteredMonthlyData.value }],
    selectedRegion.value,
    parseInt(selectedMonth.value)
  )
);

const monthlyPollutantShares = computed(() => {
  const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const totals = {};
  let total = 0;

  pollutants.forEach((p) => {
    const values = filteredMonthlyData.value
      .map((row) => Number(row[p]))
      .filter((v) => !isNaN(v) && v > 0);
    totals[p] = values.length
      ? values.reduce((a, b) => a + b) / values.length
      : 0;
    total += totals[p];
  });

  return pollutants.map((p) => ({
    name: p.toUpperCase(),
    value: total > 0 ? (totals[p] / total) * 100 : 0,
  }));
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

// 多年度月度数据（需要根据实际数据源调整）
const multiYearMonthlyData = ref([]);

// 加载多年度数据
async function loadMultiYearMonthlyData() {
  const years = ["2013", "2014", "2015"];
  const allData = [];

  for (const year of years) {
    try {
      const data = await loadMonthlyData(year, selectedMonth.value);
      if (data && data.length) {
        const avgValue =
          data.reduce((sum, row) => {
            const val = Number(row[monthlyMetric.value]);
            return sum + (isNaN(val) ? 0 : val);
          }, 0) / data.length;

        allData.push({
          year,
          period: `${year}-${selectedMonth.value}`,
          avgValue,
        });
      }
    } catch (error) {
      console.warn(`加载${year}年数据失败:`, error);
    }
  }

  multiYearMonthlyData.value = allData;
}

// 月度趋势数据（假设有跨月数据）
const monthlyTrendSeries = computed(() => {
  if (!multiYearMonthlyData.value.length) return [];
  return multiYearMonthlyData.value.map((item) => ({
    date: item.period,
    value: item.avgValue || 0,
  }));
});

const monthlyTrendDates = computed(() =>
  monthlyTrendSeries.value.map((item) => item.date)
);

// 路由切换时加载数据
watch(
  () => route.name,
  async (newName) => {
    if (newName === "monthly" || newName === "trends") {
      await loadCurrentMonthlyData();
    }
  }
);

// 初始化时如果是月度页面则加载数据
onMounted(async () => {
  if (route.name === "monthly" || route.name === "trends") {
    await loadCurrentMonthlyData();
  }
});

const nationalRange = computed(() => {
  if (!monthlyData.value.length) return { min: 0, max: 100 };

  const metric = monthlyMetric.value;
  const values = monthlyData.value
    .map((row) => {
      const val = row[metric] || row[`${metric}_mean`] || 0;
      return Number(val);
    })
    .filter((v) => !isNaN(v) && v > 0);

  if (values.length === 0) return { min: 0, max: 100 };

  return {
    min: Math.min(...values),
    max: Math.max(...values),
  };
});

// 创建固定范围的数据（保持全国范围，不随选中过滤）
const fixedRangeMapData = computed(() => {
  const nationalMin = nationalRange.value.min;
  const nationalMax = nationalRange.value.max;

  // 如果当前有选中区域，我们需要创建一个特殊的数据集
  if (selectedRegion.value && filteredMonthlyData.value.length > 0) {
    // 保持全国数据的范围，但只显示选中区域的数据
    const filteredData = filteredMonthlyData.value.map((item) => {
      // 计算该数据项在固定范围内的相对位置
      const value = Number(
        item[monthlyMetric.value] || item[`${monthlyMetric.value}_mean`] || 0
      );
      return {
        ...item,
        // 保持原始值，但颜色映射会使用固定范围
        value: value,
      };
    });

    return filteredData;
  }

  // 没有选中区域时，使用全国数据
  return monthlyData.value.map((item) => ({
    ...item,
    value: Number(
      item[monthlyMetric.value] || item[`${monthlyMetric.value}_mean`] || 0
    ),
  }));
});

// 降维分析相关状态
const selectedClusterInfo = ref(null);

// // 处理省份选择
// const handleMapSelect = (provinceName) => {
//   console.log("选中省份:", provinceName);
//   selectedRegion.value = provinceName;
//   updateClusterInfo(provinceName);
// };

// 修改updateClusterInfo函数，使用新的相似度计算
const updateClusterInfo = (provinceName) => {
  // 动态选择数据源：Trends模式用月度数据，Overview模式用年度数据(dayData)
  let data = monthlyData.value;
  if (!isTrends.value && dayData.value && dayData.value.length > 0) {
    data = dayData.value;
  }

  if (!provinceName || !data || !data.length) {
    selectedClusterInfo.value = null;
    return;
  }

  // 找到该省份的所有城市数据
  const provinceCities = data.filter((item) => item.province === provinceName);

  if (provinceCities.length === 0) {
    selectedClusterInfo.value = null;
    return;
  }

  // 计算省份平均污染物浓度
  const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
  const provinceAverages = {};

  pollutants.forEach((pollutant) => {
    const values = provinceCities
      .map((city) => city[pollutant] || city[`${pollutant}_mean`] || 0)
      .filter((val) => !isNaN(val) && val > 0);

    provinceAverages[pollutant] =
      values.length > 0 ? values.reduce((a, b) => a + b) / values.length : 0;
  });

  // 使用相对超标倍数判断主要污染物
  const pollutantStandards = {
    pm25: 35, // 24小时平均标准(μg/m³)
    pm10: 50,
    so2: 150,
    no2: 100,
    co: 4, // mg/m³
    o3: 160,
  };

  const pollutantScores = pollutants.map((pollutant) => ({
    name: pollutant,
    score: provinceAverages[pollutant] / pollutantStandards[pollutant],
    value: provinceAverages[pollutant],
  }));

  // 按超标倍数排序，取最严重的为主要污染物
  const primaryPollutant =
    pollutantScores.sort((a, b) => b.score - a.score)[0]?.name || "pm25";

  // 判断污染程度
  const totalScore = pollutantScores.reduce((sum, p) => sum + p.score, 0);
  let clusterType = "低污染区域";
  if (totalScore > 4) clusterType = "高污染区域";
  else if (totalScore > 2) clusterType = "中等污染区域";

  // 使用修复后的相似省份计算
  const similarProvinces = calculateSimilarProvinces(provinceName, data);

  selectedClusterInfo.value = {
    province: provinceName,
    clusterType,
    primaryPollutant: primaryPollutant.toUpperCase(),
    similarProvinces:
      similarProvinces.length > 0 ? similarProvinces : ["暂无相似省份数据"],
    pollutantLevels: pollutantScores,
  };
};

// 修改calculateSimilarProvinces函数
const calculateSimilarProvinces = (targetProvince, data, topN = 3) => {
  if (!targetProvince || !data.length) return [];

  // 先按省份聚合数据，避免重复
  const provinceMap = new Map();

  data.forEach((item) => {
    const province = item.province;
    if (!province) return;

    if (!provinceMap.has(province)) {
      provinceMap.set(province, []);
    }
    provinceMap.get(province).push(item);
  });

  // 计算每个省份的平均值
  const provinceAverages = new Map();
  provinceMap.forEach((cities, province) => {
    const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
    const averages = {};

    pollutants.forEach((pollutant) => {
      const values = cities
        .map((city) => city[pollutant] || city[`${pollutant}_mean`] || 0)
        .filter((val) => !isNaN(val) && val > 0);

      averages[pollutant] =
        values.length > 0 ? values.reduce((a, b) => a + b) / values.length : 0;
    });

    provinceAverages.set(province, averages);
  });

  const targetAverages = provinceAverages.get(targetProvince);
  if (!targetAverages) return [];

  // 标准化污染物数值（使用对数变换减少量级差异）
  const normalizeValue = (value, pollutant) => {
    if (value <= 0) return 0;
    // 不同污染物的基准值，用于标准化
    const baselines = {
      pm25: 75,
      pm10: 150,
      so2: 150,
      no2: 100,
      co: 4,
      o3: 160,
    };
    return Math.log1p(value / baselines[pollutant]);
  };

  const differences = Array.from(provinceAverages.entries())
    .filter(([province]) => province !== targetProvince)
    .map(([province, averages]) => {
      // 计算多维度欧氏距离（使用标准化值）
      const distance = Math.sqrt(
        Object.keys(targetAverages).reduce((sum, pollutant) => {
          const targetNorm = normalizeValue(
            targetAverages[pollutant],
            pollutant
          );
          const provinceNorm = normalizeValue(averages[pollutant], pollutant);
          const diff = targetNorm - provinceNorm;
          return sum + diff * diff;
        }, 0)
      );

      return {
        province,
        distance,
        similarity: 1 / (1 + distance),
      };
    })
    .sort((a, b) => a.distance - b.distance)
    .slice(0, topN);

  return differences.map((item) => item.province);
};

// 监听选中区域变化
watch(
  () => selectedRegion.value,
  (newRegion) => {
    if (newRegion) {
      updateClusterInfo(newRegion);
      // Linkage: Update Parallel Coordinates to show cities of the selected province
      parallelProvince.value = newRegion;
      parallelLevel.value = "city";
    } else {
      selectedClusterInfo.value = null;
      parallelProvince.value = null;
      parallelLevel.value = "province";
    }
  }
);

// 监听月度数据变化
watch(
  () => monthlyData.value,
  (newData) => {
    if (newData && newData.length > 0 && selectedRegion.value) {
      updateClusterInfo(selectedRegion.value);
    }
  }
);

// 计算可用省份列表
const availableProvinces = computed(() => {
  if (!monthlyData.value.length) return [];

  const provinces = new Set();
  monthlyData.value.forEach((item) => {
    if (item.province) provinces.add(item.province);
  });

  return Array.from(provinces).sort();
});
</script>

<style scoped>
:global(body) {
  margin: 0;
  font-family: "JetBrains Mono", monospace;
  color: #0a0a0a;
  background: #f5f5f5;
  overflow-x: hidden;
}

:root {
  --c-yellow: #ffe600;
  --c-black: #0a0a0a;
  --c-white: #ffffff;
  --c-light-gray: #e8e8e8;
  --c-gray: #888888;
  --c-bg: #f5f5f5;
  --c-card: rgba(255, 255, 255, 0.95);
  --c-border: rgba(0, 0, 0, 0.08);
  --c-accent: #ffe600;
  --font-mono: "JetBrains Mono", monospace;
  --font-display: "Oswald", sans-serif;
}

.bg {
  background: var(--c-bg);
  min-height: 100vh;
  color: var(--c-black);
  position: relative;
}

.bg-layer {
  position: fixed;
  inset: 0;
  background: none; /* disable rising grid overlay to avoid half-cover artifacts */
  pointer-events: none;
  z-index: 0;
}

.page {
  max-width: 1800px;
  margin: 0 auto;
  padding: 20px;
  position: relative;
  z-index: 1;
}

/* === Header === */
.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--c-border);
  margin-bottom: 20px;
  position: relative;
}

.topbar::after {
  content: "";
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100px;
  height: 3px;
  background: var(--c-yellow);
}

.title-block h1 {
  font-family: var(--font-display);
  font-size: 36px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin: 0;
  color: var(--c-black);
  line-height: 1;
}

.subtitle {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--c-yellow);
  margin-top: 5px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* === Controls === */
.controls-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-end;
}

.tabs {
  display: flex;
  gap: 2px;
  background: transparent;
  padding: 0;
  border: none;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tabs a {
  font-family: var(--font-display);
  font-size: 13px;
  text-transform: uppercase;
  color: var(--c-gray);
  text-decoration: none;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.02);
  border: 1px solid var(--c-border);
  transition: all 0.2s;
  clip-path: polygon(10px 0, 100% 0, 100% 100%, 0 100%, 0 10px);
  white-space: nowrap;
}

.tabs a:hover {
  color: var(--c-black);
  background: rgba(0, 0, 0, 0.05);
}

.tabs a.active {
  color: var(--c-black);
  background: var(--c-yellow);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(255, 230, 0, 0.2);
}

.view-controls {
  display: flex;
  gap: 15px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.view-toggle {
  display: flex;
  gap: 0;
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid var(--c-border);
  border-radius: 4px;
  overflow: hidden;
  padding: 2px;
}

.view-toggle button {
  font-family: var(--font-mono);
  font-size: 11px;
  background: transparent;
  border: none;
  color: var(--c-gray);
  padding: 6px 14px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.view-toggle button:hover {
  color: var(--c-black);
  background: rgba(0, 0, 0, 0.05);
}

.view-toggle button.active {
  background: var(--c-yellow);
  color: var(--c-black);
  font-weight: bold;
  box-shadow: 0 0 8px rgba(255, 230, 0, 0.4);
}

.granularity-indicator {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--c-yellow);
  margin-top: 2px;
  text-align: right;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* === Side Pane Items === */
.side-pane {
  display: flex;
  flex-direction: column;
  gap: 15px !important;
}

.side-item {
  flex: 1;
  min-height: 150px;
  overflow: hidden;
}

.side-item:first-child {
  min-height: 120px;
}

.side-item:nth-child(2) {
  min-height: 200px;
}

.side-item:nth-child(3) {
  min-height: 180px;
}

.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--c-gray);
  font-family: var(--font-mono);
  font-size: 12px;
  background: rgba(0, 0, 0, 0.02);
  border: 1px dashed var(--c-border);
}

/* === Layout === */
.layout {
  display: grid;
  grid-template-columns: 2.5fr 1.5fr;
  gap: 20px;
  margin-bottom: 20px;
}

.main-layout {
  height: 650px; /* Fixed height for the main dashboard area */
}

.secondary {
  grid-template-columns: 1fr 1fr;
}

.tertiary {
  grid-template-columns: repeat(4, 1fr);
}

.single {
  grid-template-columns: 1fr;
}

.pane {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  padding: 20px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.2s ease;
  min-height: auto;
  /* Industrial Corner Cut */
  clip-path: polygon(
    0 0,
    100% 0,
    100% calc(100% - 20px),
    calc(100% - 20px) 100%,
    0 100%
  );
}

.layout > .pane {
  min-height: 500px;
}

.secondary > .pane {
  min-height: 350px;
}

.pane:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.pane h3 {
  font-family: var(--font-display);
  font-size: 14px;
  text-transform: uppercase;
  margin: 0 0 15px 0;
  color: var(--c-black);
  letter-spacing: 0.5px;
}

.pane h4 {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--c-yellow);
  text-transform: uppercase;
  margin: 10px 0 8px 0;
  letter-spacing: 0.5px;
}

.map-pane {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.side-pane {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.side-pane::-webkit-scrollbar {
  width: 4px;
}

.side-pane::-webkit-scrollbar-thumb {
  background: var(--c-yellow);
  border-radius: 2px;
}

.side-pane::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.02);
}

.pane::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 20px;
  background: var(--c-yellow);
}

.pane h3 {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: var(--c-black);
  margin: 0 0 15px 0;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 10px;
}

.pane h3::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--c-border);
  margin-left: 10px;
}

/* === Map & Chart Overrides === */
.map-switch {
  margin-bottom: 15px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.map-switch button {
  background: rgba(0, 0, 0, 0.03);
  border: 1px solid var(--c-border);
  color: var(--c-gray);
  padding: 6px 14px;
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
  transition: all 0.2s;
  text-transform: uppercase;
  font-weight: 500;
  white-space: nowrap;
}

.map-switch button:hover {
  color: var(--c-black);
  background: rgba(0, 0, 0, 0.05);
}

.map-switch button.active {
  border-color: var(--c-yellow);
  background: var(--c-yellow);
  color: var(--c-black);
  font-weight: bold;
  box-shadow: 0 2px 6px rgba(255, 230, 0, 0.2);
}

.weather-toggle {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--c-border);
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.weather-toggle button {
  background: transparent;
  border: 1px solid var(--c-border);
  color: var(--c-gray);
  font-size: 11px;
  padding: 5px 10px;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.2s;
  text-transform: uppercase;
  font-family: var(--font-mono);
}

.weather-toggle button:hover {
  color: var(--c-yellow);
  border-color: var(--c-yellow);
}

.weather-toggle button.active {
  color: var(--c-yellow);
  border-color: var(--c-yellow);
  background: rgba(255, 230, 0, 0.05);
  font-weight: bold;
}

/* === Stats Panel === */
.stats-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stats-panel h3 {
  margin: 0 0 10px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--c-border);
  font-family: var(--font-display);
  font-size: 13px;
  text-transform: uppercase;
  color: var(--c-black);
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 230, 0, 0.02);
  border: 1px solid rgba(255, 230, 0, 0.1);
  border-left: 3px solid var(--c-yellow);
  border-radius: 3px;
  transition: all 0.2s;
}

.stat-item:hover {
  background: rgba(255, 230, 0, 0.05);
  box-shadow: 0 1px 3px rgba(255, 230, 0, 0.1);
}

.stat-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--c-gray);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: bold;
  color: var(--c-yellow);
  text-align: right;
}

.stat-item button {
  width: 100%;
  padding: 8px 12px;
  background: var(--c-yellow);
  border: none;
  color: var(--c-black);
  font-family: var(--font-mono);
  font-size: 11px;
  cursor: pointer;
  border-radius: 3px;
  font-weight: bold;
  transition: all 0.2s;
  text-transform: uppercase;
}

.stat-item button:hover {
  background: #ffd700;
  box-shadow: 0 2px 6px rgba(255, 230, 0, 0.3);
}

/* === Story Mode === */
.story-hero {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.story-visual {
  border: 1px solid var(--c-border);
  background: var(--c-card);
  position: relative;
}

.story-overlay {
  position: absolute;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--c-yellow);
  padding: 15px;
  min-width: 200px;
}

.story-date {
  font-family: var(--font-display);
  font-size: 32px;
  color: var(--c-black);
}

.story-mood {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--c-yellow);
  margin-bottom: 10px;
}

.story-progress {
  height: 2px;
  background: rgba(0, 0, 0, 0.1);
  width: 100%;
}

.story-progress-bar {
  height: 100%;
  background: var(--c-yellow);
}

/* === Section Headings === */
.section-heading {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
  padding-left: 5px;
}

.section-badge {
  background: var(--c-yellow);
  color: var(--c-black);
  font-family: var(--font-display);
  font-weight: 700;
  padding: 2px 8px;
  font-size: 14px;
  text-transform: uppercase;
}

.section-meta {
  font-size: 12px;
  color: var(--c-gray);
  font-family: var(--font-mono);
}

/* === Monthly Controls === */
.monthly-controls {
  display: flex;
  gap: 30px;
  margin-bottom: 20px;
  background: var(--c-card);
  padding: 15px;
  border: 1px solid var(--c-border);
  align-items: center;
  flex-wrap: wrap;
}

/* === Layout & Pane Styles (共享与MonthView) === */
.layout {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.layout.secondary {
  grid-template-columns: 1fr 1fr;
}

.layout.single {
  grid-template-columns: 1fr;
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

/* === Time Selector === */
.time-selector {
  display: flex;
  gap: 15px;
  align-items: center;
}

.metric-selector {
  display: flex;
  gap: 10px;
  align-items: center;
}

.monthly-controls select {
  background: #fff;
  border: 1px solid var(--c-border);
  color: #0a0a0a;
  padding: 5px 10px;
  font-family: var(--font-mono);
  font-size: 12px;
  cursor: pointer;
}

.monthly-controls select:hover {
  border-color: var(--c-yellow);
}
.monthly-controls select:hover {
  border-color: var(--c-yellow);
}

.monthly-controls label {
  color: var(--c-gray);
  font-size: 12px;
  white-space: nowrap;
}

/* === Utility === */
.mt {
  margin-top: 10px;
}
button {
  font-family: var(--font-mono);
}
.monthly-controls label {
  color: var(--c-gray);
  font-size: 12px;
  white-space: nowrap;
}

/* === Utility === */
.mt {
  margin-top: 10px;
}
button {
  font-family: var(--font-mono);
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

/* 聚类信息样式 */
.cluster-info {
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.cluster-details h4 {
  margin: 0 0 15px 0;
  color: #2f7e57;
  font-size: 16px;
  font-weight: 600;
  padding-bottom: 10px;
  border-bottom: 1px solid #eee;
}

.cluster-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 10px;
}

.stat {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.stat:last-child {
  border-bottom: none;
}

.stat .label {
  font-weight: 600;
  color: #666;
  min-width: 80px;
  font-size: 13px;
  flex-shrink: 0;
}

.stat .value {
  color: #333;
  font-size: 13px;
  flex-grow: 1;
}

.similar-provinces {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 5px;
}

.province-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  border: 1px solid #bbdefb;
  white-space: nowrap;
}

.no-selection {
  text-align: center;
  color: #666;
  padding: 40px 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.no-selection p {
  margin: 5px 0;
}

.hint {
  font-size: 12px;
  margin-top: 15px;
  line-height: 1.5;
  color: #999;
  max-width: 300px;
}

.radar-explanation {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.radar-explanation ul {
  margin: 10px 0;
  padding-left: 20px;
}

.radar-explanation li {
  margin-bottom: 5px;
}

.chart-description {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin-bottom: 15px;
  text-align: center;
}

.force-layout-explanation {
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.force-layout-explanation h4 {
  color: #2f7e57;
  margin: 15px 0 8px 0;
  font-size: 14px;
}

.force-layout-explanation ul {
  margin: 8px 0;
  padding-left: 20px;
}

.force-layout-explanation li {
  margin-bottom: 5px;
}

.force-layout-explanation .example {
  background: #e3f2fd;
  padding: 10px;
  border-radius: 6px;
  margin-top: 15px;
  border-left: 3px solid #4ecdc4;
}

.force-layout-explanation .example strong {
  color: #1976d2;
}

.force-layout-explanation .example p {
  margin: 5px 0 0 0;
  font-size: 12px;
}

#monthly-analysis-supplement {
  margin: 20px;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.icicle-explanation {
  margin-top: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #e0e0e0;
}

.icicle-explanation h4 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 14px;
  font-weight: 600;
}

.icicle-explanation ul {
  margin: 10px 0;
  padding-left: 20px;
}

.icicle-explanation li {
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.4;
  color: #34495e;
}

.icicle-explanation strong {
  color: #2c3e50;
}

.view-mode-info {
  margin-top: 15px;
  padding: 12px;
  background: #e8f4fd;
  border-radius: 4px;
  border-left: 4px solid #3498db;
}

.view-mode-info h5 {
  margin: 0 0 8px 0;
  color: #2980b9;
  font-size: 13px;
}

.view-mode-info p {
  margin: 5px 0;
  font-size: 12px;
  color: #2c3e50;
}
</style>
