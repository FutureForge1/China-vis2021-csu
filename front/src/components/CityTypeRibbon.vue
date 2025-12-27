<template>
  <div class="wrap">
    <div class="heading">
      <h3>城市类型变化凹凸图</h3>
      <span class="sub">{{ province || "全国" }} · {{ monthLabel }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{name,data}]
  typeOrder: { type: Array, default: () => [] },
  province: { type: String, default: "" },
});

const colors = ["#d23669", "#d66b6b", "#d99c7b", "#d1b181", "#8cb972", "#6ba4c1", "#8b82c9", "#9ca3af"];

const monthLabel = computed(() => (props.dates[0] || "").slice(0, 7));

const option = computed(() => {
  const maxSeries = 6;
  const seriesTrimmed = props.series.slice(0, maxSeries);
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      formatter: (p) => `${p.seriesName}<br/>${props.dates[p.dataIndex]}<br/>类型：${props.typeOrder[p.value] || "-"}`,
    },
  grid: { left: 10, right: 100, top: 20, bottom: 30, containLabel: true },
  xAxis: {
    type: "category",
    data: props.dates.map((d) => d.slice(5)),
    boundaryGap: false,
    axisLabel: { color: "#94a3b8" },
    splitLine: { show: true, lineStyle: { color: "rgba(15,23,42,0.08)" } },
  },
  yAxis: {
    type: "category",
    data: props.typeOrder.slice().reverse(),
    axisLabel: { color: "#475569" },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: false },
  },
    series: seriesTrimmed.map((s, idx) => ({
      name: s.name,
      type: "line",
      data: s.data.map((v) => (v == null ? null : props.typeOrder.length - 1 - v)),
      smooth: true,
      lineStyle: { width: idx === 0 ? 3 : 1.5, color: colors[idx % colors.length], opacity: idx === 0 ? 0.95 : 0.4 },
      itemStyle: { color: colors[idx % colors.length] },
      symbol: "none",
      emphasis: { lineStyle: { width: 3 } },
      areaStyle: { opacity: idx === 0 ? 0.12 : 0.05, color: colors[idx % colors.length] },
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
  gap: 8px;
}
.sub {
  color: #94a3b8;
  font-size: 12px;
}
.chart {
  height: 320px;
}
</style>
