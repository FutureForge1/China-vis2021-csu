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
  showValue: { type: Boolean, default: false },
  title: { type: String, default: "地图" },
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

// 1. 定义白-橙-红渐变色带
const WIND_GRADIENT = [
  "#fff7ec", "#fee8c8", "#fdd49e", "#fdbb84", 
  "#fc8d59", "#ef6548", "#d7301f", "#b30000", "#7f0000"
];

// 2. 颜色插值函数
function getGradientColor(value, min, max) {
  if (max <= min) return WIND_GRADIENT[0];
  let t = (value - min) / (max - min);
  t = Math.max(0, Math.min(1, t)); // 限制在 0-1
  const index = Math.floor(t * (WIND_GRADIENT.length - 1));
  return WIND_GRADIENT[index];
}

// 将数据相关的计算分离，避免地图拖拽时重新计算
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
  const palette =
    props.mode === "weather"
      ? ["#c7d2fe", "#93c5fd", "#60a5fa", "#3b82f6", "#1d4ed8"]
      : ["#4ade80", "#facc15", "#f97316", "#ef4444"];

  return { min, max, palette, useScatter, useWind, useFlow, useHeatmap };
});

// 风速颜色映射函数
// 风速颜色映射函数（统一红色系，速度越大颜色越深）
const getWindSpeedColor = (speed, minSpeed, maxSpeed) => {
  if (maxSpeed === minSpeed) return "#b91c1c";
  const normalized = Math.max(0, Math.min(1, (speed - minSpeed) / (maxSpeed - minSpeed)));
  const colors = ["#fee2e2", "#fecaca", "#fca5a5", "#f87171", "#ef4444", "#dc2626", "#b91c1c"];
  const index = Math.floor(normalized * (colors.length - 1));
  return colors[Math.min(index, colors.length - 1)];
};

// 风速线段宽度映射函数（固定宽度）
const getWindSpeedWidth = (speed, minSpeed, maxSpeed) => {
  return 1.5; // 所有线段固定宽度
};

// 基础地图配置，包含拖拽等设置
const baseGeoConfig = {
  map: props.mapName,
  emphasis: { label: { show: false } },
  label: {
    show: false, // 默认不显示省名，防止重叠
    color: "#666"
  },
  // 移除silent，允许tooltip显示省份名称
  // 增强边界线样式，让边界线更明显，填充完全透明
  itemStyle: {
    borderColor: "#4a5568", // 更深的边界线颜色
    borderWidth: 1.5, // 增加边界线宽度
    areaColor: "transparent" // 完全透明，只显示边界线
  }
};

