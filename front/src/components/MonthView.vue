<template>
  <div class="month-view">
    <!-- 月份视图标题 -->
    <div class="section-heading">
      <div class="section-badge">月份视图</div>
      <div class="section-meta">月均数据 · 年度趋势 · 空间分布</div>
    </div>

    <div class="time-bar">
      <div class="year-selector">
        <label>年份：</label>
        <select :value="currentYear" @change="e => $emit('update:currentYear', e.target.value)">
          <option v-for="y in availableYears" :key="y" :value="y">{{ y }}年</option>
        </select>
      </div>
      <div class="month-selector">
        <label>月份：</label>
        <div class="month-chips">
          <button 
            v-for="m in 12" 
            :key="m" 
            :class="['month-chip', { active: m === currentMonth }]"
            @click="handleMonthSelect(m)"
          >
            {{ m }}月
          </button>
        </div>
      </div>
    </div>

    <!-- 第一行：地图和月度统计 -->
    <section class="layout">
      <div class="pane map-pane">
        <div class="map-switch">
          <div class="mode-group">
            <button :class="{ active: mapMode === 'pollution' }" @click="mapMode = 'pollution'">污染</button>
            <button :class="{ active: mapMode === 'weather' }" @click="mapMode = 'weather'">气象</button>
            <button :class="{ active: mapMode === 'type' }" @click="mapMode = 'type'">类型</button>
          </div>
          
          <div class="divider" v-if="mapMode !== 'type'"></div>

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
            <button :class="{ active: weatherMetric === 'wind' }" @click="weatherMetric = 'wind'">风速</button>
            <button :class="{ active: weatherMetric === 'temp' }" @click="weatherMetric = 'temp'">气温</button>
            <button :class="{ active: weatherMetric === 'rh' }" @click="weatherMetric = 'rh'">湿度</button>
            <button :class="{ active: weatherMetric === 'psfc' }" @click="weatherMetric = 'psfc'">气压</button>
          </div>
        </div>

        <MapPanel
          v-if="mapMode === 'pollution' && monthMapSeries.length > 0"
          :key="`pol-${currentYear}-${currentMonth}-${metric}`"
          :data="monthMapSeries"
          :metric="metric"
          :title="`月均分布：${metric}`"
          :selected-name="selectedRegion"
          :show-value="true"
          map-name="china_cities" 
          @select="handleMapSelect"
        />
        
        <MapPanel
          v-else-if="mapMode === 'weather' && (weatherMapSeries.length > 0 || monthWindVectors.length > 0)"
          :key="`wea-${currentYear}-${currentMonth}-${weatherMetric}`"
          :data="weatherMapSeries"
          :metric="weatherMetricLabel"
          :title="`气象分布：${weatherMetricLabel}`"
          mode="weather"
          :selected-name="selectedRegion"
          :wind="monthWindVectors" 
          :show-value="true"
          :map-name="currentMapName" 
          @select="handleMapSelect"
        />

        <div v-else-if="!isMonthDetailLoading && monthMapSeries.length === 0" class="placeholder-map">
          数据加载中或暂无数据...
        </div>
        
        <TypeMap
          v-else-if="mapMode === 'type' && typeMapData.length > 0"
          :key="`typ-${currentYear}-${currentMonth}`"
          :data="typeMapData"
          title="主导污染类型"
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
          v-if="monthCityTypeRibbon.dates && monthCityTypeRibbon.dates.length > 0"
          :dates="monthCityTypeRibbon.dates"
          :series="monthCityTypeRibbon.series"
          :type-order="monthCityTypeRibbon.typeOrder"
          :province="selectedRegion"
        />
        <div v-else class="placeholder-pane">
          <div class="placeholder-content">
            <h4>城市类型演变</h4>
            <p>暂无数据或数据加载中</p>
          </div>
        </div>
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
  buildWindVectors,
  loadRegionIndex,
  buildMonthlyWindVectors,
  rowsToScatter,
  attachAQI,
  computeAQIRanking,
  computeAQIRankingMonthly,
  computeTypeByRegion,
  computeTypeTimeline,
  computeYearlyRadial,
  computeWindRose,
  computeMonthlyRing,
  computeMonthlyRingMonthly,
  computeCityMonthStats,
  computeCityTypeTrajectory,
  loadDataByGranularity,
  getAvailableDatesByGranularity,
  computeTrendSeriesByGranularity,
  computeLevelTimelineByGranularity,
  computeMonthlyBoxData,
  loadOneMonth,
  normalizeProvince,
  loadCityMap,
  matchGeoName,
} from "../utils/dataLoader";

