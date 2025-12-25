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
          </nav>
          <TimeControls
            :granularity="granularity"
            :metric="metric"
            :date-options="availableDates"
            :current-date="currentDate"
            @update:granularity="granularity = $event"
            @update:metric="metric = $event"
            @update:date="handleDateChange"
          />
        </div>
      </header>

      <template v-if="isOverview">
        <ControlPanel
          class="pane"
          :date="currentDate"
          :region="selectedRegion || '全国'"
          :rows="dayData"
          :metric="metric"
          :map-mode="mapMode"
          @select-metric="metric = $event"
          @toggle-map-mode="mapMode = $event"
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
            <TypeMap v-else :items="typeMapData" />
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
            <AQIRanking :items="aqiRanking" @select="handleRankingSelect" />
          </div>
          <div class="pane">
            <ParallelAQI :rows="parallelRows" @select="handleParallelSelect" />
            <div class="parallel-actions">
              <span>当前维度：{{ parallelLevel === "province" ? "省均值" : `城市（${parallelProvince || "未选"}` }} </span>
              <button @click="resetParallel">重置到省</button>
            </div>
          </div>
        </section>
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
        <section class="layout secondary">
          <div class="pane map-pane">
            <TypeMap :items="typeMapData" />
          </div>
          <div class="pane">
            <TypeScatter :points="typeScatter" @select="handleTypeSelect" />
          </div>
        </section>

        <section class="layout secondary">
          <div class="pane">
            <TypeScatter :points="tsneScatter" @select="handleTypeSelect" />
          </div>
          <div class="pane">
            <TypeBump :dates="typeTimeline.dates" :series="typeTimeline.series" />
          </div>
        </section>

        <section class="layout secondary">
          <div class="pane">
            <WindCompass :data="windRose" />
          </div>
          <div class="pane wind-summary">
            <div class="summary-row">
              <div class="label">最强方向</div>
              <div class="value">{{ windSummary.maxDir }}</div>
            </div>
            <div class="summary-row">
              <div class="label">最强风速</div>
              <div class="value">{{ windSummary.maxVal }} m/s</div>
            </div>
            <div class="summary-row">
              <div class="label">平均风速</div>
              <div class="value">{{ windSummary.avg }} m/s</div>
            </div>
            <p class="muted note">基于当日 u / v 计算的 8 向均值</p>
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
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import TimeControls from "./components/TimeControls.vue";
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

function normalizeProvince(name) {
  if (!name) return "";
  let n = String(name).split("|").pop().trim();

  const direct = {
    北京: "北京市",
    天津: "天津市",
    上海: "上海市",
    重庆: "重庆市",
    "内蒙古自治区": "内蒙古自治区",
    内蒙古: "内蒙古自治区",
    "广西壮族自治区": "广西壮族自治区",
    广西: "广西壮族自治区",
    "新疆维吾尔自治区": "新疆维吾尔自治区",
    新疆: "新疆维吾尔自治区",
    "宁夏回族自治区": "宁夏回族自治区",
    宁夏: "宁夏回族自治区",
    "西藏自治区": "西藏自治区",
    西藏: "西藏自治区",
    "香港特别行政区": "香港特别行政区",
    香港: "香港特别行政区",
    "澳门特别行政区": "澳门特别行政区",
    澳门: "澳门特别行政区",
    "中国香港": "香港特别行政区",
    "中國香港": "香港特别行政区",
    "中国澳门": "澳门特别行政区",
    "中國澳門": "澳门特别行政区",
    "台湾省": "台湾省",
    台湾: "台湾省",
    "黑龙江省": "黑龙江省",
    "黑龍江省": "黑龙江省",
  };
  if (direct[n]) return direct[n];

  // Strip common suffixes, then append “省”
  n = n.replace(/省|市|自治区|壮族自治区|维吾尔自治区|回族自治区|特别行政区/g, "").trim();
  if (!n) return "";
  return `${n}省`;
}

function aggregateMap(rows, metricName) {
  const sums = new Map();
  const counts = new Map();
  for (const row of rows) {
    const prov = normalizeProvince(row.province);
    const val = Number(row[metricName] ?? 0);
    if (!prov || Number.isNaN(val)) continue;
    sums.set(prov, (sums.get(prov) || 0) + val);
    counts.set(prov, (counts.get(prov) || 0) + 1);
  }
  return Array.from(sums.entries()).map(([prov, sum]) => ({
    name: prov,
    value: sum / (counts.get(prov) || 1),
  }));
}

const mapSeries = computed(() => aggregateMap(dayData.value, metric.value));

const levelStats = computed(() =>
  classifyLevels(dayData.value, metric.value)
);

const radialVector = computed(() => computeRadialVector(dayData.value));

const trendSeries = computed(() =>
  computeTrendSeries(allDays.value, metric.value)
);

const trendDates = computed(() => allDays.value.map((item) => item.date));

const levelTimeline = computed(() =>
  computeLevelTimeline(allDays.value, metric.value)
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
const weatherMapSeries = computed(() => aggregateMap(dayData.value, weatherMetric.value));
const weatherMetricLabel = computed(() => {
  const map = { wind: "风速", temp: "气温", rh: "湿度", psfc: "气压" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

const scatterPoints = computed(() => {
  if (!regionIndex.value) return [];
  if (mapMode.value === "weather" && weatherMetric.value === "wind") return [];
  return rowsToScatter(
    dayData.value,
    mapMode.value === "weather" ? weatherMetric.value : metric.value,
    regionIndex.value
  );
});

const windVectors = computed(() =>
  regionIndex.value && mapMode.value === "weather" && weatherMetric.value === "wind"
    ? buildWindVectors(dayData.value, regionIndex.value, 0.3)
    : []
);
const windFlow = computed(() =>
  regionIndex.value && mapMode.value === "weather" && weatherMetric.value === "wind"
    ? buildWindFlow(dayData.value, regionIndex.value, 0.35, 4)
    : []
);

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
  const index = await loadIndex();
  availableDates.value = index.days;
  currentDate.value = index.days[0] || "2013-01-01";

  // Preload all days for the trend line if the index is present.
  const loadedAll = [];
  for (const day of index.days) {
    const data = await loadOneDay(day);
    if (data.length) {
      loadedAll.push({ date: day, data });
    }
  }
  allDays.value = loadedAll;

  const first = await loadOneDay(currentDate.value);
  dayData.value = first;

  regionIndex.value = await loadRegionIndex();

  startStoryLoop();
}

async function handleDateChange(value) {
  currentDate.value = value;
  const data = await loadOneDay(value);
  dayData.value = data;
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

watch(metric, () => {
  // Metric change just reuses loaded data; computed props react automatically.
});

onMounted(() => {
  bootstrap();
});
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
</style>
