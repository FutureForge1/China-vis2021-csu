<template>
  <div class="forecast-overview">
    <div class="overview-header">
      <h2 class="overview-title">
        <span class="badge">多维预测概览</span>
        <span class="subtitle">{{ currentDate }} · {{ regionLabel }}</span>
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

      <!-- 误差分布箱线图 -->
      <div class="overview-card medium">
        <div class="card-header">
          <h3>📦 预测误差分布</h3>
        </div>
        <div class="chart-box" ref="errorBoxRef"></div>
        <p class="chart-desc">各污染物误差统计 · 箱线图展示</p>
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
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  actualData: { type: Array, default: () => [] }, // 实际数据
  predData: { type: Array, default: () => [] }, // 预测数据
  currentDate: { type: String, default: "" },
  region: { type: String, default: "all" },
  regionLabel: { type: String, default: "全国" },
});

// 控制状态
const surface3DMetric = ref("pm25");
const heatmapMode = ref("pred");
const showOutliers = ref(false);

// Chart refs
const surface3DRef = ref(null);
const radarRef = ref(null);
const heatmapRef = ref(null);
const aqiDistRef = ref(null);
const parallelRef = ref(null);
const errorBoxRef = ref(null);

// Chart instances
let surface3DChart = null;
let radarChart = null;
let heatmapChart = null;
let aqiDistChart = null;
let parallelChart = null;
let errorBoxChart = null;

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

  // 1. 获取当前日期数据
  const targetDate = props.currentDate;
  const daysData = props.predData.filter((d) => d.date === targetDate);

  if (daysData.length === 0) {
    surface3DChart.setOption(
      {
        title: {
          text: "当前日期无预测数据",
          left: "center",
          top: "center",
          textStyle: { color: "#999" },
        },
      },
      true
    );
    return;
  }

  // 2. 数据处理：计算每个城市的综合 AQI 并排序
  const cityStats = daysData.map((d) => {
    // 计算所有污染物的分指数 (IAQI)
    // 使用 calcIAQI 辅助函数
    const i_pm25 = calcIAQI(
      d.pm25,
      [0, 35, 75, 115, 150, 250, 350, 500],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_pm10 = calcIAQI(
      d.pm10,
      [0, 50, 150, 250, 350, 420, 500, 600],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_so2 = calcIAQI(
      d.so2,
      [0, 50, 150, 475, 800, 1600, 2100, 2620],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_no2 = calcIAQI(
      d.no2,
      [0, 40, 80, 180, 280, 565, 750, 940],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_co = calcIAQI(
      d.co,
      [0, 2, 4, 14, 24, 36, 48, 60],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );
    const i_o3 = calcIAQI(
      d.o3,
      [0, 160, 200, 300, 400, 800, 1000, 1200],
      [0, 50, 100, 150, 200, 300, 400, 500]
    );

    const maxIAQI = Math.max(i_pm25, i_pm10, i_so2, i_no2, i_co, i_o3);

    return {
      city: d.city,
      values: [i_pm25, i_pm10, i_so2, i_no2, i_co, i_o3],
      maxIAQI,
      raw: d,
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

// 6. 渲染误差箱线图
const renderErrorBox = () => {
  if (!errorBoxRef.value) return;
  if (!errorBoxChart) {
    errorBoxChart = echarts.init(errorBoxRef.value);
  }

  const errors = pollutants.map((p) => {
    const errs = [];
    for (
      let i = 0;
      i < Math.min(props.predData.length, props.actualData.length);
      i++
    ) {
      const pred = props.predData[i][p];
      const actual = props.actualData[i][p];
      if (pred != null && actual != null) {
        errs.push(Math.abs(pred - actual));
      }
    }
    return errs.sort((a, b) => a - b);
  });

  const boxData = errors.map((arr) => {
    if (arr.length === 0) return [0, 0, 0, 0, 0];
    const q1 = arr[Math.floor(arr.length * 0.25)];
    const median = arr[Math.floor(arr.length * 0.5)];
    const q3 = arr[Math.floor(arr.length * 0.75)];
    return [arr[0], q1, median, q3, arr[arr.length - 1]];
  });

  const option = {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
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
      name: "误差绝对值",
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
    ],
  };

  errorBoxChart.setOption(option);
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
  renderErrorBox();
};

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  if (surface3DChart) surface3DChart.dispose();
  if (radarChart) radarChart.dispose();
  if (heatmapChart) heatmapChart.dispose();
  if (aqiDistChart) aqiDistChart.dispose();
  if (parallelChart) parallelChart.dispose();
  if (errorBoxChart) errorBoxChart.dispose();
});

const handleResize = () => {
  surface3DChart?.resize();
  radarChart?.resize();
  heatmapChart?.resize();
  aqiDistChart?.resize();
  parallelChart?.resize();
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
.chart-box {
  width: 100%;
  height: 400px;
}

.chart-parallel {
  height: 300px;
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