// 单独导入新添加的函数
import { computeRadialVectorByMonthly, computeMonthlyBoxDataForView } from "../utils/dataLoader";

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
  }
});

// Emits
const emit = defineEmits([
  "update:region", 
  "select-month", 
  "update:metric",      // <--- 关键：修复污染物切换无效
  "update:currentYear"  // <--- 关键：支持年份切换
]);

// 响应式数据
const mapMode = ref("pollution");
const weatherMetric = ref("wind");
const regionIndex = ref(null);
// const monthlyData = ref([]);
const currentMonth = ref(1);
const monthlyAggregatedData = ref([]); // 存 12 个月的 _monthly.json 数据
const currentMonthDailyData = ref([]); // 存当前选中月份的 30 天日数据 (用于箱线图、堆叠图)
const isMonthDetailLoading = ref(false); // 详情加载状态
// 【新增】存储 GeoJSON 中的所有标准城市名，用于匹配
const mapGeoNames = ref([]);
// 计算属性
const selectedCity = computed(() => props.selectedRegion || "");

// 修改为返回 { name: '地图标准名', value: 数值 } 格式
const monthMapSeries = computed(() => {
  // 如果地图标准名还没加载，暂时返回空
  if (mapGeoNames.value.length === 0) return [];

  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];

  const mapData = [];
  
  for (const row of monthEntry.data) {
    // 获取数据中的原始名称
    const rawName = row.city || row.province; 
    
    // 【核心】将数据名 映射到 地图名
    // 比如：数据 "株洲市" -> 地图 "株洲市" (如果地图里有)
    // 比如：数据 "黔南布依族苗族自治州" -> 地图 "黔南州" (假设地图里是简称)
    const mappedName = matchGeoName(rawName, mapGeoNames.value);
    
    const val = Number(row[`${props.metric}_mean`]);

    if (mappedName && Number.isFinite(val)) {
      mapData.push({
        name: mappedName, // ECharts 需要这个名字与 GeoJSON properties.name 一致
        value: val,
        // (可选) 可以在 tooltip 中使用 rawName 显示原始全称
        originalName: rawName 
      });
    }
  }
  return mapData;
});

// 【新增】根据当前指标决定底图类型
const currentMapName = computed(() => {
  // 风速 -> 省级地图 (china)
  if (mapMode.value === 'weather' && weatherMetric.value === 'wind') {
    return 'china';
  }
  // 其他 -> 市级地图 (china_cities)
  return 'china_cities';
});


// 【修改】气象地图数据 (色块部分)
const weatherMapSeries = computed(() => {
  // 1. 如果是风速模式，不要返回色块数据！避免 MapPanel 渲染空数据的 visualMap 报错
  if (weatherMetric.value === 'wind') {
    return []; 
  }

  // 2. 其他模式 (温度/湿度等)，走市级地图匹配逻辑
  if (mapGeoNames.value.length === 0) return [];
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];
  
  const mapData = [];
  for (const row of monthEntry.data) {
    const rawName = row.city || row.province;
    const mappedName = matchGeoName(rawName, mapGeoNames.value);
    const val = Number(row[`${weatherMetric.value}_mean`]);
    
    if (mappedName && Number.isFinite(val)) {
      mapData.push({
        name: mappedName, 
        value: val,
        originalName: rawName
      });
    }
  }
  return mapData;
});



