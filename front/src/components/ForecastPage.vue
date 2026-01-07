<template>
  <div class="forecast-page">
    <SectionHeading
      badge="预测实验"
      meta="2013-2018训练 · 2019 预测 · 实况对比"
    />

    <div class="toolbar glass-panel">
      <!-- View Mode Toggle -->
      <div class="control-group">
        <label>视图模式</label>
        <div class="segmented-control">
          <div
            v-for="v in [
              { k: 'overview', t: '📊 多维概览' },
              { k: 'detail', t: '🔍 详细分析' },
            ]"
            :key="v.k"
            class="segment"
            :class="{ active: viewMode === v.k }"
            @click="viewMode = v.k"
          >
            {{ v.t }}
          </div>
        </div>
      </div>

      <!-- Mode Selection -->
      <div class="control-group" v-show="viewMode === 'detail'">
        <label>显示模式</label>
        <div class="segmented-control">
          <div
            v-for="m in [
              { k: 'actual', t: '实况' },
              { k: 'pred', t: '预测' },
              { k: 'compare', t: '对比' },
            ]"
            :key="m.k"
            class="segment"
            :class="{ active: mode === m.k }"
            @click="mode = m.k"
          >
            {{ m.t }}
          </div>
        </div>
      </div>

      <!-- Granularity -->
      <div class="control-group" v-show="viewMode === 'detail'">
        <label>时间粒度</label>
        <div class="segmented-control">
          <div
            v-for="g in [
              { k: 'day', t: '日' },
              { k: 'month', t: '月' },
              { k: 'year', t: '年' },
            ]"
            :key="g.k"
            class="segment"
            :class="{ active: granularity === g.k }"
            @click="granularity = g.k"
          >
            {{ g.t }}
          </div>
        </div>
      </div>

      <!-- Date Select -->
      <div class="control-group">
        <label>时间点</label>
        <div class="custom-select-wrapper">
          <select v-model="currentDate" class="glass-select">
            <option v-for="d in dateOptions" :key="d" :value="d">
              {{ d }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
      </div>

      <!-- Region Select -->
      <div class="control-group">
        <label>地区</label>
        <div class="custom-select-wrapper">
          <select v-model="region" class="glass-select">
            <option
              v-for="opt in regionOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
      </div>

      <!-- Search (Merged) -->
      <div class="control-group search-group">
        <div class="search-box">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索城市 或 经度,纬度"
            @keyup.enter="handleSearch"
            class="glass-input"
          />
          <button class="icon-btn" @click="handleSearch" title="定位">⌖</button>
        </div>
      </div>

      <!-- Metric Select -->
      <div class="control-group" v-show="viewMode === 'detail'">
        <label>指标</label>
        <div class="custom-select-wrapper">
          <select v-model="metric" class="glass-select">
            <option
              v-for="k in [
                'pm25',
                'pm10',
                'so2',
                'no2',
                'co',
                'o3',
                'temp',
                'rh',
                'psfc',
                'u',
                'v',
              ]"
              :value="k"
              :key="k"
            >
              {{ k.toUpperCase() }}
            </option>
          </select>
          <span class="select-arrow">▼</span>
        </div>
      </div>
    </div>

    <!-- Overview Section -->
    <ForecastOverview
      v-if="viewMode === 'overview'"
      :actual-data="allActualData"
      :pred-data="allPredData"
      :current-date="currentDate"
      :region="region"
      :region-label="regionLabel"
    />

    <!-- Detail Analysis Section -->
    <div v-show="viewMode === 'detail'" class="detail-section">
      <section class="layout secondary">
        <div class="pane map-pane">
          <MapPanel
            :data="mapSeries"
            :metric="metric"
            :title="mapTitle"
            :selected-name="selectedRegion"
            @select="handleMapSelect"
          />
        </div>
        <div class="pane stats-pane">
          <h3>概要</h3>
          <div class="stat-grid">
            <div class="stat">
              <span class="label">实况均值</span>
              <span class="value">{{ actualAvg.toFixed(2) }}</span>
            </div>
            <div class="stat">
              <span class="label">预测均值</span>
              <span class="value">{{ predAvg.toFixed(2) }}</span>
            </div>
            <div class="stat" v-if="mode === 'compare'">
              <span class="label">偏差(预测-实况)</span>
              <span
                class="value"
                :class="{ pos: diffAvg >= 0, neg: diffAvg < 0 }"
                >{{ diffAvg.toFixed(2) }}</span
              >
            </div>
          </div>
          <div class="note">
            数据：2019全年。若预测文件缺失，将回退显示实况。
          </div>
          <!-- 移除原有列表形式的重要性展示，改用 ECharts 渲染 -->
        </div>
      </section>

      <section class="layout tertiary">
        <div class="pane">
          <TrendLine
            :metric="metric"
            :series="actualTrend"
            :dates="trendDates"
          />
          <p class="caption">实况趋势 ({{ granularityLabel }})</p>
        </div>
        <div class="pane">
          <TrendLine :metric="metric" :series="predTrend" :dates="trendDates" />
          <p class="caption">预测趋势 ({{ granularityLabel }})</p>
        </div>
        <div class="pane">
          <div class="mini-compare">
            <h4>对比曲线</h4>
            <div class="mini-chart" ref="compareRef"></div>
            <div class="caption">灰=实况，黄=预测；跟随粒度/地区筛选</div>
          </div>
        </div>
      </section>

      <section class="layout quaternary">
        <div class="pane">
          <h4>月度预测 vs 实况</h4>
          <div class="chart" ref="monthlyRef"></div>
          <p class="caption">按月均值对比，当前指标与地区</p>
        </div>
        <div class="pane">
          <h4>特征权重 / 误差</h4>
          <div class="chart" ref="featureRef"></div>
          <p class="caption">重要性取自ΔMAE归一化，MAE来自metrics_summary</p>
        </div>
      </section>
    </div>
    <!-- End Detail Section -->
  </div>
