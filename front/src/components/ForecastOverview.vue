<template>
  <div class="forecast-overview">
    <div class="overview-header">
      <h2 class="overview-title">
        <span class="badge">多维预测概览</span>
        <span class="subtitle">{{ timeRangeLabel }} · {{ regionLabel }}</span>
      </h2>
    </div>

    <div class="overview-grid">
      <!-- 3D污染物构成图 (原3D时空曲面图) -->
      <div class="overview-card large">
        <div class="card-header">
          <h3>🧱 重点区域污染物3D构成墙</h3>
          <!-- 移除单选PM2.5控件，因为现在展示的是全污染物 -->
        </div>
        <div class="chart-3d" ref="surface3DRef"></div>
        <p class="chart-desc">Top15 污染城市多污染物 3D 结构对比 (基于 IAQI)</p>
      </div>

      <!-- 多维雷达对比 -->
      <div class="overview-card medium">
        <div class="card-header">
          <h3>🎯 多污染物雷达对比</h3>
        </div>
        <div class="chart-radar" ref="radarRef"></div>
        <p class="chart-desc">预测值（蓝）vs 实际值（橙）· 归一化显示</p>
      </div>

      <!-- AQI预警时间轴 -->
      <div class="overview-card xlarge" v-if="granularity === 'year'">
        <div class="card-header">
          <h3>⚠️ AQI预警时间轴（2019年）</h3>
          <div class="card-controls">
            <span class="threshold-label">预警阈值: AQI ≥ 150</span>
          </div>
        </div>
        <div class="chart-timeline" ref="timelineRef"></div>
        <p class="chart-desc">点击日期联动查看空间分布 · 颜色表示污染等级</p>
      </div>

      <!-- 误差分布箱线图 -->
      <div class="overview-card medium">
        <div class="card-header">
          <h3>📦 预测误差分布</h3>
        </div>
        <div class="chart-box" ref="errorBoxRef"></div>
        <p class="chart-desc">各污染物误差统计 · 重污染日标红 · 点击查看详情</p>
      </div>

      <!-- 关联热力矩阵 -->
      <div class="overview-card medium">
        <div class="card-header">
          <h3>🔥 污染物关联热力图</h3>
          <div class="card-controls">
            <button
              class="toggle-btn"
              :class="{ active: heatmapMode === 'pred' }"
              @click="heatmapMode = 'pred'"
            >
              预测
            </button>
            <button
              class="toggle-btn"
              :class="{ active: heatmapMode === 'actual' }"
              @click="heatmapMode = 'actual'"
            >
              实际
            </button>
          </div>
        </div>
        <div class="chart-heatmap" ref="heatmapRef"></div>
        <p class="chart-desc">相关系数矩阵 · 揭示污染物联动关系</p>
      </div>

      <!-- AQI等级分布 -->
      <div class="overview-card small">
        <div class="card-header">
          <h3>📊 AQI等级分布</h3>
        </div>
        <div class="chart-dist" ref="aqiDistRef"></div>
        <p class="chart-desc">预测准确度 · 等级一致性分析</p>
      </div>

      <!-- 平行坐标系 -->
      <div class="overview-card xlarge">
        <div class="card-header">
          <h3>📈 多维平行坐标系</h3>
          <div class="card-controls">
            <label class="checkbox-label">
              <input type="checkbox" v-model="showOutliers" />
              <span>显示异常值</span>
            </label>
          </div>
        </div>
        <div class="chart-parallel" ref="parallelRef"></div>
        <p class="chart-desc">高维数据全景视图 · 拖拽坐标轴可筛选</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import * as echarts from "echarts";
import "echarts-gl"; // 3D图表支持
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";

const props = defineProps({
  actualData: { type: Array, default: () => [] }, // 实际数据
  predData: { type: Array, default: () => [] }, // 预测数据
  currentDate: { type: String, default: "" },
  granularity: { type: String, default: "year" }, // 时间粒度：day/month/year
  region: { type: String, default: "all" },
  regionLabel: { type: String, default: "全国" },
});

// 时间范围标签
const timeRangeLabel = computed(() => {
  if (props.granularity === "day") {
    return props.currentDate;
  } else if (props.granularity === "month") {
    return props.currentDate.slice(0, 7); // YYYY-MM
  } else {
    return "2019年全年";
  }
});

// 控制状态
const surface3DMetric = ref("pm25");
const heatmapMode = ref("pred");
const showOutliers = ref(false);
const selectedDate = ref("");

// Chart refs
const surface3DRef = ref(null);
const radarRef = ref(null);
const heatmapRef = ref(null);
const aqiDistRef = ref(null);
const parallelRef = ref(null);
const errorBoxRef = ref(null);
const timelineRef = ref(null);

