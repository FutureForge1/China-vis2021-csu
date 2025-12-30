<template>
  <div class="month-view">
    <!-- 月份视图标题 -->
    <div class="section-heading">
      <div class="section-badge">月份视图</div>
      <div class="section-meta">月均数据 · 年度趋势 · 空间分布</div>
    </div>

    <!-- 第一行：地图和月度统计 -->
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
          :data="monthMapSeries"
          :metric="metric"
          :title="`月均地图：${metric}`"
          :selected-name="selectedRegion"
          :show-value="true"  
          @select="handleMapSelect"
        />
        
        <MapPanel
          v-else-if="mapMode === 'weather'"
          :data="weatherMapSeries"
          :metric="weatherMetricLabel"
          :title="`气象：${weatherMetricLabel}`"
          mode="weather"
          :selected-name="selectedRegion"
          :show-value="true"
          @select="handleMapSelect"
        />
        <TypeMap v-else :items="typeMapData" />
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

    <!-- 第二行：箱线图和月度堆叠 -->
    <section class="layout secondary">
      <div class="pane">
        <MonthlyBoxPlot
          :data="monthlyBoxData"
          :metric="metric"
          :title="`${metric.toUpperCase()} 月度波动范围`"
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

    <!-- 第三行：城市分析 -->
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
          :dates="monthCityTypeRibbon.dates"
          :series="monthCityTypeRibbon.series"
          :type-order="monthCityTypeRibbon.typeOrder"
          :province="selectedRegion"
        />
      </div>
    </section>

    <!-- 第四行：排名和环形图 -->
    <section class="layout secondary">
      <div class="pane">
        <AQIRanking :items="monthAQIRanking" @select="handleRankingSelect" />
      </div>
      <div class="pane">
        <MonthlyRing :items="monthlyRings" />
      </div>
    </section>

    <!-- 第五行：风向和对比 -->
    <section class="layout tertiary">
      <div class="pane">
        <WindCompass :data="monthWindRose" />
      </div>
      <div class="pane">
        <AQICompareLine :days="monthAQICompare.days" :series="monthAQICompare.series" :mode="'monthly'" />
      </div>
      <div class="pane">
        <!-- 预留位置，可以添加其他月度对比图表 -->
        <div class="placeholder-pane">
          <div class="placeholder-content">
            <h4>月度对比</h4>
            <p>可添加年际对比或其他分析</p>
          </div>
        </div>
      </div>
      <div class="pane">
        <!-- 预留位置 -->
        <div class="placeholder-pane">
          <div class="placeholder-content">
            <h4>扩展图表</h4>
            <p>预留位置用于未来扩展</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import MapPanel from "./MapPanel.vue";
import ControlPanel from "./ControlPanel.vue";
import TrendLine from "./TrendLine.vue";
import LevelBar from "./LevelBar.vue";
import RadialPollutant from "./RadialPollutant.vue";
import SeasonalLevelStack from "./SeasonalLevelStack.vue";
import AQIRanking from "./AQIRanking.vue";
import MonthlyRing from "./MonthlyRing.vue";
import WindCompass from "./WindCompass.vue";
import CityStackedPie from "./CityStackedPie.vue";
import CityTypeRibbon from "./CityTypeRibbon.vue";
import TypeMap from "./TypeMap.vue";
import MonthlyBoxPlot from "./MonthlyBoxPlot.vue";
import AQICompareLine from "./AQICompareLine.vue";
import {
  classifyLevels,
  computeRadialVector,
  computeTrendSeries,
  computeLevelTimeline,
  loadRegionIndex,
  rowsToScatter,
  attachAQI,
  computeAQIRanking,
  computeTypeByRegion,
  computeTypeTimeline,
  computeYearlyRadial,
  computeWindRose,
  computeMonthlyRing,
  computeCityMonthStats,
  computeCityTypeTrajectory,
  loadDataByGranularity,
  getAvailableDatesByGranularity,
  computeTrendSeriesByGranularity,
  computeLevelTimelineByGranularity,
  computeMonthlyBoxData,
  loadOneMonth,
  normalizeProvince
} from "../utils/dataLoader";

// Props
const props = defineProps({
  currentYear: {
    type: String,
    default: "2013"
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
  }
});

// Emits
const emit = defineEmits(['update:region', 'select-month']);

// 响应式数据
const mapMode = ref("pollution");
const weatherMetric = ref("wind");
const regionIndex = ref(null);
// const monthlyData = ref([]);
const currentMonth = ref(1);
const monthlyAggregatedData = ref([]); // 存 12 个月的 _monthly.json 数据
const currentMonthDailyData = ref([]); // 存当前选中月份的 30 天日数据 (用于箱线图、堆叠图)
const isMonthDetailLoading = ref(false); // 详情加载状态

