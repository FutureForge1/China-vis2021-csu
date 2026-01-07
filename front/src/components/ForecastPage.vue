<template>
  <div class="forecast-page">
    <SectionHeading
      badge="预测实验"
      meta="2013-2018训练 · 2019 预测 · 实况对比"
    />

    <div class="toolbar">
      <div class="group">
        <label>数据源</label>
        <div class="chips">
          <button
            :class="{ active: mode === 'actual' }"
            @click="mode = 'actual'"
          >
            实况
          </button>
          <button :class="{ active: mode === 'pred' }" @click="mode = 'pred'">
            预测
          </button>
          <button
            :class="{ active: mode === 'compare' }"
            @click="mode = 'compare'"
          >
            对比
          </button>
        </div>
      </div>
      <div class="group">
        <label>粒度</label>
        <div class="chips">
          <button
            :class="{ active: granularity === 'day' }"
            @click="granularity = 'day'"
          >
            日
          </button>
          <button
            :class="{ active: granularity === 'month' }"
            @click="granularity = 'month'"
          >
            月
          </button>
          <button
            :class="{ active: granularity === 'year' }"
            @click="granularity = 'year'"
          >
            年
          </button>
        </div>
      </div>
      <div class="group">
        <label>日期</label>
        <select v-model="currentDate">
          <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
        </select>
      </div>
      <div class="group">
        <label>地区</label>
        <select v-model="region">
          <option
            v-for="opt in regionOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
      <div class="group">
        <label>指标</label>
        <select v-model="metric">
          <option value="pm25">PM2.5</option>
          <option value="pm10">PM10</option>
          <option value="so2">SO₂</option>
          <option value="no2">NO₂</option>
          <option value="co">CO</option>
          <option value="o3">O₃</option>
          <option value="temp">温度</option>
          <option value="rh">湿度</option>
          <option value="psfc">气压</option>
          <option value="u">风U</option>
          <option value="v">风V</option>
        </select>
      </div>
    </div>

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
          仅使用 2019 全年数据，若预测文件不存在则回退为实况。
        </div>
        <div class="importance" v-if="featureImportance.length">
          <h4>特征重要性 (ΔMAE 归一化)</h4>
          <ul>
            <li v-for="item in featureImportance" :key="item.feature">
              <span class="name">{{ item.feature.toUpperCase() }}</span>
              <span class="value"
                >{{ (item.importance * 100).toFixed(1) }}%</span
              >
            </li>
          </ul>
        </div>
      </div>
    </section>

    <section class="layout tertiary">
      <div class="pane">
        <TrendLine :metric="metric" :series="actualTrend" :dates="trendDates" />
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
import MapPanel from "./MapPanel.vue";
import SectionHeading from "./SectionHeading.vue";
import TrendLine from "./TrendLine.vue";

const metric = ref("pm25");
const mode = ref("pred");
const currentDate = ref("2019-01-01");
const dateOptions = ref([]);
const selectedRegion = ref("");
const granularity = ref("day");
const region = ref("all");
const regionOptions = ref([{ label: "全国平均", value: "all" }]);
const featureImportance = ref([]);
const metricsSummary = ref(null);

const YEAR = "2019";
const actualCache = ref(new Map());
const predCache = ref(new Map());

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
  const data = await fetchJson(buildPaths(base, dateStr));
  cache.value.set(dateStr, data || []);
  return data || [];
}