// Emit events
const emit = defineEmits(["date-select", "error-detail"]);

// Chart instances
let surface3DChart = null;
let radarChart = null;
let heatmapChart = null;
let aqiDistChart = null;
let parallelChart = null;
let errorBoxChart = null;
let timelineChart = null;

// Geo Data
let cityGeoMap = new Map();

// 污染物列表
const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
const allMetrics = [...pollutants, "temp", "rh", "psfc"];

// 计算AQI
const calculateAQI = (pm25, pm10, so2, no2, co, o3) => {
  const iaqi = [
    calcIAQI(
      pm25,
      [0, 35, 75, 115, 150, 250, 350, 500],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
    calcIAQI(
      pm10,
      [0, 50, 150, 250, 350, 420, 500, 600],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
    calcIAQI(
      so2,
      [0, 50, 150, 475, 800, 1600, 2100, 2620],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
    calcIAQI(
      no2,
      [0, 40, 80, 180, 280, 565, 750, 940],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
    calcIAQI(
      co,
      [0, 2, 4, 14, 24, 36, 48, 60],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
    calcIAQI(
      o3,
      [0, 160, 200, 300, 400, 800, 1000, 1200],
      [0, 50, 100, 150, 200, 300, 400, 500]
    ),
  ];
  return Math.max(...iaqi.filter((v) => !isNaN(v)));
};

const calcIAQI = (cp, bps, iaqis) => {
  if (cp === null || cp === undefined || isNaN(cp)) return 0;
  for (let i = 0; i < bps.length - 1; i++) {
    if (cp >= bps[i] && cp < bps[i + 1]) {
      return (
        ((iaqis[i + 1] - iaqis[i]) / (bps[i + 1] - bps[i])) * (cp - bps[i]) +
        iaqis[i]
      );
    }
  }
  return iaqis[iaqis.length - 1];
};

const getAQILevel = (aqi) => {
  if (aqi <= 50) return "优";
  if (aqi <= 100) return "良";
  if (aqi <= 150) return "轻度";
  if (aqi <= 200) return "中度";
  if (aqi <= 300) return "重度";
  return "严重";
};

// 计算相关系数
const calculateCorrelation = (data, metrics) => {
  const matrix = [];
  for (let i = 0; i < metrics.length; i++) {
    const row = [];
    for (let j = 0; j < metrics.length; j++) {
      if (i === j) {
        row.push(1);
      } else {
        const arr1 = data
          .map((d) => d[metrics[i]])
          .filter((v) => v != null && !isNaN(v));
        const arr2 = data
          .map((d) => d[metrics[j]])
          .filter((v) => v != null && !isNaN(v));
        row.push(pearsonCorrelation(arr1, arr2));
      }
    }
    matrix.push(row);
  }
  return matrix;
};

const pearsonCorrelation = (x, y) => {
  if (x.length !== y.length || x.length === 0) return 0;
  const n = x.length;
  const sumX = x.reduce((a, b) => a + b, 0);
  const sumY = y.reduce((a, b) => a + b, 0);
  const sumXY = x.reduce((sum, xi, i) => sum + xi * y[i], 0);
  const sumX2 = x.reduce((sum, xi) => sum + xi * xi, 0);
  const sumY2 = y.reduce((sum, yi) => sum + yi * yi, 0);

  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt(
    (n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY)
  );

  return denominator === 0 ? 0 : numerator / denominator;
};

// 1. 渲染重点区域多污染物3D构成墙 (3D Multi-Pollutant Structure)
const render3DSurface = () => {
  if (!surface3DRef.value) return;
  if (!surface3DChart) {
    surface3DChart = echarts.init(surface3DRef.value);
  }

  // 使用所有传入的数据（已经在父组件中按粒度过滤）
  const daysData = props.predData;

  if (daysData.length === 0) {
    surface3DChart.setOption(
      {
        title: {
          text: "当前时间范围无预测数据",
          left: "center",
          top: "center",
          textStyle: { color: "#999" },
        },
      },
      true
    );
    return;
  }

  // 2. 数据处理：按城市聚合，计算平均IAQI
  const cityAggregates = new Map();

  daysData.forEach((d) => {
    const city = d.city || "未知";
    if (!cityAggregates.has(city)) {
      cityAggregates.set(city, {
        city,
        pm25List: [],
        pm10List: [],
        so2List: [],
        no2List: [],
        coList: [],
        o3List: [],
      });
    }
    const agg = cityAggregates.get(city);
    if (d.pm25 != null) agg.pm25List.push(d.pm25);
    if (d.pm10 != null) agg.pm10List.push(d.pm10);
    if (d.so2 != null) agg.so2List.push(d.so2);
    if (d.no2 != null) agg.no2List.push(d.no2);
    if (d.co != null) agg.coList.push(d.co);
    if (d.o3 != null) agg.o3List.push(d.o3);
  });

  const cityStats = Array.from(cityAggregates.values()).map((agg) => {
    const avg = (arr) =>
      arr.length > 0 ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;

    const avgPm25 = avg(agg.pm25List);
    const avgPm10 = avg(agg.pm10List);
    const avgSo2 = avg(agg.so2List);
    const avgNo2 = avg(agg.no2List);
    const avgCo = avg(agg.coList);
    const avgO3 = avg(agg.o3List);

    // 计算平均IAQI
    const i_pm25 = calcIAQI(
      avgPm25,
      [0, 35, 75, 115, 150, 250, 350, 500],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_pm10 = calcIAQI(
      avgPm10,
      [0, 50, 150, 250, 350, 420, 500, 600],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_so2 = calcIAQI(
      avgSo2,
      [0, 50, 150, 475, 800, 1600, 2100, 2620],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_no2 = calcIAQI(
      avgNo2,
      [0, 40, 80, 180, 280, 565, 750, 940],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_co = calcIAQI(
      avgCo,
      [0, 2, 4, 14, 24, 36, 48, 60],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_o3 = calcIAQI(
      avgO3,
      [0, 160, 200, 300, 400, 800, 1000, 1200],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );

    const maxIAQI = Math.max(i_pm25, i_pm10, i_so2, i_no2, i_co, i_o3);

    return {
      city: agg.city,
      values: [i_pm25, i_pm10, i_so2, i_no2, i_co, i_o3],
      maxIAQI,
      avgConc: {
        pm25: avgPm25,
        pm10: avgPm10,
        so2: avgSo2,
        no2: avgNo2,
        co: avgCo,
        o3: avgO3,
      },
    };
  });

  // 3. 排序取 Top 15 (按污染最重)
  const topCities = cityStats
    .sort((a, b) => b.maxIAQI - a.maxIAQI)
    .slice(0, 15);

  // 4. 构建 3D Bar 数据 [X:污染物, Y:城市, Z:IAQI]
  // Pollutants order: PM2.5, PM10, SO2, NO2, CO, O3
  const pollutantsLabel = ["PM2.5", "PM10", "SO2", "NO2", "CO", "O3"];
  const bar3DData = [];

  topCities.forEach((c, yIndex) => {
    // yIndex对应城市
    c.values.forEach((val, xIndex) => {
      // xIndex对应污染物
      bar3DData.push({
        name: c.city + " " + pollutantsLabel[xIndex],
        value: [xIndex, yIndex, val],
        itemStyle: {
          color: getAQIColor(val), // 使用 AQI 颜色
        },
      });
    });
  });

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      formatter: (params) => {
        const city = topCities[params.value[1]].city;
        const type = pollutantsLabel[params.value[0]];
        const val = params.value[2].toFixed(0);
        return `${city} <br/> ${type} IAQI: <strong>${val}</strong>`;
      },
    },
    xAxis3D: {
      type: "category",
      data: pollutantsLabel,
      name: "污染物",
      axisLabel: {
        interval: 0,
        textStyle: { color: "#666", fontSize: 10 },
      },
      axisPointer: { show: false }, // 优化视觉
    },
    yAxis3D: {
      type: "category",
      data: topCities.map((c) => c.city),
      name: "Top 污染城市",
      axisLabel: {
        interval: 0,
        rotate: -45, // 倾斜避免重叠
        textStyle: { color: "#666", fontSize: 10 },
      },
    },
    zAxis3D: {
      type: "value",
      name: "IAQI (分指数)",
      axisLine: { lineStyle: { color: "#999" } },
    },
    grid3D: {
      boxWidth: 100,
      boxDepth: 120, // 城市多一点，深度拉大
      boxHeight: 80,
      viewControl: {
        beta: 30,
        alpha: 20,
        distance: 240,
        autoRotate: false, // 禁止自动旋转，方便看清
      },
      light: {
        main: { intensity: 1.2, shadow: true },
        ambient: { intensity: 0.3 },
      },
    },
    series: [
      {
        type: "bar3D",
        data: bar3DData,
        shading: "color", // 使用数据自身的颜色
        barSize: 0.8, // 相对宽度
        animation: true,
        animationDurationUpdate: 500,
      },
    ],
  };

  surface3DChart.setOption(option, true);
};

// Helper: 获取颜色 (简单版)
const getAQIColor = (val) => {
  if (val <= 50) return "#00E400";
  if (val <= 100) return "#FFFF00";
  if (val <= 150) return "#FF7E00";
  if (val <= 200) return "#FF0000";
  if (val <= 300) return "#99004C";
  return "#7E0023";
};

// 2. 渲染多维雷达图
const renderRadar = () => {
  if (!radarRef.value) return;
  if (!radarChart) {
    radarChart = echarts.init(radarRef.value);
  }

  const actualAvgs = pollutants.map((p) => {
    const vals = props.actualData.map((d) => d[p]).filter((v) => v != null);
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  });

  const predAvgs = pollutants.map((p) => {
    const vals = props.predData.map((d) => d[p]).filter((v) => v != null);
    return vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  });

  // 归一化到0-100
  const maxVals = pollutants.map((p, i) =>
    Math.max(actualAvgs[i], predAvgs[i])
  );
  const normalizedActual = actualAvgs.map((v, i) =>
    maxVals[i] > 0 ? (v / maxVals[i]) * 100 : 0
  );
  const normalizedPred = predAvgs.map((v, i) =>
    maxVals[i] > 0 ? (v / maxVals[i]) * 100 : 0
  );

  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    legend: {
      data: ["预测", "实际"],
      bottom: 10,
      textStyle: { color: "#333" },
    },
    radar: {
      indicator: pollutants.map((p) => ({ name: p.toUpperCase(), max: 100 })),
      shape: "polygon",
      radius: "60%",
      splitArea: {
        areaStyle: {
          color: ["rgba(255, 255, 255, 0.1)", "rgba(255, 255, 255, 0.3)"],
        },
      },
      axisLine: { lineStyle: { color: "rgba(0, 0, 0, 0.2)" } },
      splitLine: { lineStyle: { color: "rgba(0, 0, 0, 0.2)" } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: normalizedPred,
            name: "预测",
            areaStyle: { color: "rgba(52, 152, 219, 0.3)" },
            lineStyle: { color: "#3498db", width: 2 },
            itemStyle: { color: "#3498db" },
          },
          {
            value: normalizedActual,
            name: "实际",
            areaStyle: { color: "rgba(230, 126, 34, 0.3)" },
            lineStyle: { color: "#e67e22", width: 2 },
            itemStyle: { color: "#e67e22" },
          },
        ],
      },
    ],
  };

  radarChart.setOption(option);
};

// 3. 渲染热力矩阵
const renderHeatmap = () => {
  if (!heatmapRef.value) return;
  if (!heatmapChart) {
    heatmapChart = echarts.init(heatmapRef.value);
  }

  const data = heatmapMode.value === "pred" ? props.predData : props.actualData;
  const corrMatrix = calculateCorrelation(data, pollutants);

  const heatmapData = [];
  pollutants.forEach((row, i) => {
    pollutants.forEach((col, j) => {
      heatmapData.push([j, i, corrMatrix[i][j].toFixed(2)]);
    });
  });

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      position: "top",
      formatter: (params) => {
        return `${pollutants[params.value[1]].toUpperCase()} ↔ ${pollutants[
          params.value[0]
        ].toUpperCase()}<br/>相关系数: ${params.value[2]}`;
      },
    },
    grid: {
      left: "15%",
      right: "10%",
      top: "10%",
      bottom: "15%",
    },
    xAxis: {
      type: "category",
      data: pollutants.map((p) => p.toUpperCase()),
      splitArea: { show: true },
      axisLabel: { color: "#333" },
    },
    yAxis: {
      type: "category",
      data: pollutants.map((p) => p.toUpperCase()),
      splitArea: { show: true },
      axisLabel: { color: "#333" },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: "0%",
      inRange: {
        color: [
          "#313695",
          "#4575b4",
          "#74add1",
          "#f7f7f7",
          "#fdae61",
          "#f46d43",
          "#d73027",
        ],
      },
      textStyle: { color: "#333" },
    },
    series: [
      {
        type: "heatmap",
        data: heatmapData,
        label: {
          show: true,
          color: "#333",
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0, 0, 0, 0.5)",
          },
        },
      },
    ],
  };

  heatmapChart.setOption(option);
};

// 4. 渲染AQI等级分布
const renderAQIDist = () => {
  if (!aqiDistRef.value) return;
  if (!aqiDistChart) {
    aqiDistChart = echarts.init(aqiDistRef.value);
  }

  const levels = ["优", "良", "轻度", "中度", "重度", "严重"];
  const actualLevels = { 优: 0, 良: 0, 轻度: 0, 中度: 0, 重度: 0, 严重: 0 };
  const predLevels = { 优: 0, 良: 0, 轻度: 0, 中度: 0, 重度: 0, 严重: 0 };

  props.actualData.forEach((d) => {
    const aqi = calculateAQI(d.pm25, d.pm10, d.so2, d.no2, d.co, d.o3);
    actualLevels[getAQILevel(aqi)]++;
  });

  props.predData.forEach((d) => {
    const aqi = calculateAQI(d.pm25, d.pm10, d.so2, d.no2, d.co, d.o3);
    predLevels[getAQILevel(aqi)]++;
  });

  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["实际", "预测"],
      top: 10,
      textStyle: { color: "#333" },
    },
    grid: {
      left: "10%",
      right: "10%",
      top: "20%",
      bottom: "15%",
    },
    xAxis: {
      type: "category",
      data: levels,
      axisLabel: { color: "#666" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#666" },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.06)" } },
    },
    series: [
      {
        name: "实际",
        type: "bar",
        data: levels.map((l) => actualLevels[l]),
        itemStyle: { color: "#e67e22" },
      },
      {
        name: "预测",
        type: "bar",
        data: levels.map((l) => predLevels[l]),
        itemStyle: { color: "#3498db" },
      },
    ],
  };

  aqiDistChart.setOption(option);
};

