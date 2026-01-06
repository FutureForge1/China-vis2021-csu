<template>
  <div class="wrap">
    <div class="heading">
      <h3>{{ mode === 'monthly' ? 'MULTI-YEAR AQI COMPARISON' : 'MULTI-YEAR AQI TREND' }}</h3>
      <span class="sub">{{ mode === 'monthly' ? 'MONTHLY MEAN' : 'DAILY MEAN' }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  days: { type: Array, default: () => [] }, // ["1","2",...] or ["Jan","Feb",...]
  series: { type: Array, default: () => [] }, // [{name, data}]
  mode: { type: String, default: "daily" }, // "daily" or "monthly"
});

const option = computed(() => {
  const isMonthly = props.mode === 'monthly';

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (params) => {
        const dateLabel = isMonthly ? params[0].name : `DAY ${params[0].name}`;
        let result = `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${dateLabel}</div>`;
        params.forEach(param => {
          result += `<div style="display: flex; justify-content: space-between; gap: 12px;">
            <span>${param.marker}${param.seriesName}</span>
            <span style="font-weight: bold; color: #0a0a0a;">${param.value.toFixed(1)}</span>
          </div>`;
        });
        return result;
      }
    },
    legend: { 
      top: 0, 
      right: 0,
      textStyle: { 
        color: "#666",
        fontFamily: "JetBrains Mono",
        fontSize: 10
      },
      itemWidth: 12,
      itemHeight: 2
    },
    grid: { top: 30, left: 40, right: 20, bottom: 20 },
    xAxis: {
      type: "category",
      data: props.days,
      axisLabel: {
        color: "#666",
        fontFamily: "JetBrains Mono",
        fontSize: 10,
        formatter: (value) => isMonthly ? value : value
      },
      axisLine: { lineStyle: { color: "#ddd" } },
      axisTick: { show: false }
    },
    yAxis: {
      type: "value",
      name: "AQI",
      nameTextStyle: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      splitLine: { lineStyle: { color: "#ddd", type: "dashed" } },
    },
    series: props.series.map((s) => ({
      type: "line",
      name: s.name,
      data: s.data,
      smooth: isMonthly ? false : true,
      showSymbol: isMonthly ? true : false,
      symbolSize: isMonthly ? 6 : 4,
      lineStyle: { width: 2 },
      emphasis: {
        focus: 'series',
        lineStyle: { width: 3 }
      },
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
  font-size: 14px;
  font-weight: bold;
  color: #0a0a0a;
  font-family: "Oswald", sans-serif;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.sub {
  color: #FFE600;
  font-size: 10px;
  font-family: "JetBrains Mono", monospace;
  text-transform: uppercase;
}
.chart {
  flex: 1;
  min-height: 0;
}
</style>
