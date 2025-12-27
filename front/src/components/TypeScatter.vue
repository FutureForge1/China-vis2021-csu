<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染类型聚类散点</h3>
      <span class="sub">特征值占比</span>
    </div>
    <VChart :option="option" autoresize class="chart" @click="handleClick" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  points: { type: Array, default: () => [] }, // [{name, x, y, size, type, primary}]
});

const emit = defineEmits(["select"]);

const palette = {
  标准型: "#22c55e",
  偏二次型: "#facc15",
  偏燃煤型: "#ef4444",
  偏交通型: "#2563eb",
  偏燃烧型: "#a855f7",
  偏颗粒物型: "#f97316",
  未知: "#9ca3af",
};

const option = computed(() => {
  const data = props.points.map((p) => ({
    name: p.name,
    value: [p.x, p.y, p.size],
    type: p.type,
    primary: p.primary?.toUpperCase?.() || "-",
  }));
  return {
    backgroundColor: "transparent",
    tooltip: {
      formatter: (p) => {
        const d = data[p.dataIndex];
        return `${d.name}<br/>类型：${d.type}<br/>主导：${d.primary}<br/>颗粒占比：${d.value[0]}<br/>O3占比：${d.value[1]}`;
      },
    },
    xAxis: {
      name: "颗粒物占比 (PM2.5+PM10)",
      min: 0,
      max: 1,
      axisLabel: { color: "#cdd9e5" },
      nameTextStyle: { color: "#cdd9e5" },
    },
    yAxis: {
      name: "二次污染占比 (O3)",
      min: 0,
      max: 1,
      axisLabel: { color: "#cdd9e5" },
      nameTextStyle: { color: "#cdd9e5" },
    },
    series: [
      {
        type: "scatter",
        symbolSize: (p) => 10 + Math.sqrt(p[2] || 0) * 15, // 缩小点大小
        data,
        itemStyle: {
          color: (p) => {
            const d = data[p.dataIndex];
            return palette[d.type] || "#9ca3af";
          },
          opacity: 0.82,
        },
        emphasis: { focus: "self", itemStyle: { opacity: 1 } },
      },
    ],
  };
});

function handleClick(p) {
  const idx = p?.dataIndex;
  if (idx != null) emit("select", props.points[idx]?.name);
}
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.sub {
  color: #9eb1c7;
  font-size: 12px;
}
.chart {
  height: 320px;
}
</style>