</template>

<script setup>
import * as echarts from "echarts";
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { loadRegionIndex } from "../utils/dataLoader";
import ForecastOverview from "./ForecastOverview.vue";
import MapPanel from "./MapPanel.vue";
import SectionHeading from "./SectionHeading.vue";
import TrendLine from "./TrendLine.vue";

const viewMode = ref("overview"); // 新增：视图模式切换
const metric = ref("pm25");
const mode = ref("pred");
const currentDate = ref("2019-01-01");
const rawDates = ref([]);
const dateOptions = computed(() => {
  if (granularity.value === "day") return rawDates.value;
  if (granularity.value === "month") {
    const months = Array.from(
      new Set(rawDates.value.map((d) => d.slice(0, 7)))
    );
    return months.sort();
  }
  return [YEAR];
});
const selectedRegion = ref("");
const granularity = ref("day");
const region = ref("all");
const searchQuery = ref("");
const regionOptions = ref([{ label: "全国平均", value: "all" }]);
const featureImportance = ref([]);
const metricsSummary = ref(null);
const regionIndex = ref(null);

const YEAR = "2019";
const actualCache = ref(new Map());
const predCache = ref(new Map());
const selectedCoord = computed(() => {
  if (region.value === "all" || !regionIndex.value) return null;
  const hit = regionIndex.value.get(region.value);
  return hit || null;
});

let compareChart = null;
const compareRef = ref(null);
let monthlyChart = null;
const monthlyRef = ref(null);
let featureChart = null;
const featureRef = ref(null);

function buildPaths(base, dateStr) {
  const clean = dateStr.replace(/-/g, "");
  const year = clean.slice(0, 4);
  const monthPadded = clean.slice(4, 6);
  const monthRaw = String(parseInt(monthPadded, 10));
  const day = clean.slice(6, 8);
  return [
    `${base}/${year}/${monthPadded}/${day}/${clean}.json`,
    `${base}/${year}/${monthRaw}/${day}/${clean}.json`,
    `${base}/${year}/${monthPadded}/${clean}.json`,
  ];
}

