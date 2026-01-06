<template>
  <div class="wrap">
    <div class="heading">
      <h3>POLLUTION TYPE CLUSTERING</h3>
      <span class="sub">FEATURE RATIO</span>
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

const typeMap = {
  "标准型": "STANDARD",
  "偏二次型": "SECONDARY",
  "偏燃煤型": "COAL",
  "偏交通型": "TRAFFIC",
  "偏燃烧型": "COMBUSTION",
  "偏颗粒物型": "PARTICULATE",
  "未知": "UNKNOWN"
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
      backgroundColor: "rgba(20, 20, 20, 0.9)",
      borderColor: "rgba(255, 255, 255, 0.15)",
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (p) => {
        const d = data[p.dataIndex];
        const typeEn = typeMap[d.type] || d.type;
        return `<div style="font-weight:bold;margin-bottom:4px;font-family:'Oswald'">${d.name}</div>
                <div style="font-size:12px">TYPE: ${typeEn}</div>
                <div style="font-size:12px">PRIMARY: ${d.primary}</div>
                <div style="font-size:12px">PARTICULATE: ${d.value[0].toFixed(2)}</div>
                <div style="font-size:12px">O3: ${d.value[1].toFixed(2)}</div>`;
      },
    },
    xAxis: {
      name: "PARTICULATE RATIO",
      min: 0,
      max: 1,
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      nameTextStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    },
    yAxis: {
      name: "O3 RATIO",
      min: 0,
      max: 1,
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisLabel: { color: "#666", fontFamily: 'JetBrains Mono' },
      nameTextStyle: { color: "#666", fontFamily: 'JetBrains Mono' },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    },
    series: [
      {
        type: "scatter",
        symbolSize: (p) => 8 + Math.sqrt(p[2] || 0) * 12,
        data,
        itemStyle: {
          color: (p) => {
            const d = data[p.dataIndex];
            return palette[d.type] || "#9ca3af";
          },
          opacity: 0.7,
          borderColor: "rgba(255,255,255,0.2)",
          borderWidth: 1,
        },
        emphasis: {
          focus: "self",
          itemStyle: {
            opacity: 1,
            borderColor: "#0a0a0a",
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: "rgba(0,0,0,0.5)",
          },
        },
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
  gap: 10px;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 10px;
  border-bottom: 1px solid var(--c-border);
  padding-bottom: 5px;
}
h3 {
  margin: 0;
  font-family: var(--font-display);
  font-size: 16px;
  color: var(--c-white);
}
.sub {
  color: var(--c-gray);
  font-family: var(--font-mono);
  font-size: 10px;
  text-transform: uppercase;
}
.chart {
  height: 320px;
}
</style>