// 5. 渲染平行坐标系
const renderParallel = () => {
  if (!parallelRef.value) return;
  if (!parallelChart) {
    parallelChart = echarts.init(parallelRef.value);
  }

  const sampleSize = 200;
  const sampledPred = props.predData.slice(0, sampleSize);
  const sampledActual = props.actualData.slice(0, sampleSize);

  const parallelData = sampledPred.map((p, idx) => {
    const a = sampledActual[idx] || {};
    return [
      p.pm25 || 0,
      p.pm10 || 0,
      p.so2 || 0,
      p.no2 || 0,
      p.co || 0,
      p.o3 || 0,
      calculateAQI(p.pm25, p.pm10, p.so2, p.no2, p.co, p.o3),
    ];
  });

  const option = {
    backgroundColor: "transparent",
    parallelAxis: [
      { dim: 0, name: "PM2.5" },
      { dim: 1, name: "PM10" },
      { dim: 2, name: "SO₂" },
      { dim: 3, name: "NO₂" },
      { dim: 4, name: "CO" },
      { dim: 5, name: "O₃" },
      { dim: 6, name: "AQI" },
    ],
    parallel: {
      left: "5%",
      right: "10%",
      top: "10%",
      bottom: "10%",
      parallelAxisDefault: {
        type: "value",
        nameTextStyle: { color: "#333" },
        axisLine: { lineStyle: { color: "#ccc" } },
        axisTick: { lineStyle: { color: "#ccc" } },
        axisLabel: { color: "#666" },
        splitLine: { show: false },
      },
    },
    visualMap: {
      show: true,
      min: 0,
      max: 300,
      dimension: 6,
      inRange: {
        color: ["#50a3ba", "#eac736", "#d94e5d"],
      },
      textStyle: { color: "#333" },
    },
    series: [
      {
        type: "parallel",
        smooth: 0.3, // Optimization: Curve smoothing
        lineStyle: {
          width: 1.5,
          opacity: 0.3, // Optimization: Lower opacity for density
        },
        // Optimization: Blend mode for better density visualization (if supported, otherwise opacity handles it)
        data: parallelData,
      },
    ],
  };

  parallelChart.setOption(option);
};