async function fetchJson(paths) {
  for (const p of paths) {
    try {
      const res = await fetch(p);
      if (res.ok) return await res.json();
    } catch (_) {
      /* ignore */
    }
  }
  return [];
}

async function loadDay(dateStr, cache, base) {
  if (cache.value.has(dateStr)) return cache.value.get(dateStr);
  let data = await fetchJson(buildPaths(base, dateStr));
  // 标准化数据：确保所有数值字段都是数字类型（预测数据可能是number，实况数据可能是string）
  if (data && Array.isArray(data)) {
    data = data.map((row) => {
      const normalized = { ...row };
      // 转换所有可能的数值字段
      const numericFields = [
        "pm25",
        "pm10",
        "so2",
        "no2",
        "co",
        "o3",
        "temp",
        "rh",
        "psfc",
        "u",
        "v",
      ];
      for (const field of numericFields) {
        if (normalized[field] !== undefined && normalized[field] !== null) {
          normalized[field] = Number(normalized[field]);
        }
      }
      return normalized;
    });
  }
  cache.value.set(dateStr, data || []);
  return data || [];
}

async function loadIndex() {
  // 强制生成 2019 全年日期，不再依赖 index.json，确保显示完整的一年
  const days = [];
  const start = new Date(`${YEAR}-01-01`);
  const end = new Date(`${YEAR}-12-31`);
  for (let d = start; d <= end; d.setDate(d.getDate() + 1)) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const da = String(d.getDate()).padStart(2, "0");
    days.push(`${y}-${m}-${da}`);
  }
  rawDates.value = days;
  finalizeDateInit();
}

function finalizeDateInit() {
  const opts = dateOptions.value;
  if (opts.length && !opts.includes(currentDate.value)) {
    currentDate.value = opts[0];
  }
}

watch(granularity, () => {
  const opts = dateOptions.value;
  if (!opts.includes(currentDate.value) && opts.length) {
    currentDate.value = opts[0];
  }
});

function rowsForSelection(cache) {
  if (granularity.value === "day") {
    return cache.value.get(currentDate.value) || [];
  }
  if (granularity.value === "month") {
    const prefix = `${currentDate.value}-`;
    const acc = [];
    for (const [d, rows] of cache.value.entries()) {
      if (d.startsWith(prefix)) acc.push(...(rows || []));
    }
    return acc;
  }
  const acc = [];
  for (const rows of cache.value.values()) {
    if (rows) acc.push(...rows);
  }
  return acc;
}

function aggregateMap(rows, metricName) {
  const sums = new Map();
  const counts = new Map();
  for (const row of rows) {
    const val = Number(row?.[metricName]);
    if (!Number.isFinite(val)) continue;
    const prov = row.province;
    if (prov) {
      sums.set(prov, (sums.get(prov) || 0) + val);
      counts.set(prov, (counts.get(prov) || 0) + 1);
    }
    if (row.city) {
      sums.set(row.city, (sums.get(row.city) || 0) + val);
      counts.set(row.city, (counts.get(row.city) || 0) + 1);
    }
  }
  return Array.from(sums.entries()).map(([name, sum]) => ({
    name,
    value: sum / (counts.get(name) || 1),
  }));
}

