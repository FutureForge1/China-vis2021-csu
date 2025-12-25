<template>
  <div class="wrap">
    <div class="heading">
      <h3>月均污染物线圈</h3>
      <span class="sub">颜色=月均 AQI 等级</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name,data,aqi,level}]
});

const levelColor = {
  优: "#22c55e",
  良: "#a3e635",
  轻度: "#facc15",
  中度: "#f97316",
  重度: "#ef4444",
  严重: "#7f1d1d",
};

const option = computed(() => {
  const indicators = props.items[0]?.data?.map((d) => d.indicator) || [];
  const max = Math.max(
    10,
    ...props.items.flatMap((item) => item.data?.map((d) => Number(d.value) || 0) || [])
  );

  return {
    backgroundColor: "transparent",
    legend: { top: 4, textStyle: { color: "#cdd9e5" } },
    tooltip: {
      formatter: (p) => {
        const item = props.items[p.seriesIndex];
        const vals = indicators.map((ind, idx) => `${ind}: ${p.value[idx]}`);
        return `${item.name}（AQI ${item.aqi} / ${item.level}）<br/>${vals.join("<br/>")}`;
      },
    },
    radar: {
      indicator: indicators.map((ind) => ({ name: ind, max })),
      splitNumber: 5,
      splitArea: { areaStyle: { color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.04)"] } },
      axisName: { color: "#cdd9e5" },
      axisLabel: { show: false },
    },
    series: props.items.map((item) => ({
      type: "radar",
      name: item.name,
      data: [item.data.map((d) => d.value)],
      areaStyle: { opacity: 0.12, color: levelColor[item.level] || "#60a5fa" },
      lineStyle: { width: 2, color: levelColor[item.level] || "#60a5fa" },
    })),
  };
});
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
  height: 280px;
}
</style>