const weatherMetricLabel = computed(() => {
  const map = { wind: "风速", temp: "气温", rh: "湿度", psfc: "气压" };
  return map[weatherMetric.value] || weatherMetric.value.toUpperCase();
});

// 类型地图数据
// 修改 typeMapData
const typeMapData = computed(() => {
  // 1. 安全检查：如果市级地图名字还没加载，先返回空，防止计算出错
  if (mapGeoNames.value.length === 0) return [];

  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  if (!monthEntry || !monthEntry.data) return [];

  // 2. 【核心修改】将聚合粒度从 "province" 改为 "city"
  // 这样 computeTypeByRegion 会返回每个市的主导类型
  const rawList = computeTypeByRegion(monthEntry.data, "city", "month");
  // 3. 名字匹配：将数据里的城市名映射到 GeoJSON 标准名
  const validList = [];
  for (const item of rawList) {
    // item.name 是数据里的城市名 (如 "株洲市")
    const mappedName = matchGeoName(item.name, mapGeoNames.value);
    
    if (mappedName) {
      validList.push({
        ...item,
        name: mappedName // 替换为地图能识别的标准名
      });
    }
  }
  
  return validList;
});

// 2. 修正月度等级分布图 (LevelBar)
// 逻辑分支：
// - 如果【未选城市】：统计该月374个城市的【月均值】分布 (空间分布)
// - 如果【已选城市】：统计该城市在该月31天的【日均值】分布 (时间分布)
// const monthLevelStats = computed(() => {
//   if (selectedCity.value) {
//     // 【微观模式】选中了城市，查看该城市的时间分布 (总数 ~30)
//     const targetCity = normalizeProvince(selectedCity.value);
    
//     // 从日数据中筛选出该城市的数据
//     const cityDailyData = currentMonthDailyData.value.filter(row => {
//       // 兼容城市名或省名匹配 (根据你的数据结构调整)
//       const rowName = normalizeProvince(row.city || row.province);
//       return rowName === targetCity;
//     });
    
//     return classifyLevels(cityDailyData, props.metric);
//   } else {
//     // 【宏观模式】未选城市，查看全国的空间分布 (总数 374)
//     // 使用聚合数据，避免 31 * 374 的巨大数字
//     const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
//     if (!monthEntry || !monthEntry.data) return classifyLevels([], props.metric);
    
//     // 注意：classifyLevels 默认读取 raw field。
//     // 对于聚合数据，我们需要告诉它去读 pm25_mean。
//     // 但是 classifyLevels 很简单，只接受字段名。
//     // 技巧：我们可以临时映射一下，或者让 dataLoader 里的 classifyLevels 支持粒度参数。
    
//     // 方案：直接传给它正确的数据结构
//     // 你的 monthly.json 里字段是 pm25_mean
//     // 我们需要构建一个临时数组，把 pm25_mean 映射为 pm25 传给 classifyLevels，
//     // 或者修改 classifyLevels 让它更智能。
//     // 鉴于 classifyLevels 是通用的，我们在这里处理数据更安全。
    
//     const mappedData = monthEntry.data.map(row => ({
//       ...row,
//       [props.metric]: row[`${props.metric}_mean`] // 把 pm25_mean 赋值给 pm25，欺骗 classifyLevels
//     }));
    