function averageMetric(rows, metricName = metric.value) {
  const vals = rows
    .map((r) => Number(r?.[metricName]))
    .filter((v) => Number.isFinite(v));
  if (!vals.length) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

function matchesRegion(row, regionName) {
  if (regionName === "all" || !regionName) return true;
  return row.province === regionName || row.city === regionName;
}

function findRegionByName(name) {
  if (!name) return null;
  const trimmed = name.trim();
  if (!trimmed) return null;
  // 优先精确匹配 options
  const direct = regionOptions.value.find(
    (o) => o.value === trimmed || o.label === trimmed
  );
  if (direct) return direct.value;
  // 退化为包含匹配（RegionIndex 里更多别名）
  if (regionIndex.value) {
    for (const key of regionIndex.value.keys()) {
      if (key.includes(trimmed)) return key;
    }
  }
  return null;
}

function findClosestRegionByCoord(lon, lat) {
  if (!regionIndex.value) return null;
  let best = null;
  let bestDist = Number.POSITIVE_INFINITY;
  for (const [name, coord] of regionIndex.value.entries()) {
    const dLon = lon - coord.lon;
    const dLat = lat - coord.lat;
    const dist2 = dLon * dLon + dLat * dLat; // 平面近似足够
    if (dist2 < bestDist) {
      bestDist = dist2;
      best = name;
    }
  }
  return best;
}

function handleSearch() {
  const q = searchQuery.value.trim();
  if (!q) return;
  // 经纬度模式："116.4,39.9" 或 "116.4 39.9"
  const coordMatch = q.match(/(-?\d+(?:\.\d+)?)\s*[ ,]\s*(-?\d+(?:\.\d+)?)/);
  if (coordMatch) {
    const lon = Number(coordMatch[1]);
    const lat = Number(coordMatch[2]);
    if (Number.isFinite(lon) && Number.isFinite(lat)) {
      const near = findClosestRegionByCoord(lon, lat);
      if (near) {
        region.value = near;
        selectedRegion.value = near;
      }
    }
    return;
  }

  const hit = findRegionByName(q);
  if (hit) {
    region.value = hit;
    selectedRegion.value = hit;
  }
}

function aggregateSeries(cache, metricName) {
  const grouped = new Map();
  for (const [dateStr, rows] of cache.value.entries()) {
    if (!rows) continue;
    const filtered = rows.filter((r) => matchesRegion(r, region.value));
    const val = averageMetric(filtered, metricName);
    if (granularity.value === "day") {
      grouped.set(dateStr, val);
    } else if (granularity.value === "month") {
      const key = dateStr.slice(0, 7); // YYYY-MM
      const list = grouped.get(key) || [];
      list.push(val);
      grouped.set(key, list);
    } else if (granularity.value === "year") {
      const key = dateStr.slice(0, 4);
      const list = grouped.get(key) || [];
      list.push(val);
      grouped.set(key, list);
    }
  }

  return Array.from(grouped.entries())
    .map(([k, v]) => ({
      date: k,
      value: Array.isArray(v)
        ? averageMetric(
            v.map((x) => ({ val: x })),
            "val"
          )
        : v,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));
}

function aggregateByMonth(cache, metricName) {
  const monthMap = new Map();
  for (const [dateStr, rows] of cache.value.entries()) {
    if (!rows) continue;
    const filtered = rows.filter((r) => matchesRegion(r, region.value));
    const val = averageMetric(filtered, metricName);
    const monthKey = dateStr.slice(0, 7); // YYYY-MM
    const list = monthMap.get(monthKey) || [];
    list.push(val);
    monthMap.set(monthKey, list);
  }
  return Array.from(monthMap.entries())
    .map(([k, arr]) => ({
      month: k,
      value: averageMetric(
        arr.map((x) => ({ val: x })),
        "val"
      ),
    }))
    .sort((a, b) => a.month.localeCompare(b.month));
}

const mapSeries = computed(() => {
  const rows =
    mode.value === "pred"
      ? rowsForSelection(predCache)
      : rowsForSelection(actualCache);
  return aggregateMap(rows, metric.value);
});

const mapTitle = computed(() => {
  if (mode.value === "pred")
    return `预测 ${YEAR} ${metric.value.toUpperCase()} 分布`;
  if (mode.value === "compare")
    return `预测 vs 实况 ${YEAR} ${metric.value.toUpperCase()}`;
  return `实况 ${YEAR} ${metric.value.toUpperCase()} 分布`;
});

const actualTrend = computed(() => aggregateSeries(actualCache, metric.value));
const predTrend = computed(() => aggregateSeries(predCache, metric.value));

const trendDates = computed(() => actualTrend.value.map((d) => d.date));

const monthlyCompare = computed(() => {
  const act = aggregateByMonth(actualCache, metric.value);
  const pred = aggregateByMonth(predCache, metric.value);
  const mapPred = new Map(pred.map((p) => [p.month, p.value]));
  return act.map((a) => ({
    month: a.month,
    actual: a.value,
    pred: mapPred.get(a.month) ?? a.value,
  }));
});

const actualAvg = computed(() => {
  const rows = rowsForSelection(actualCache).filter((r) =>
    matchesRegion(r, region.value)
  );
  return averageMetric(rows);
});

const predAvg = computed(() => {
  const rows = rowsForSelection(predCache).filter((r) =>
    matchesRegion(r, region.value)
  );
  return averageMetric(rows);
});

const diffAvg = computed(() => predAvg.value - actualAvg.value);

// 概览模式需要的全部数据
const allActualData = computed(() => {
  const result = [];
  for (const [_, data] of actualCache.value) {
    if (Array.isArray(data)) {
      result.push(...data.filter((r) => matchesRegion(r, region.value)));
    }
  }
  return result;
});

const allPredData = computed(() => {
  const result = [];
  for (const [_, data] of predCache.value) {
    if (Array.isArray(data)) {
      result.push(...data.filter((r) => matchesRegion(r, region.value)));
    }
  }
  return result;
});

const regionLabel = computed(() => {
  const opt = regionOptions.value.find((o) => o.value === region.value);
  return opt ? opt.label : "全国";
});

function handleMapSelect(name) {
  if (!name) {
    // 名字为空，说明点击了 "BACK TO NATIONAL"
    selectedRegion.value = "";
    region.value = "all";
    return;
  }

  selectedRegion.value = name;

  // 尝试在下拉框选项中找到对应值
  const hit = regionOptions.value.find(
    (o) => o.value === name || o.label === name
  );
  if (hit) {
    region.value = hit.value;
  } else {
    // 如果不在列表里（比如具体城市但列表只有省），也强制选中
    region.value = name;
  }
}

watch(region, (newVal) => {
  if (newVal === "all") {
    selectedRegion.value = "";
  } else {
    selectedRegion.value = newVal;
  }
});

async function preloadAll() {
  if (!rawDates.value.length) return;
  await Promise.all(
    rawDates.value.map(async (d) => {
      await loadDay(d, actualCache, "/data");
      const pred = await loadDay(d, predCache, "/data/predictions");
      if (!pred?.length) {
        // fallback to actual when prediction missing
        predCache.value.set(d, actualCache.value.get(d) || []);
      }
    })
  );

  // Build region options from loaded data
  const regions = new Set();
  for (const rows of actualCache.value.values()) {
    for (const r of rows || []) {
      if (r.province) regions.add(r.province);
      if (r.city) regions.add(r.city);
    }
  }
  regionOptions.value = [{ label: "全国平均", value: "all" }].concat(
    Array.from(regions)
      .sort()
      .map((r) => ({ label: r, value: r }))
  );
}

function renderCompare() {
  if (!compareRef.value) return;
  if (!compareChart) compareChart = echarts.init(compareRef.value);

  const actual = actualTrend.value.map((d) => d.value);
  const pred = predTrend.value.map((d) => d.value);

  compareChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 36, bottom: 28, left: 48, right: 16 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: trendDates.value,
      axisLabel: { color: "#666", fontSize: 10, interval: "auto" },
      axisLine: { lineStyle: { color: "#ddd" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#666", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.06)" } },
    },
    legend: { data: ["实况", "预测"], textStyle: { color: "#333" } },
    series: [
      {
        name: "实况",
        type: "line",
        data: actual,
        showSymbol: false,
        lineStyle: { color: "#7FB3FF", width: 2 },
        areaStyle: { color: "rgba(127,179,255,0.15)" },
      },
      {
        name: "预测",
        type: "line",
        data: pred,
        showSymbol: false,
        lineStyle: { color: "#FFE600", width: 2.5 },
        areaStyle: { color: "rgba(255,230,0,0.2)" },
      },
    ],
  });
}

function renderMonthly() {
  if (!monthlyRef.value) return;
  if (!monthlyChart) monthlyChart = echarts.init(monthlyRef.value);

  const months = monthlyCompare.value.map((d) => d.month);
  const act = monthlyCompare.value.map((d) => d.actual);
  const pred = monthlyCompare.value.map((d) => d.pred);

  monthlyChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 36, bottom: 42, left: 48, right: 16 },
    tooltip: { trigger: "axis" },
    legend: { data: ["实况", "预测"], textStyle: { color: "#333" } },
    xAxis: {
      type: "category",
      data: months,
      axisLabel: { color: "#666", rotate: 30, fontSize: 10 },
      axisLine: { lineStyle: { color: "#ddd" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#666", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.06)" } },
    },
    series: [
      {
        name: "实况",
        type: "bar",
        data: act,
        itemStyle: { color: "#7FB3FF" },
        barGap: "10%",
      },
      {
        name: "预测",
        type: "bar",
        data: pred,
        itemStyle: { color: "#FFE600" },
      },
    ],
  });
}