// 6. 渲染AQI预警时间轴
const renderTimeline = () => {
  if (!timelineRef.value) {
    console.log("[Timeline] timelineRef 为空");
    return;
  }
  if (!timelineChart) {
    timelineChart = echarts.init(timelineRef.value);
  }

  console.log(
    "[Timeline] 渲染时间轴，predData长度:",
    props.predData.length,
    "actualData长度:",
    props.actualData.length
  );

  const AQI_THRESHOLD = 150;

  // 按日期聚合数据，计算每天的全国平均AQI
  const dateMap = new Map();
  props.predData.forEach((p, idx) => {
    const date = p.date || `Day ${idx + 1}`;
    if (!dateMap.has(date)) {
      dateMap.set(date, { predList: [], actualList: [] });
    }
    dateMap.get(date).predList.push(p);
  });

  props.actualData.forEach((a, idx) => {
    const date = a.date || props.predData[idx]?.date || `Day ${idx + 1}`;
    if (dateMap.has(date)) {
      dateMap.get(date).actualList.push(a);
    }
  });

  const timelineData = Array.from(dateMap.entries())
    .map(([date, { predList, actualList }]) => {
      // 计算该日期所有城市的平均AQI
      const predAqis = predList
        .map((p) => calculateAQI(p.pm25, p.pm10, p.so2, p.no2, p.co, p.o3))
        .filter((v) => !isNaN(v));
      const actualAqis = actualList
        .map((a) => calculateAQI(a.pm25, a.pm10, a.so2, a.no2, a.co, a.o3))
        .filter((v) => !isNaN(v));

      const aqi =
        predAqis.length > 0
          ? predAqis.reduce((sum, v) => sum + v, 0) / predAqis.length
          : 0;
      const actualAqi =
        actualAqis.length > 0
          ? actualAqis.reduce((sum, v) => sum + v, 0) / actualAqis.length
          : 0;

      let level = "优";
      let color = "#00e400";
      if (aqi >= 300) {
        level = "严重污染";
        color = "#7e0023";
      } else if (aqi >= 200) {
        level = "重度污染";
        color = "#8f3f97";
      } else if (aqi >= 150) {
        level = "中度污染";
        color = "#ff0000";
      } else if (aqi >= 100) {
        level = "轻度污染";
        color = "#ff7e00";
      } else if (aqi >= 50) {
        level = "良";
        color = "#ffff00";
      }

      return {
        date,
        aqi,
        actualAqi,
        level,
        color,
        isWarning: aqi >= AQI_THRESHOLD,
        cityCount: predList.length,
      };
    })
    .sort((a, b) => a.date.localeCompare(b.date));

  const xAxisData = timelineData.map((d) => d.date);
  const seriesData = timelineData.map((d, idx) => ({
    value: d.aqi,
    itemStyle: {
      color: d.color,
      borderColor: d.isWarning ? "#ff0000" : "#fff",
      borderWidth: d.isWarning ? 2 : 0,
    },
    emphasis: {
      itemStyle: {
        borderWidth: 3,
        shadowBlur: 10,
        shadowColor: d.color,
      },
    },
    date: d.date,
    level: d.level,
    actualAqi: d.actualAqi,
    levelColor: d.color, // 保存颜色用于tooltip显示
  }));

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params) => {
        const p = params[0];
        const data = p.data;
        return `
          <div style="padding: 8px;">
            <div style="font-weight: bold; margin-bottom: 4px;">${
              data.date
            }</div>
            <div style="color: ${data.levelColor};">污染等级: ${
          data.level
        }</div>
            <div>全国平均AQI: <strong>${data.value.toFixed(0)}</strong></div>
            <div>实际平均: <strong>${data.actualAqi.toFixed(0)}</strong></div>
            <div style="font-size: 11px; color: #666;">城市数: ${
              data.cityCount
            }</div>
            ${
              data.value >= 150
                ? '<div style="color: #ff0000; font-weight: bold;">⚠️ 超过预警阈值</div>'
                : ""
            }
            <div style="margin-top: 4px; font-size: 11px; color: #999;">点击查看详情</div>
          </div>
        `;
      },
    },
    grid: {
      left: "3%",
      right: "3%",
      top: "15%",
      bottom: "10%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: xAxisData,
      axisLabel: {
        color: "#666",
        interval: Math.floor(xAxisData.length / 12),
        rotate: 45,
      },
      axisLine: { lineStyle: { color: "#ddd" } },
    },
    yAxis: {
      type: "value",
      name: "AQI",
      axisLabel: { color: "#666" },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.06)" } },
    },
    series: [
      {
        type: "bar",
        data: seriesData,
        barMaxWidth: 8,
        markLine: {
          silent: true,
          symbol: "none",
          lineStyle: {
            color: "#ff0000",
            type: "dashed",
            width: 2,
          },
          label: {
            position: "end",
            formatter: "预警阈值 150",
            color: "#ff0000",
          },
          data: [{ yAxis: AQI_THRESHOLD }],
        },
      },
    ],
  };

  timelineChart.setOption(option);

  // 添加点击事件
  timelineChart.off("click");
  timelineChart.on("click", (params) => {
    if (params.data && params.data.date) {
      selectedDate.value = params.data.date;
      emit("date-select", params.data.date);
    }
  });
};