//     return classifyLevels(mappedData, props.metric);
//   }
// });
const monthLevelStats = computed(() => {
  // 如果选中了具体城市 (从地图点击)
  if (selectedCity.value) {
    // 逻辑简化：直接从当月已加载的日数据中找这个城市
    // 注意：regionIndex 中的名字通常是 "北京市"，数据中可能是 "北京" 或 "北京市"，需注意匹配
    // 建议使用 includes 或 normalize
    const target = selectedCity.value; 

    // 过滤出该城市的 28-31 条日数据
    const cityDays = currentMonthDailyData.value.filter(r => 
      (r.city && r.city.includes(target)) || (r.province && r.province.includes(target))
    );
    
    // 统计这 ~30 天的等级分布
    return classifyLevels(cityDays, props.metric);
  } 
  // 如果没选城市 (宏观视图)
  else {
    // 保持之前的逻辑：展示该月 374 个城市的月均等级分布
    const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
    if (!monthEntry || !monthEntry.data) return classifyLevels([], props.metric);

    // 映射字段名以适配 classifyLevels
    const statsData = monthEntry.data.map(row => ({
      [props.metric]: row[`${props.metric}_mean`] 
    }));
    
    return classifyLevels(statsData, props.metric);
  }
});

// 4. 雷达图 (RadialPollutant) -> 使用当前选中月的聚合数据 (表示该月的平均污染构成)
const monthRadialVector = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  const data = monthEntry ? monthEntry.data : [];
  return computeRadialVectorByMonthly(data);
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
  // 使用专门为月聚合数据设计的函数
  return computeMonthlyBoxDataForView(monthlyAggregatedData.value, props.metric);
});

// 7. 季节性堆叠图 (SeasonalLevelStack) -> 使用全年聚合数据 (展示12个月的等级构成趋势)
const monthlyLevelTimeline = computed(() => {
  // 这里 metric 传入的是 "pm25"，dataLoader 会自动找 "pm25_mean"
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
  // 只有当有日数据时才计算
  if (!currentMonthDailyData.value || currentMonthDailyData.value.length === 0) {
    console.log('[MonthView] CityTypeRibbon: No daily data available');
    return { dates: [], series: [], typeOrder: [] };
  }

  const result = computeCityTypeTrajectory(currentMonthDailyData.value, props.selectedRegion || null, currentMonth.value);
  console.log('[MonthView] CityTypeRibbon data:', {
    dates: result.dates?.length,
    series: result.series?.length,
    selectedRegion: props.selectedRegion,
    currentMonth: currentMonth.value,
    dailyDataLength: currentMonthDailyData.value?.length
  });
  return result;
});

// 11. 排名 (AQIRanking) -> 使用当前选中月的聚合数据
const monthAQIRanking = computed(() => {
  const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
  const data = monthEntry ? monthEntry.data : [];
  return computeAQIRankingMonthly(data, "province", 15);
});