// 计算属性
const selectedCity = computed(() => props.selectedRegion || "");

// 月份地图数据
const monthMapSeries = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];

  // 使用 Map 进行聚合计算
  const sums = new Map();
  const counts = new Map();

  for (const row of monthEntry.data) {
    const prov = normalizeProvince(row.province); // 归一化省名
    // 读取预计算的月均值
    const val = Number(row[`${props.metric}_mean`] ?? 0);
    
    if (!prov || Number.isNaN(val)) continue;
    
    sums.set(prov, (sums.get(prov) || 0) + val);
    counts.set(prov, (counts.get(prov) || 0) + 1);
  }

  // 生成聚合后的省级数据
  return Array.from(sums.entries()).map(([prov, sum]) => ({
    name: prov,
    // 保留1位小数
    value: Number((sum / (counts.get(prov) || 1)).toFixed(1))
  }));
});

// 气象地图数据
// 修改 weatherMapSeries
const weatherMapSeries = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];
  
  const sums = new Map();
  const counts = new Map();
  for (const row of monthEntry.data) {
    const prov = normalizeProvince(row.province);
    const val = Number(row[`${weatherMetric.value}_mean`] ?? 0);
    if (!prov || Number.isNaN(val)) continue;
    sums.set(prov, (sums.get(prov) || 0) + val);
    counts.set(prov, (counts.get(prov) || 0) + 1);
  }
  return Array.from(sums.entries()).map(([prov, sum]) => ({
    name: prov,
    value: sum / (counts.get(prov) || 1),
  }));
});

const weatherMetricLabel = computed(() => {
  const map = { wind: "风速", temp: "气温", rh: "湿度", psfc: "气压" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

// 类型地图数据
// 修改 typeMapData
const typeMapData = computed(() => {
  // 找到当前选中月份
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];
  
  // 使用工具函数计算类型
  return computeTypeByRegion(monthEntry.data, "province").map((item) => ({
    ...item,
    name: normalizeProvince(item.name),
    type: item.type || "未知",
    primary: item.primary || "-",
  }));
});

// 月度统计数据
// 修改 monthLevelStats
const monthLevelStats = computed(() => {
  return classifyLevels(currentMonthDailyData.value, props.metric);
});

// 4. 雷达图 (RadialPollutant) -> 使用当前选中月的聚合数据 (表示该月的平均污染构成)
const monthRadialVector = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  const data = monthEntry ? monthEntry.data : [];
  return computeRadialVector(data);
});

// 5. 趋势线 (TrendLine) -> 使用全年聚合数据
const monthTrendSeries = computed(() => {
  return computeTrendSeriesByGranularity(monthlyAggregatedData.value, props.metric, "month");
});

const monthTrendDates = computed(() => {
  return monthlyAggregatedData.value.map(entry => entry.date);
});

// 6. 箱线图 (MonthlyBoxPlot) -> 使用全年聚合数据 (展示12个月的波动)
const monthlyBoxData = computed(() => {
  // dataLoader 会自动处理 _mean 后缀
  return computeMonthlyBoxData(monthlyAggregatedData.value, props.metric);
});

// 7. 季节性堆叠图 (SeasonalLevelStack) -> 使用全年聚合数据 (展示12个月的等级构成趋势)
const monthlyLevelTimeline = computed(() => {
  return computeLevelTimelineByGranularity(monthlyAggregatedData.value, props.metric, "month");
});

// 8. 城市详情 (CityStackedPie) -> 使用聚合数据 (响应快)
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

// 9. 城市统计 (CityStackedPie Tooltip) -> 使用日详情数据 (为了计算 min/max)
const monthCityStats = computed(() => {
  return computeCityMonthStats(currentMonthDailyData.value, selectedCity.value, currentMonth.value);
});

// 10. 城市类型演变 (CityTypeRibbon) -> 使用日详情数据 (展示该月每天的变化)
const monthCityTypeRibbon = computed(() => {
  return computeCityTypeTrajectory(currentMonthDailyData.value, props.selectedRegion || null, currentMonth.value);
});

// 11. 排名 (AQIRanking) -> 使用当前选中月的聚合数据
const monthAQIRanking = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  const data = monthEntry ? monthEntry.data : [];
  return computeAQIRanking(data, "province", 15);
});

// 12. 环形图 (MonthlyRing) -> 使用全年聚合数据
const monthlyRings = computed(() => {
  return computeMonthlyRing(monthlyAggregatedData.value);
});