// 7. 渲染误差箱线图（增强版：标注重污染日）
const renderErrorBox = () => {
  if (!errorBoxRef.value) return;
  if (!errorBoxChart) {
    errorBoxChart = echarts.init(errorBoxRef.value);
  }

  const percentile = (arr, ratio) => {
    if (!arr.length) return 0;
    const idx = (arr.length - 1) * ratio;
    const lower = Math.floor(idx);
    const upper = Math.ceil(idx);
    if (lower === upper) return arr[lower];
    return arr[lower] + (arr[upper] - arr[lower]) * (idx - lower);
  };

  const AQI_THRESHOLD = 150;

  // 构建实际数据的索引映射 (city-date -> data)
  const actualMap = new Map();
  props.actualData.forEach((item) => {
    const key = `${item.city}-${item.date}`;
    actualMap.set(key, item);
  });

  const errors = pollutants.map((p) => {
    const errs = [];
    const heavyPollutionErrs = [];

    // 遍历预测数据，找到对应的实际数据进行匹配
    props.predData.forEach((predItem) => {
      const key = `${predItem.city}-${predItem.date}`;
      const actualItem = actualMap.get(key);

      if (actualItem) {
        const pred = predItem[p];
        const actual = actualItem[p];

        if (pred != null && actual != null) {
          const err = Math.abs(pred - actual);
          errs.push(err);

          // 检查是否为重污染日
          const actualAqi = calculateAQI(
            actualItem.pm25,
            actualItem.pm10,
            actualItem.so2,
            actualItem.no2,
            actualItem.co,
            actualItem.o3
          );
          if (actualAqi >= AQI_THRESHOLD) {
            heavyPollutionErrs.push(err);
          }
        }
      }
    });

    return { errs: errs.sort((a, b) => a - b), heavyErrs: heavyPollutionErrs };
  });

  // 调试信息
  console.log("ErrorBox Debug:", {
    predDataLength: props.predData.length,
    actualDataLength: props.actualData.length,
    samplePred: props.predData[0],
    sampleActual: props.actualData[0],
    pm25Errors: errors[0].errs.slice(0, 10),
    matchCount: errors[0].errs.length,
  });

  const boxData = errors.map(({ errs: arr }) => {
    if (arr.length === 0) return [0, 0, 0, 0, 0];
    const q1 = percentile(arr, 0.25);
    const median = percentile(arr, 0.5);
    const q3 = percentile(arr, 0.75);
    const iqr = q3 - q1;
    const lowerFence = Math.max(q1 - 1.5 * iqr, 0);
    const upperFence = q3 + 1.5 * iqr;
    const minVal = arr.find((v) => v >= lowerFence) ?? arr[0];
    const maxVal =
      [...arr].reverse().find((v) => v <= upperFence) ?? arr[arr.length - 1];
    return [minVal, q1, median, q3, maxVal];
  });

  // 计算重污染日的平均误差（用于标注）
  const heavyPollutionMarks = errors
    .map(({ heavyErrs }, idx) => {
      if (heavyErrs.length === 0) return null;
      const avgErr = heavyErrs.reduce((a, b) => a + b, 0) / heavyErrs.length;
      return [
        idx, // x轴位置（污染物索引）
        avgErr, // y轴位置（平均误差值）
        heavyErrs.length, // 额外信息：样本数
      ];
    })
    .filter(Boolean);

  const option = {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (params) => {
        if (params.componentSubType === "boxplot") {
          const [min, q1, median, q3, max] = params.data;
          return `
            <div style="padding: 8px;">
              <div style="font-weight: bold;">${params.name}</div>
              <div>最小值: ${min.toFixed(2)}</div>
              <div>Q1: ${q1.toFixed(2)}</div>
              <div>中位数: ${median.toFixed(2)}</div>
              <div>Q3: ${q3.toFixed(2)}</div>
              <div>最大值: ${max.toFixed(2)}</div>
              <div style="margin-top: 4px; color: #ff0000;">红点=重污染日平均误差</div>
            </div>
          `;
        }
        if (params.componentSubType === "scatter") {
          const [x, y, count] = params.data;
          return `
            <div style="padding: 8px;">
              <div style="font-weight: bold; color: #ff0000;">⚠️ 重污染日误差</div>
              <div>${pollutants[x].toUpperCase()}</div>
              <div>平均误差: <strong>${y.toFixed(2)}</strong></div>
              <div>样本数: ${count} 天</div>
              <div style="margin-top: 4px; font-size: 11px; color: #999;">点击查看详情</div>
            </div>
          `;
        }
        return params.name;
      },
    },
    grid: {
      left: "10%",
      right: "10%",
      top: "10%",
      bottom: "15%",
    },
    xAxis: {
      type: "category",
      data: pollutants.map((p) => p.toUpperCase()),
      axisLabel: { color: "#666" },
    },
    yAxis: {
      type: "value",
      name: "预测绝对误差",
      axisLabel: { color: "#666" },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.06)" } },
    },
    series: [
      {
        type: "boxplot",
        data: boxData,
        itemStyle: {
          color: "#3498db",
          borderColor: "#2980b9",
        },
      },
      {
        name: "重污染日误差",
        type: "scatter",
        data: heavyPollutionMarks,
        symbolSize: 12,
        itemStyle: {
          color: "#ff0000",
          borderColor: "#fff",
          borderWidth: 2,
        },
        label: {
          show: true,
          position: "top",
          formatter: (params) => params.data[1].toFixed(1),
          color: "#ff0000",
          fontSize: 10,
          fontWeight: "bold",
        },
        z: 10,
      },
    ],
  };

  errorBoxChart.setOption(option);

  // 添加点击事件
  errorBoxChart.off("click");
  errorBoxChart.on("click", (params) => {
    if (params.componentSubType === "scatter" && params.data) {
      const [x, y] = params.data;
      // 点击重污染日标记，可以触发详细分析
      emit("error-detail", {
        pollutant: pollutants[x],
        error: y,
      });
    }
  });
};

