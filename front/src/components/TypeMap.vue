<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>城市污染类型地图</h3>
        <span class="sub">按主导污染物 · 柔和填色</span>
      </div>
      <div class="legend">
        <span v-for="item in legendItems" :key="item.label" class="legend-chip">
          <span class="dot" :style="{ background: item.color }"></span>
          {{ item.label }}
        </span>
      </div>
    </div>
    <div class="chart" v-if="mapReady">
      <VChart :option="option" autoresize />
    </div>
    <div v-else class="placeholder">地图加载中，请检查 /public/china.json</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { registerMap } from "echarts/core";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name, type, primary}]
});

const colors = {
  标准型: "#a3d9c9",
  偏二次型: "#9cb8f5",
  偏燃煤型: "#f6c173",
  偏交通型: "#6ccdc0",
  偏燃烧型: "#c7a0ff",
  偏颗粒物型: "#f69b9b",
  未知: "#e5e7eb",
};

const mapReady = ref(false);

const legendItems = computed(() =>
  Object.entries(colors).map(([label, color]) => ({ label, color }))
);

const option = computed(() => {
  const data = props.items.map((d) => {
    const type = d.type || "未知";
    const color = colors[type] || "#e5e7eb";
    return {
      name: d.name,
      value: 1,
      type,
      primary: (d.primary || "-").toUpperCase?.() || "-",
      itemStyle: {
        areaColor: color,
        color,
        borderColor: "#d1d5db",
      },
    };
  });

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(21, 30, 47, 0.85)",
      borderColor: "rgba(255,255,255,0.08)",
      textStyle: { color: "#e5ecf4", fontSize: 12 },
      formatter: (p) =>
        `${p.name}<br/>类型：${p.data?.type || "-"}<br/>主导：${p.data?.primary || "-"}`,
    },
    series: [
      {
        type: "map",
        map: "china",
        data,
        roam: true,
        emphasis: { label: { show: false } },
        zoom: 1.05,
        itemStyle: {
          borderColor: "rgba(31,41,55,0.16)",
          borderWidth: 1,
          shadowColor: "rgba(15, 23, 42, 0.12)",
          shadowBlur: 6,
        },
        emphasis: {
          itemStyle: {
            shadowColor: "rgba(0,0,0,0.18)",
            shadowBlur: 12,
            borderColor: "#0f172a",
          },
        },
      },
      {
        type: "map",
        map: "china",
        data: data.map((d) => ({
          ...d,
          itemStyle: {
            areaColor: d.itemStyle.areaColor,
            color: d.itemStyle.areaColor,
            borderColor: "rgba(31,41,55,0.12)",
          },
        })),
        roam: false,
        silent: true,
        zlevel: 1,
        itemStyle: { opacity: 0.95 },
      },
    ],
  };
});

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
      // try next
    }
  }
  console.warn("无法加载 china 地图，请将 GeoJSON 放到 public/china.json");
  mapReady.value = false;
}

onMounted(() => {
  loadMap();
});
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  height: 100%;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 6px;
  justify-content: space-between;
  flex-wrap: wrap;
}
.sub {
  color: #9eb1c7;
  font-size: 12px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.legend-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px solid rgba(15, 23, 42, 0.08);
  font-size: 12px;
  color: #1f2937;
}
.legend-chip .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.1);
}
.chart {
  flex: 1;
  min-height: 360px;
  position: relative;
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
