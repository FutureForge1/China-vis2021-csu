<template>
  <div class="wrap">
    <div class="heading">
      <h3>CITY TYPE BUMP CHART</h3>
      <span class="sub">{{ province || "NATIONAL" }} · {{ monthLabel }}</span>
    </div>
    <div v-if="!dates || dates.length === 0 || !series || series.length === 0" class="no-data">
      <p>{{ province ? 'Loading province data...' : 'Select a province to view type evolution' }}</p>
    </div>
    <VChart v-else :option="option" class="chart" />
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

// Endfield Yellow Scale
const colors = ["#FFE600", "#ccb800", "#998a00", "#665c00", "#4d4500", "#ddd333", "#1a1a1a", "#000000"];

const monthLabel = computed(() => (props.dates[0] || "").slice(0, 7));

const option = computed(() => {
  console.log('[CityTypeRibbon] Props:', {
    dates: props.dates?.length,
    series: props.series?.length,
    typeOrder: props.typeOrder?.length,
    province: props.province
  });

  if (!props.dates || props.dates.length === 0 || !props.series || props.series.length === 0) {
    console.log('[CityTypeRibbon] No data available');
    return {
      backgroundColor: "transparent",
      title: {
        text: 'NO DATA',
        left: 'center',
        top: 'center',
        textStyle: { color: '#666', fontSize: 14, fontFamily: "JetBrains Mono" }
      }
    };
  }

  const maxSeries = 6;
  const seriesTrimmed = props.series.slice(0, maxSeries);
  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "item",
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (p) => {
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${p.seriesName}</div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>DATE:</span><span style="font-weight: bold; color: #0a0a0a;">${props.dates[p.dataIndex]}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>TYPE:</span><span style="font-weight: bold; color: #0a0a0a;">${props.typeOrder[p.value] || "-"}</span></div>`;
      },
    },
  grid: { left: 10, right: 100, top: 20, bottom: 30, containLabel: true },
  xAxis: {
    type: "category",
    data: props.dates.map((d) => d.slice(5)),
    boundaryGap: false,
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    splitLine: { show: true, lineStyle: { color: "rgba(0,0,0,0.05)" } },
    axisLine: { lineStyle: { color: "#ddd" } },
    axisTick: { show: false }
  },
  yAxis: {
    type: "category",
    data: props.typeOrder.slice().reverse(),
    axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
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
  height: 100%;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
}
h3 {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: #0a0a0a;
  font-family: "Oswald", sans-serif;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.sub {
  color: #000;
  background: #FFE600;
  padding: 2px 6px;
  font-size: 11px;
  font-weight: bold;
  font-family: "JetBrains Mono", monospace;
  text-transform: uppercase;
}
.chart {
  flex: 1;
  min-height: 0;
  width: 100%;
  height: 450px;
}

.no-data {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-family: "JetBrains Mono", monospace;
  font-size: 12px;
  text-align: center;
  padding: 40px;
}
</style>