// 初始化和监听
onMounted(async () => {
  // Load GeoJSON
  try {
    const chinaRes = await fetch("/china.json");
    const chinaGeo = await chinaRes.json();
    echarts.registerMap("china", chinaGeo);

    const regionRes = await fetch("/region.json");
    const regions = await regionRes.json();
    regions.forEach((r) => {
      // Use standard city name as key
      if (r.city && r.longitude && r.latitude) {
        cityGeoMap.set(r.city, [Number(r.longitude), Number(r.latitude)]);
      }
    });
  } catch (e) {
    console.error("Failed to load geo data", e);
  }

  nextTick(() => {
    initCharts(); // Helper to re-run renders
  });

  window.addEventListener("resize", handleResize);
});

const initCharts = () => {
  render3DSurface();
  renderRadar();
  renderHeatmap();
  renderAQIDist();
  renderParallel();
  renderTimeline();
  renderErrorBox();
};

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  if (surface3DChart) surface3DChart.dispose();
  if (radarChart) radarChart.dispose();
  if (heatmapChart) heatmapChart.dispose();
  if (aqiDistChart) aqiDistChart.dispose();
  if (parallelChart) parallelChart.dispose();
  if (timelineChart) timelineChart.dispose();
  if (errorBoxChart) errorBoxChart.dispose();
});