function renderFeature() {
  if (!featureRef.value) return;
  if (!featureChart) featureChart = echarts.init(featureRef.value);

  const data = featureImportance.value.map((f) => ({
    name: f.feature.toUpperCase(),
    value: Number((f.importance * 100).toFixed(2)),
  }));

  // Sort for Nightingale Rose effect
  data.sort((a, b) => a.value - b.value);

  featureChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "item", formatter: "{b}: {c}%" },
    legend: {
      type: "scroll",
      left: "left",
      top: "middle",
      orient: "vertical",
      textStyle: { color: "#333", fontSize: 11 },
    },
    series: [
      {
        name: "特征重要性",
        type: "pie",
        radius: [20, 100],
        center: ["60%", "50%"],
        roseType: "area",
        itemStyle: {
          borderRadius: 4,
          borderColor: "rgba(0,0,0,0.5)",
          borderWidth: 1,
        },
        data: data,
        label: {
          color: "#333",
          fontSize: 11,
        },
        labelLine: {
          lineStyle: { color: "rgba(0, 0, 0, 0.2)" },
        },
        animationType: "scale",
        animationEasing: "elasticOut",
        animationDelay: function (idx) {
          return Math.random() * 200;
        },
      },
    ],
  });
}

watch([metric, currentDate, mode, granularity, region], () => {
  nextTick(renderCompare);
  nextTick(renderMonthly);
  nextTick(renderFeature);
});

