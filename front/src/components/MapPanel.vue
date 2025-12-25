<template>
  <div class="wrap">
    <div class="heading">
      <h2>{{ title }}</h2>
      <span class="badge">地图</span>
    </div>
    <div class="chart" v-if="mapReady">
      <VChart :option="chartOption" autoresize @click="handleClick" />
    </div>
    <div v-else class="placeholder">
      地图加载中，请确保 /public/china.json 可用。
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { registerMap } from "echarts/core";

const props = defineProps({
  data: { type: Array, default: () => [] },
  metric: { type: String, default: "pm25" },
  title: { type: String, default: "地图" },
  selectedName: { type: String, default: "" },
  mode: { type: String, default: "pollution" }, // pollution | weather
  scatter: { type: Array, default: () => [] }, // [{name, value, coord:[lon,lat]}]
  wind: { type: Array, default: () => [] }, // [{coords:[[lon,lat],[lon2,lat2]], speed}]
  flow: { type: Array, default: () => [] }, // densified lines for flow effect
});

const emit = defineEmits(["select"]);

const mapReady = ref(false);

const chartOption = computed(() => {
  const useScatter = props.scatter.length > 0;
  const useWind = props.wind.length > 0;
  const useFlow = props.flow.length > 0;
  const values = useFlow
    ? props.flow.map((d) => Number(d.speed ?? 0))
    : useWind
    ? props.wind.map((d) => Number(d.speed ?? 0))
    : useScatter
    ? props.scatter.map((d) => Number(d.value ?? 0))
    : props.data.map((d) => Number(d.value ?? 0));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 50;
  const palette =
    props.mode === "weather"
      ? ["#c7d2fe", "#93c5fd", "#60a5fa", "#3b82f6", "#1d4ed8"]
      : ["#4ade80", "#facc15", "#f97316", "#ef4444"];

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (p) =>
        `${p.name}<br/>${props.metric.toUpperCase()}: ${p.value ?? "-"}`,
    },
    geo: useScatter || useWind || useFlow
      ? {
          map: "china",
          roam: true,
          emphasis: { label: { show: false } },
        }
      : undefined,
    visualMap: useWind || useFlow
      ? undefined
      : {
          min,
          max: max === min ? min + 1 : max,
          text: ["高", "低"],
          calculable: true,
          right: 10,
          bottom: 20,
          inRange: {
            color: palette,
          },
        },
    series: [
      useScatter
        ? {
            name: props.metric,
            type: "scatter",
            coordinateSystem: "geo",
            data: props.scatter.map((s) => ({
              name: s.name,
              value: [s.coord[0], s.coord[1], s.value],
            })),
            symbolSize: (p) => {
              const val = Number(p[2]) || 0;
              if (max === min) return 4;
              const t = Math.max(0, Math.min(1, (val - min) / (max - min)));
              return 3 + t * 6;
            },
            encode: { value: 2 },
            itemStyle: { color: palette[palette.length - 1], opacity: 0.7 },
          }
        : {
            name: props.metric,
            type: "map",
            map: "china",
            roam: true,
            emphasis: { label: { show: false } },
            data: props.data,
            selectedMode: "single",
            selected: props.selectedName ? { [props.selectedName]: true } : {},
          },
      ...(props.wind && props.wind.length
        ? [
            {
              type: "lines",
              coordinateSystem: "geo",
              data: props.wind.map((w) => ({
                coords: w.coords,
                value: w.speed,
              })),
              lineStyle: {
                color: "#3b82f6",
                width: 1,
                opacity: 0.45,
                cap: "round",
              },
              effect: {
                show: true,
                symbol: "arrow",
                symbolSize: 5,
                color: "#2563eb",
                trailLength: 0.5,
                constantSpeed: 20,
              },
              blendMode: "lighter",
              zlevel: 3,
              large: true,
            },
          ]
        : []),
      ...(props.flow && props.flow.length
        ? [
            {
              type: "lines",
              coordinateSystem: "geo",
              data: props.flow.map((w) => ({
                coords: w.coords,
                value: w.speed,
              })),
              polyline: false,
              lineStyle: {
                color: "#60a5fa",
                width: 0.8,
                opacity: 0.35,
                curveness: 0.05,
              },
              effect: {
                show: true,
                period: 6,
                trailLength: 0.4,
                symbol: "none",
                color: "#93c5fd",
              },
              blendMode: "lighter",
              zlevel: 2,
              large: true,
            },
          ]
        : []),
    ],
  };
});

// Prefer Aliyun DataV Atlas (全国边界)，fallback to local copies.
const MAP_PATHS = [
  "/china.json",
  "/data/china.json",
  "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
];

async function loadMap() {
  for (const path of MAP_PATHS) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      const geo = await res.json();
      registerMap("china", geo);
      mapReady.value = true;
      return;
    } catch (err) {
      // try next path
    }
  }
  console.warn("无法加载 china 地图，请将 GeoJSON 放到 public/china.json");
  mapReady.value = false;
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

function handleClick(p) {
  if (p?.name) emit("select", p.name);
}
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: 100%;
}

.heading {
  display: flex;
  align-items: center;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 16px;
}

.badge {
  font-size: 12px;
  color: #9eb1c7;
  border: 1px solid #30363d;
  padding: 2px 6px;
  border-radius: 6px;
}

.chart {
  flex: 1;
  min-height: 360px;
}

.placeholder {
  flex: 1;
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #9eb1c7;
  border: 1px dashed #30363d;
  border-radius: 8px;
}
</style>