const handleResize = () => {
  surface3DChart?.resize();
  radarChart?.resize();
  heatmapChart?.resize();
  aqiDistChart?.resize();
  parallelChart?.resize();
  timelineChart?.resize();
  errorBoxChart?.resize();
};

watch(
  () => props.actualData,
  () => {
    nextTick(() => {
      renderRadar();
      renderHeatmap();
      renderAQIDist();
      renderParallel();
      renderTimeline();
      renderErrorBox();
    });
  },
  { deep: true }
);

watch(
  () => props.predData,
  () => {
    nextTick(() => {
      render3DSurface();
      renderRadar();
      renderHeatmap();
      renderAQIDist();
      renderParallel();
      renderTimeline();
      renderErrorBox();
    });
  },
  { deep: true }
);

watch(surface3DMetric, render3DSurface);
watch(heatmapMode, renderHeatmap);
</script>

<style scoped>
.forecast-overview {
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.overview-header {
  margin-bottom: 30px;
}

.overview-title {
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 28px;
  color: var(--c-black);
  font-weight: 600;
}

.badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 16px;
}

.subtitle {
  font-size: 16px;
  color: #666;
  font-weight: 400;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 20px;
}

.overview-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.overview-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.overview-card.xlarge {
  grid-column: span 12;
}