onMounted(async () => {
  regionIndex.value = await loadRegionIndex();
  await loadIndex();
  await preloadAll();
  await loadFeatureImportance();
  await loadMetrics();
  nextTick(renderCompare);
  nextTick(renderMonthly);
  nextTick(renderFeature);
});

onBeforeUnmount(() => {
  if (compareChart) {
    compareChart.dispose();
    compareChart = null;
  }
  if (monthlyChart) {
    monthlyChart.dispose();
    monthlyChart = null;
  }
  if (featureChart) {
    featureChart.dispose();
    featureChart = null;
  }
});

async function loadFeatureImportance() {
  try {
    const res = await fetch("/data/predictions/feature_importance.json");
    if (res.ok) {
      const json = await res.json();
      featureImportance.value = json;
    }
  } catch (_) {
    featureImportance.value = [];
  }
}

async function loadMetrics() {
  try {
    const res = await fetch("/data/predictions/metrics_summary.json");
    if (res.ok) {
      metricsSummary.value = await res.json();
    }
  } catch (_) {
    metricsSummary.value = null;
  }
}

const granularityLabel = computed(() => {
  if (granularity.value === "day") return "日";
  if (granularity.value === "month") return "月";
  return "年";
});
</script>

<style scoped>
.forecast-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  color: var(--c-black);
  padding: 0;
}