// 12. 环形图 (MonthlyRing) -> 使用全年聚合数据
const monthlyRings = computed(() => {
  return computeMonthlyRingMonthly(monthlyAggregatedData.value);
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

// 【修改】风场矢量数据 (箭头部分)
const monthWindVectors = computed(() => {
  // 只有在 气象模式 且 指标为 风速 时才计算
  if (mapMode.value === 'weather' && weatherMetric.value === 'wind') {
    const monthEntry = monthlyAggregatedData.value.find(m => m.month === currentMonth.value);
    
    // 必须要有数据且地理索引已加载
    if (!monthEntry || !monthEntry.data || !regionIndex.value) return [];
    
    // 调用工具函数：
    // 使用 monthEntry.data (市级数据 374条)
    // 使用 regionIndex (查找经纬度)
    // scale 设为 0.15 (根据箭头大小调整)
    return buildMonthlyWindVectors(monthEntry.data, regionIndex.value, 0.15);
  }
  return [];
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
  
  try {
    // 【关键修复】确保地理索引优先加载
    if (!regionIndex.value) {
      regionIndex.value = await loadRegionIndex();
    }

    const months = Array.from({ length: 12 }, (_, i) => `${props.currentYear}-${String(i + 1).padStart(2, '0')}`);
    
    // 并行加载12个月的 monthly.json
    const promises = months.map(m => loadOneMonth(m));
    const results = await Promise.all(promises);

    monthlyAggregatedData.value = results.map((data, index) => ({
      date: months[index],
      month: index + 1,
      data: data || []
    }));
    
    console.log("[MonthView] 全年聚合数据加载完成");
    
    // 加载当前选中月份的详情
    await loadMonthDetail(currentMonth.value);
  } catch (err) {
    console.error("[MonthView] 加载聚合数据失败:", err);
  }
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
  const dayEntries = [];

  // 并发加载该月所有天，构建 { date, data } 格式
  const promises = [];
  for (let d = 1; d <= daysInMonth; d++) {
    const dayPadded = String(d).padStart(2, '0');
    const dateStr = `${year}-${monthStr}-${dayPadded}`;
    promises.push(
      loadDataByGranularity("day", year, dateStr).then(data => ({
        date: dateStr,
        data: data || []
      }))
    );
  }

  // 并发加载该月所有天
  const results = await Promise.allSettled(promises);

  // 收集成功的数据，保持 { date, data } 格式
  results.forEach(res => {
    if (res.status === 'fulfilled' && res.value && res.value.data && res.value.data.length > 0) {
      dayEntries.push(res.value);
    }
  });

  currentMonthDailyData.value = dayEntries;
  isMonthDetailLoading.value = false;
  console.log(`[MonthView] ${monthNum}月 详情数据加载完成，共 ${dayEntries.length} 天数据`);
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

// 【新增】初始化地图函数
async function initMapData() {
  // 1. 加载市级地图名字 (给污染/温度等用)
  const geoJson = await loadCityMap();
  if (geoJson && geoJson.features) {
    mapGeoNames.value = geoJson.features.map(f => f.properties.name);
  }
  
  // 2. 加载地理坐标索引 (给风廓线用，用来定坐标)
  if (!regionIndex.value) {
    regionIndex.value = await loadRegionIndex();
  }
}

// 在 watch(currentYear) 或 onMounted 中调用
// 建议放在 loadMonthlyAggregatedData 内部或并行调用
watch(() => props.currentYear, async () => {
  await initMapData(); // 确保地图已加载
  await loadMonthlyAggregatedData();
  // 初始化时加载当前选中月份的详情数据
  await loadMonthDetail(currentMonth.value);
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

.placeholder-map {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 0.9rem;
  background: #f8fafc;
  border-radius: 8px;
}

/* 时间控制栏 */
.time-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  margin-bottom: 8px;
}

.year-selector, .month-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.year-selector label, .month-selector label {
  font-size: 0.85rem;
  color: #64748b;
  font-weight: 500;
}

.year-selector select {
  padding: 4px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  color: #1e293b;
  font-weight: 600;
  cursor: pointer;
  outline: none;
}

.month-chips {
  display: flex;
  gap: 4px;
}

.month-chip {
  background: transparent;
  border: 1px solid transparent;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.8rem;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.month-chip:hover {
  background: #f1f5f9;
}

.month-chip.active {
  background: #2f7e57;
  color: white;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(47, 126, 87, 0.2);
}

/* 地图切换栏优化 */
.map-switch {
  /* 确保 map-switch 是 flex 布局 */
  display: flex;
  align-items: center;
  gap: 8px;
  /* 调整原有样式适应新结构 */
  padding: 6px 10px;
}

.mode-group {
  display: flex;
  gap: 4px;
}

.divider {
  width: 1px;
  height: 16px;
  background: #e2e8f0;
  margin: 0 4px;
}

.metric-toggle, .weather-toggle {
  display: flex;
  gap: 4px;
}

/* 通用按钮样式微调 */
.map-switch button {
  white-space: nowrap;
}

.metric-toggle button, .weather-toggle button {
  font-size: 0.75rem;
  padding: 3px 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
}

.metric-toggle button.active, .weather-toggle button.active {
  background: rgba(47, 126, 87, 0.1);
  border-color: #2f7e57;
  color: #2f7e57;
  font-weight: 600;
}
</style>