.overview-card.large {
  grid-column: span 8;
}

.overview-card.medium {
  grid-column: span 4;
}

.overview-card.small {
  grid-column: span 4;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 2px solid #eee;
}

.card-header h3 {
  font-size: 18px;
  color: var(--c-black);
  font-weight: 600;
  margin: 0;
}

.card-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.mini-select {
  padding: 5px 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  color: var(--c-black);
  font-size: 12px;
  cursor: pointer;
  outline: none;
}

.toggle-btn {
  padding: 5px 12px;
  border: 1px solid #ddd;
  background: white;
  color: #666;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s;
}

.toggle-btn.active {
  background: #3498db;
  color: white;
  border-color: #3498db;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.chart-3d,
.chart-radar,
.chart-heatmap,
.chart-dist,
.chart-parallel,
.chart-timeline,
.chart-box {
  width: 100%;
  height: 400px;
}

.chart-parallel,
.chart-timeline {
  height: 300px;
}

.threshold-label {
  font-size: 12px;
  color: #ff0000;
  font-weight: 600;
  padding: 4px 8px;
  background: rgba(255, 0, 0, 0.1);
  border-radius: 4px;
}

.chart-desc {
  margin-top: 10px;
  font-size: 12px;
  color: #999;
  text-align: center;
  font-style: italic;
}

@media (max-width: 1400px) {
  .overview-card.large {
    grid-column: span 12;
  }
  .overview-card.medium {
    grid-column: span 6;
  }
}

@media (max-width: 900px) {
  .overview-card.medium,
  .overview-card.small {
    grid-column: span 12;
  }
}
</style>