const chartOption = computed(() => {
  const { min, max, palette, useScatter, useWind, useFlow, useHeatmap } = dataStats.value;

  return {
    backgroundColor: "transparent",
    // 鼠标悬浮时显示省份名称
    tooltip: {
      show: true,
      formatter: function(params) {
        // 修改 Tooltip 逻辑
        if (props.showValue && !isNaN(params.value)) {
          // 月均视图：显示 名称 + 指标名 + 数值
          return `${params.name}<br/>${props.metric}: ${params.value}`;
        }
        // 日均视图（默认）：只显示省名
        return params.name;
      }
    },
    // 禁用悬停高亮
    hoverLayerThreshold: Infinity,

    geo: useScatter || useWind || useFlow || useHeatmap
      ? {
          ...baseGeoConfig,
          // 对于散点图和风场数据，禁用缩放和平移
          roam: false,
          // 【新增修改点 2】：确保 Geo 组件完全透明，只显示边界线
          itemStyle: {
            areaColor: "transparent", // 完全透明，只显示边界线
            borderColor: "#4a5568",
            borderWidth: 1.5
          },
          // 确保地图边界线在最上层
          // 【新增】手动配置选中区域的样式：仅加粗边框，不改变透明度，不触发高亮淡出
          regions: props.selectedName ? [
            {
              name: props.selectedName,
              itemStyle: {
                borderWidth: 3,             // 显著加粗
                borderColor: '#1f2937',     // 加深颜色 (或者用主题色 '#2f7e57')
                shadowColor: 'rgba(0, 0, 0, 0.5)', 
                shadowBlur: 10,
                areaColor: "transparent"    // 保持透明，不遮挡下方的散点数据
              },
              // 强制高亮状态下也保持该样式，防止鼠标滑过时样式跳变
              emphasis: {
                itemStyle: {
                  borderWidth: 4,
                  borderColor: '#1f2937',
                  areaColor: "transparent"
                }
              }
            }
            ] : [],
          zlevel: 10
        }
      : undefined,

    visualMap: useWind || useFlow
      ? undefined
      : useHeatmap
      ? {
          min,
          max: max === min ? min + 1 : max,
          calculable: true,
          inRange: { color: ["#fef3c7", "#fbbf24", "#ef4444", "#7f1d1d"] },
          right: 10,
          bottom: 20,
        }
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
      // 主要数据系列（散点图、热力图、地图或透明地图）
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
            // 禁用悬停高亮
            emphasis: { focus: 'none' },
            silent: true, // 禁用鼠标事件
            // 禁用progressive渲染，数据加载完后一次性渲染所有点
            progressive: false, // 禁用逐步渲染
            // 数据点在地图下面
            zlevel: 1
          }
        : useHeatmap
        ? {
            name: props.metric,
            type: "heatmap",
            coordinateSystem: "geo",
            data: props.heatmap,
            pointSize: 10,
            blurSize: 25,
            // 禁用悬停高亮
            emphasis: { focus: 'none' },
            silent: true, // 禁用鼠标事件
            // 禁用progressive渲染，数据加载完后一次性渲染所有点
            progressive: false, // 禁用逐步渲染
            // 数据点在地图下面
            zlevel: 1,
          }
        : useWind || useFlow // 风场或流场模式
        ? {
            // 返回一个透明对象，因为底图已经由 geo 组件负责绘制了
            // 这样就避免了"双重地图"的问题
            type: "map",
            map: "china",
            silent: true,
            itemStyle: { opacity: 0 }, // 完全隐藏这个多余的系列地图
            zlevel: 1 // 数据点在地图下面
          }
        : {
            // 普通地图模式：显示数据和处理高亮
            name: props.metric,
            type: "map",
            map: props.mapName,
            roam: true,
            emphasis: { label: { show: false }, focus: 'none' },
            data: props.data.map(item => ({
              ...item,
              itemStyle: {
                ...item.itemStyle,
                // 如果是选中的区域，显示半透明的蓝色背景
                areaColor: item.name === props.selectedName
                  ? 'rgba(59, 130, 246, 0.3)' // 蓝色半透明
                  : "transparent", // 其他区域透明
                borderColor: item.name === props.selectedName
                  ? "#3b82f6" // 蓝色边框
                  : "#4a5568", // 默认边框
                borderWidth: item.name === props.selectedName ? 2 : 1.5
              }
            })),
            selectedMode: "single",
            // 允许鼠标悬浮显示tooltip，但禁用其他交互
            // 确保地图边界线在最上层，覆盖数据点
            zlevel: 10
          },

      // 高亮地图系列：仅在非散点图模式下显示选中区域高亮
      ...(!useScatter && props.selectedName ? [{
        name: "highlight",
        type: "map",
        map: props.mapName,
        roam: false,
        silent: true, // 不响应鼠标事件
        data: [{
          name: props.selectedName,
          value: 1,
          itemStyle: {
            areaColor: 'rgba(59, 130, 246, 0.3)', // 蓝色半透明
            borderColor: "#3b82f6", // 蓝色边框
            borderWidth: 2
          }
        }],
        zlevel: 15 // 在最上层
      }] : []),

      ...(props.wind && props.wind.length
        ? [
            {
              type: "lines",
              coordinateSystem: "geo",
              // 修正：在 data 映射时直接计算好每一条线的 lineStyle
              data: props.wind.map((w) => {
                const speed = w.value ?? w.speed ?? 0;
                const { min, max } = dataStats.value;
                return {
                  coords: w.coords,
                  value: speed,
                  lineStyle: {
                    color: getWindSpeedColor(speed, min, max),
                    width: getWindSpeedWidth(speed, min, max),
                    opacity: 0.9,
                    cap: "round"
                  }
                };
              }),
              // 移除原本无效的 lineStyle 回调配置
              blendMode: "normal",
              zlevel: 1, // 数据点在地图下面
              emphasis: { focus: 'none' },
              silent: true,
              // 禁用progressive渲染，数据加载完后一次性渲染所有线条
              progressive: false,
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
  // local pretty-printed geojson (provided by user)
  "/中国_市.pretty.json",
  "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
];

async function loadMap() {
  console.log('[MapPanel] loadMap: trying MAP_PATHS', MAP_PATHS);
  for (const path of MAP_PATHS) {
    try {
      console.log('[MapPanel] loadMap: fetch', path);
      const res = await fetch(path);
      console.log('[MapPanel] loadMap: fetched', path, 'ok=', res.ok, 'status=', res.status);
      if (!res.ok) continue;
      const geo = await res.json();
      console.log('[MapPanel] loadMap: registerMap from', path);
      registerMap("china", geo);
      mapReady.value = true;
      console.log('[MapPanel] loadMap: registerMap success');
      return;
    } catch (err) {
      console.warn('[MapPanel] loadMap: failed to load', path, err);
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
