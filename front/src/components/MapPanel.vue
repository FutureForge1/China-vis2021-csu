<template>
  <div class="wrap">
    <div class="heading">
      <h2>{{ title }}</h2>
      <div class="actions">
        <button
          v-if="currentLevel !== 'china'"
          class="back-btn"
          @click="goBack"
        >
          BACK TO NATIONAL
        </button>
        <span class="badge">{{
          currentLevel === "china" ? "NATIONAL" : currentProvince
        }}</span>
      </div>
    </div>
    <div class="chart" v-if="mapReady">
      <VChart
        ref="chartRef"
        :option="chartOption"
        autoresize
        @click="handleClick"
      />
    </div>
    <div v-else class="placeholder">LOADING MAP DATA...</div>
  </div>
</template>

<script setup>
import { registerMap } from "echarts/core";
import { computed, nextTick, onMounted, ref, watch } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] },
  metric: { type: String, default: "pm25" },
  showValue: { type: Boolean, default: false },
  title: { type: String, default: "MAP" },
  selectedName: { type: String, default: "" },
  mode: { type: String, default: "pollution" }, // pollution | weather
  scatter: { type: Array, default: () => [] }, // [{name, value, coord:[lon,lat]}]
  wind: { type: Array, default: () => [] }, // [{coords:[[lon,lat],[lon2,lat2]], speed}]
  flow: { type: Array, default: () => [] }, // densified lines for flow effect
  heatmap: { type: Array, default: () => [] }, // [[lon,lat,val]]
  mapName: { type: String, default: "china" },
});

const emit = defineEmits(["select"]);

const mapReady = ref(false);
const chartRef = ref(null);
const currentLevel = ref("china");
const currentProvince = ref("");
const provinceGeoJson = ref(null);

// Cache
let allCitiesGeoJson = null;
let cityToProvinceMap = new Map();

// Endfield Yellow Gradient
const WIND_GRADIENT = [
  "#ddd333",
  "#4d4500",
  "#665c00",
  "#807300",
  "#998a00",
  "#b2a100",
  "#ccb800",
  "#e6cf00",
  "#FFE600",
];

function getGradientColor(value, min, max) {
  if (max <= min) return WIND_GRADIENT[0];
  let t = (value - min) / (max - min);
  t = Math.max(0, Math.min(1, t));
  const index = Math.floor(t * (WIND_GRADIENT.length - 1));
  return WIND_GRADIENT[index];
}

const dataStats = computed(() => {
  const useScatter = props.scatter.length > 0;
  const useWind = props.wind.length > 0;
  const useFlow = props.flow.length > 0;
  const useHeatmap = props.heatmap.length > 0;
  const values = useHeatmap
    ? props.heatmap.map((d) => Number(d[2] ?? 0))
    : useFlow
    ? props.flow.map((d) => Number(d.speed ?? 0))
    : useWind
    ? props.wind.map((d) => Number(d.speed ?? 0))
    : useScatter
    ? props.scatter.map((d) => Number(d.value ?? 0))
    : props.data.map((d) => Number(d.value ?? 0));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 50;

  // Strict Endfield Palette (Yellow Scale)
  const palette = [
    "#1a1a1a",
    "#ddd333",
    "#665c00",
    "#998a00",
    "#ccb800",
    "#FFE600",
  ];

  return { min, max, palette, useScatter, useWind, useFlow, useHeatmap };
});

const getWindSpeedColor = (speed, minSpeed, maxSpeed) => {
  if (maxSpeed === minSpeed) return "#FFE600";
  const normalized = Math.max(
    0,
    Math.min(1, (speed - minSpeed) / (maxSpeed - minSpeed))
  );
  const colors = ["#ddd333", "#665c00", "#998a00", "#ccb800", "#FFE600"];
  const index = Math.floor(normalized * (colors.length - 1));
  return colors[Math.min(index, colors.length - 1)];
};

const getWindSpeedWidth = (speed, minSpeed, maxSpeed) => {
  return 1.5;
};

const baseGeoConfig = computed(() => {
  const isChina = currentLevel.value === "china";
  const config = {
    map: isChina ? "china" : "province_map",
    roam: true,
    scaleLimit: isChina ? { min: 1.2, max: 5 } : { min: 0.5, max: 20 },
    emphasis: {
      label: { show: true, color: "#000" },
      itemStyle: { areaColor: "#FFE600" }, // Yellow on hover
    },
    label: {
      show: true,
      color: "#666",
      fontSize: 10,
      textShadowColor: "#fff",
      textShadowBlur: 3,
    },
    itemStyle: {
      borderColor: "#ddd",
      borderWidth: 1,
      areaColor: "#1a1a1a", // Dark background
    },
  };

  if (isChina) {
    config.center = [105, 36];
    config.zoom = 1.5;
  }

  return config;
});