async function loadIndex() {
  const res = await fetch(`/data/${YEAR}/index.json`);
  if (res.ok) {
    const json = await res.json();
    dateOptions.value = json.days || [];
    if (dateOptions.value.length) currentDate.value = dateOptions.value[0];
  } else {
    dateOptions.value = [`${YEAR}-01-01`];
    currentDate.value = `${YEAR}-01-01`;
  }
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
      ? predCache.value.get(currentDate.value) || []
      : actualCache.value.get(currentDate.value) || [];
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

const actualAvg = computed(() =>
  averageMetric(actualCache.value.get(currentDate.value) || [])
);
const predAvg = computed(() =>
  averageMetric(predCache.value.get(currentDate.value) || [])
);
const diffAvg = computed(() => predAvg.value - actualAvg.value);

function handleMapSelect(name) {
  selectedRegion.value = name;
}

async function preloadAll() {
  if (!dateOptions.value.length) return;
  await Promise.all(
    dateOptions.value.map(async (d) => {
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
    grid: { top: 16, bottom: 28, left: 36, right: 12 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: trendDates.value,
      axisLabel: { color: "#ccc", fontSize: 10, interval: "auto" },
      axisLine: { lineStyle: { color: "#666" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#ccc", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    },
    legend: { data: ["实况", "预测"], textStyle: { color: "#ddd" } },
    series: [
      {
        name: "实况",
        type: "line",
        data: actual,
        showSymbol: false,
        lineStyle: { color: "#888", width: 1.5 },
        areaStyle: { color: "rgba(255,255,255,0.05)" },
      },
      {
        name: "预测",
        type: "line",
        data: pred,
        showSymbol: false,
        lineStyle: { color: "#FFE600", width: 1.8 },
        areaStyle: { color: "rgba(255,230,0,0.08)" },
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
    grid: { top: 28, bottom: 36, left: 42, right: 16 },
    tooltip: { trigger: "axis" },
    legend: { data: ["实况", "预测"], textStyle: { color: "#ddd" } },
    xAxis: {
      type: "category",
      data: months,
      axisLabel: { color: "#ccc", rotate: 30, fontSize: 10 },
      axisLine: { lineStyle: { color: "#666" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#ccc", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
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

  const names = featureImportance.value.map((f) => f.feature.toUpperCase());
  const importance = featureImportance.value.map((f) =>
    Number((f.importance * 100).toFixed(2))
  );
  const maeMap = new Map(
    (metricsSummary.value?.per_feature || []).map((m) => [m.feature, m.mae])
  );
  const mae = featureImportance.value.map((f) => maeMap.get(f.feature) ?? 0);

  featureChart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["重要性(%)", "MAE"], textStyle: { color: "#ddd" } },
    grid: { top: 32, bottom: 20, left: 60, right: 24 },
    xAxis: {
      type: "value",
      axisLabel: { color: "#ccc" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    },
    yAxis: { type: "category", data: names, axisLabel: { color: "#ccc" } },
    series: [
      {
        name: "重要性(%)",
        type: "bar",
        data: importance,
        itemStyle: { color: "#FFE600" },
      },
      { name: "MAE", type: "bar", data: mae, itemStyle: { color: "#7FB3FF" } },
    ],
  });
}

watch([metric, currentDate, mode, granularity, region], () => {
  nextTick(renderCompare);
  nextTick(renderMonthly);
  nextTick(renderFeature);
});

onMounted(async () => {
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
  gap: 16px;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  background: rgba(0, 0, 0, 0.25);
  padding: 10px 12px;
  border: 1px solid var(--c-border);
}
.group {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--c-white);
  font-family: var(--font-mono);
}
.group label {
  color: var(--c-gray);
  font-size: 11px;
}
.chips {
  display: flex;
  gap: 6px;
}
.chips button,
.group select {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--c-border);
  color: var(--c-white);
  padding: 6px 10px;
  font-family: var(--font-mono);
  cursor: pointer;
}
.chips button.active {
  background: var(--c-yellow);
  color: #000;
  font-weight: 600;
}
.layout {
  display: grid;
  gap: 12px;
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
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--c-border);
  padding: 12px;
  min-height: 120px;
}
.map-pane {
  min-height: 420px;
}
.stats-pane h3 {
  margin: 0 0 8px;
  color: var(--c-white);
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 8px;
}
.importance {
  margin-top: 12px;
}
.importance h4 {
  margin: 0 0 6px;
  color: var(--c-white);
  font-size: 13px;
}
.importance ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 6px;
}
.importance li {
  display: flex;
  justify-content: space-between;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--c-border);
  padding: 6px 8px;
  color: var(--c-white);
  font-family: var(--font-mono);
  font-size: 12px;
}
.importance .value {
  color: var(--c-yellow);
  font-weight: 600;
}
.chart {
  width: 100%;
  height: 260px;
}
.stat {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--c-border);
}
.label {
  color: var(--c-gray);
  font-size: 11px;
  font-family: var(--font-mono);
}
.value {
  color: var(--c-white);
  font-weight: 700;
  font-family: var(--font-mono);
}
.value.pos {
  color: #4caf50;
}
.value.neg {
  color: #e53935;
}
.note {
  color: var(--c-gray);
  font-size: 11px;
  margin-top: 6px;
}
.caption {
  color: var(--c-gray);
  font-size: 12px;
  margin-top: 6px;
}
.mini-compare {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}
.mini-compare h4 {
  margin: 0;
  color: var(--c-white);
}
.mini-chart {
  flex: 1;
  min-height: 180px;
}
</style>