.glass-panel {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  background: var(--c-card);
  border: 1px solid var(--c-border);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 16px 20px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.control-group label {
  font-size: 10px;
  color: var(--c-gray);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Segmented Control */
.segmented-control {
  display: flex;
  background: var(--c-light-gray);
  border-radius: 6px;
  padding: 2px;
  border: 1px solid var(--c-border);
}

.segment {
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: var(--c-gray);
  user-select: none;
  font-weight: 500;
}

.segment:hover {
  color: var(--c-black);
  background: rgba(255, 230, 0, 0.1);
}

.segment.active {
  background: var(--c-yellow);
  color: var(--c-black);
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(255, 230, 0, 0.3);
}

/* Custom Select */
.custom-select-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.glass-select {
  appearance: none;
  background: var(--c-white);
  border: 1px solid var(--c-border);
  color: var(--c-black);
  padding: 8px 32px 8px 12px;
  border-radius: 6px;
  font-family: var(--font-mono);
  font-size: 12px;
  min-width: 120px;
  cursor: pointer;
  transition: all 0.2s;
}

.glass-select option {
  background: var(--c-white);
  color: var(--c-black);
  padding: 8px;
}

.glass-select:hover {
  border-color: rgba(0, 0, 0, 0.2);
  background: #fafafa;
}

.glass-select:focus {
  outline: none;
  border-color: var(--c-yellow);
  box-shadow: 0 0 0 3px rgba(255, 230, 0, 0.15);
}

.select-arrow {
  position: absolute;
  right: 10px;
  font-size: 8px;
  color: var(--c-gray);
  pointer-events: none;
}

/* Search Box */
.search-group {
  margin-left: auto; /* Push to right */
}

.search-box {
  display: flex;
  align-items: center;
  background: var(--c-white);
  border: 1px solid var(--c-border);
  border-radius: 20px;
  padding: 2px 4px;
  transition: all 0.2s;
}

.search-box:focus-within {
  border-color: var(--c-yellow);
  background: #fafafa;
  box-shadow: 0 0 0 3px rgba(255, 230, 0, 0.15);
}

.glass-input {
  background: transparent;
  border: none;
  color: var(--c-black);
  padding: 8px 12px;
  font-size: 12px;
  width: 180px;
  outline: none;
}

.glass-input::placeholder {
  color: var(--c-gray);
}

.icon-btn {
  background: none;
  border: none;
  color: var(--c-yellow);
  cursor: pointer;
  padding: 6px 10px;
  font-size: 14px;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.icon-btn:hover {
  opacity: 1;
}

/* Layout adjustments */
.layout {
  display: grid;
  gap: 16px;
}
.layout.secondary {
  grid-template-columns: 2fr 1fr;
}
.layout.tertiary {
  grid-template-columns: repeat(3, 1fr);
}
.layout.quaternary {
  grid-template-columns: repeat(2, 1fr);
}

.pane {
  background: var(--c-card);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 20px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.pane:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.map-pane {
  min-height: 480px;
  border: 1px solid var(--c-border);
}

.stats-pane h3 {
  margin: 0 0 16px;
  font-size: 16px;
  font-weight: 600;
  color: var(--c-black);
  border-bottom: 2px solid var(--c-yellow);
  padding-bottom: 8px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: rgba(255, 230, 0, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(255, 230, 0, 0.2);
}

.stat .label {
  font-size: 11px;
  color: var(--c-gray);
  margin-bottom: 4px;
  text-transform: uppercase;
}

.stat .value {
  font-size: 20px;
  font-weight: 600;
  color: var(--c-black);
  font-family: var(--font-mono);
}

.note {
  font-size: 11px;
  color: var(--c-gray);
  line-height: 1.5;
  padding: 8px 12px;
  background: rgba(255, 230, 0, 0.05);
  border-radius: 4px;
  border-left: 3px solid var(--c-yellow);
}

.mini-compare h4,
.pane h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--c-black);
  font-weight: 600;
}

.mini-chart {
  flex: 1;
  min-height: 200px;
}

.chart {
  width: 100%;
  height: 300px;
}

.coord-display {
  display: inline-block;
  color: var(--c-gray);
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--c-light-gray);
  border: 1px solid var(--c-border);
  padding: 4px 8px;
  border-radius: 4px;
}

.caption {
  margin-top: 12px;
  font-size: 12px;
  color: var(--c-gray);
  text-align: center;
  font-style: italic;
}
</style>