const chartOption = computed(() => {
  const { min, max, palette, useScatter, useWind, useFlow, useHeatmap } =
    dataStats.value;

  return {
    backgroundColor: "transparent",
    tooltip: {
      show: true,
      backgroundColor: "rgba(0, 0, 0, 0.9)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: { color: "#FFE600", fontFamily: "JetBrains Mono" },
      formatter: function (params) {
        if (params.data && !isNaN(params.data.value)) {
          const val = Array.isArray(params.data.value)
            ? params.data.value[2]
            : params.data.value;
          return `<div style="font-family: 'Oswald'; font-weight: bold; color: #0a0a0a;">${
            params.name
          }</div>
                  <div style="font-family: 'JetBrains Mono'; font-size: 12px; color: #FFE600;">
                    ${props.metric.toUpperCase()}: ${Number(val).toFixed(2)}
                  </div>`;
        }
        return params.name;
      },
    },
    geo: {
      ...baseGeoConfig.value,
      silent: false,
      zlevel: 10,
    },
    animation: false,
    visualMap:
      useWind || useFlow
        ? undefined
        : {
            min,
            max: max === min ? min + 1 : max,
            calculable: true,
            orient: "horizontal",
            left: "center",
            bottom: 10,
            inRange: { color: palette },
            textStyle: { color: "#666", fontFamily: "JetBrains Mono" },
          },
    series: [
      {
        name: props.metric,
        type: "map",
        geoIndex: 0,
        data: props.data.map((item) => ({
          name: item.name,
          value: item.value,
        })),
      },
      ...(useScatter && currentLevel.value === "china"
        ? [
            {
              type: "scatter",
              coordinateSystem: "geo",
              data: props.scatter.map((s) => ({
                name: s.name,
                value: [...s.coord, s.value],
              })),
              symbolSize: (val) => {
                const v = val[2];
                const t = (v - min) / (max - min || 1);
                return 4 + t * 8;
              },
              itemStyle: {
                color: palette[palette.length - 1],
                opacity: 0.8,
              },
              silent: true,
              zlevel: 11,
            },
          ]
        : []),
    ],
  };
});

async function loadMap() {
  try {
    const res = await fetch("/china.json");
    const geo = await res.json();
    registerMap("china", geo);

    const cityRes = await fetch("/china_city.json");
    allCitiesGeoJson = await cityRes.json();

    const regionRes = await fetch("/region.json");
    const regions = await regionRes.json();
    regions.forEach((r) => {
      cityToProvinceMap.set(r.city, r.province);
      cityToProvinceMap.set(r.county, r.province);
    });

    mapReady.value = true;
  } catch (err) {
    console.error("Failed to load maps:", err);
  }
}

function handleClick(params) {
  // 如果点击的是地图区域（componentType === 'geo' 或 'series' && seriesType === 'map'）
  if (
    params.componentType === "geo" ||
    (params.componentType === "series" && params.seriesType === "map")
  ) {
    if (currentLevel.value === "china" && params.name) {
      drillDown(params.name);
    }
    emit("select", params.name);
  }
}

async function drillDown(provinceName) {
  if (!allCitiesGeoJson) return;

  const provinceCities = allCitiesGeoJson.features.filter((f) => {
    const cityName = f.properties.name;
    return (
      cityToProvinceMap.get(cityName) === provinceName ||
      cityName.includes(provinceName.slice(0, 2))
    );
  });

  if (provinceCities.length === 0) return;

  const geoJson = {
    type: "FeatureCollection",
    features: provinceCities,
  };

  registerMap("province_map", geoJson);
  currentLevel.value = "province";
  currentProvince.value = provinceName;

  await nextTick();
}

function goBack() {
  currentLevel.value = "china";
  currentProvince.value = "";
  emit("select", ""); // Reset selection in parent
}

onMounted(() => {
  loadMap();
});

watch(
  () => props.data,
  () => {
    // reactive update handled by computed option
  }
);
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
  position: relative;
}

.heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

h2 {
  margin: 0;
  font-family: "Oswald", sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #0a0a0a;
  text-transform: uppercase;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn {
  background: transparent;
  border: 1px solid #ffe600;
  color: #ffe600;
  font-family: "JetBrains Mono", monospace;
  font-size: 10px;
  padding: 2px 8px;
  cursor: pointer;
  text-transform: uppercase;
}

.back-btn:hover {
  background: #ffe600;
  color: #000;
}

.badge {
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  color: #666;
  background: transparent;
  border: 1px solid #ddd;
  padding: 2px 8px;
  text-transform: uppercase;
}

.chart {
  flex: 1;
  min-height: 450px;
}

.placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-family: "JetBrains Mono", monospace;
}
</style>