// 13. 风向玫瑰 (WindCompass) -> 使用日详情数据 (聚合数据只有u/v均值，无法画出分布)
const monthWindRose = computed(() => {
  return computeWindRose(currentMonthDailyData.value);
});

// 14. AQI对比 (AQICompareLine) -> 使用全年聚合数据
const monthAQICompare = computed(() => {
  const currentYearData = monthlyAggregatedData.value.map(entry => {
    // 计算该月全国均值
    if (entry.data && entry.data.length > 0) {
      const sum = entry.data.reduce((acc, r) => acc + (Number(r[`${props.metric}_mean`]) || 0), 0);
      return sum / entry.data.length;
    }
    return 0;
  });

  return {
    days: monthlyAggregatedData.value.map(m => `${m.month}月`),
    series: [{ name: props.currentYear, data: currentYearData }]
  };
});



// 事件处理
function handleMapSelect(name) {
  emit('update:region', name);
}

function handleRankingSelect(name) {
  emit('update:region', name);
}


// 初始化数据
// 1. 初始化：并发加载 12 个月的聚合文件 (极快)
async function loadMonthlyAggregatedData() {
  console.log(`[MonthView] 开始加载 ${props.currentYear} 全年聚合数据...`);
  
  // 构造 12 个月的标识符，例如 ["2013-01", "2013-02", ...]
  const months = Array.from({ length: 12 }, (_, i) => {
    return `${props.currentYear}-${String(i + 1).padStart(2, '0')}`;
  });

  // 并发请求
  const promises = months.map(m => loadOneMonth(m));
  const results = await Promise.all(promises);

  // 整理数据结构
  monthlyAggregatedData.value = results.map((data, index) => ({
    date: months[index],        // "2013-01"
    month: index + 1,           // 1
    data: data || []            // 这是一个数组，包含该月374个城市的统计对象
  }));
  
  console.log("[MonthView] 全年聚合数据加载完成");
  
  // 初始化完成后，默认加载第一个月(或当前选中的月)的详情
  await loadMonthDetail(currentMonth.value);
}

// 2. 按需加载：选中某个月时，去加载那一天的日数据
async function loadMonthDetail(monthNum) {
  isMonthDetailLoading.value = true;
  currentMonthDailyData.value = []; // 清空上一月数据，避免图表闪烁混淆

  const year = props.currentYear;
  const monthStr = String(monthNum).padStart(2, '0');
  
  // 你的目录结构是 /data/2013/01/01/20130101.json
  // 我们需要计算该月有多少天，然后并发加载
  const daysInMonth = new Date(year, monthNum, 0).getDate(); // 获取当月天数
  const promises = [];

  for (let d = 1; d <= daysInMonth; d++) {
    const dayPadded = String(d).padStart(2, '0');
    // 使用 dataLoader 里的 loadOneDay 或者直接 fetch
    // 这里复用 loadDataByGranularity("day", ...) 即可
    const dateStr = `${year}-${monthStr}-${dayPadded}`;
    promises.push(loadDataByGranularity("day", year, dateStr));
  }

  // 并发加载该月所有天
  const results = await Promise.allSettled(promises);
  
  // 收集成功的数据
  const allRows = [];
  results.forEach(res => {
    if (res.status === 'fulfilled' && res.value && res.value.length) {
      allRows.push(...res.value);
    }
  });

  currentMonthDailyData.value = allRows;
  isMonthDetailLoading.value = false;
  console.log(`[MonthView] ${monthNum}月 详情数据加载完成，共 ${allRows.length} 条记录`);
}

// 监听月份切换
function handleMonthSelect(month) {
  // 将 "2013-05" 这种格式转为数字 5，或者直接传数字
  // SeasonalLevelStack 传回来可能是 "2013-05"
  const m = typeof month === 'string' ? parseInt(month.split('-')[1]) : month;
  
  if (currentMonth.value !== m) {
    currentMonth.value = m;
    loadMonthDetail(m);
    emit('select-month', m);
  }
}

// 监听年份变化
watch(() => props.currentYear, () => {
  loadMonthlyAggregatedData(); // 使用新的函数名
}, { immediate: true });

// 监听指标变化
watch(() => props.metric, () => {
  // 重新计算相关数据
});


</script>

<style scoped>
.month-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
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

.mt {
  margin-top: 6px;
}

.placeholder-pane {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
}

.placeholder-content {
  text-align: center;
  color: var(--muted);
}

.placeholder-content h4 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
}

.placeholder-content p {
  margin: 0;
  font-size: 12px;
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
}
</style>
