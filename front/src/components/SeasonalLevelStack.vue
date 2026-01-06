<template>
  <div class="wrap">
    <div class="heading">
      <h3>{{ mode === 'monthly' ? 'MONTHLY LEVEL DIST' : 'ANNUAL LEVEL DIST' }}</h3>
      <span class="sub">{{ metricLabel }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" @click="handleClick" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{name, data}]
  metric: { type: String, default: "pm25" },
  mode: { type: String, default: "daily" }, // "daily" or "monthly"
});

const emit = defineEmits(["select-date"]);

const metricLabel = computed(() => props.metric.toUpperCase());

function handleClick(params) {
  // params.name carries the x-axis category value (date string)
  if (params?.name) emit("select-date", params.name);
}

const option = computed(() => {
  const isMonthly = props.mode === 'monthly';

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: { color: "#0a0a0a", fontFamily: 'JetBrains Mono' },
      formatter: (params) => {
        let total = 0;
        params.forEach(param => total += param.value);
        let result = `<div style="border-bottom: 1px solid #ddd; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${isMonthly ? params[0].name : params[0].name}</div>`;
        params.forEach(param => {
          result += `<div style="display: flex; justify-content: space-between; gap: 12px;"><span>${param.seriesName}:</span><span style="font-weight: bold;">${param.value}</span></div>`;
        });
        result += `<div style="border-top: 1px solid #ddd; margin-top: 4px; padding-top: 4px; display: flex; justify-content: space-between;"><span>TOTAL:</span><span style="font-weight: bold;">${total}</span></div>`;
        return result;
      }
    },
    grid: { top: 30, left: 40, right: 20, bottom: 20 },
    xAxis: {
      type: "category",
      data: isMonthly ? ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'] : props.dates,
      axisLabel: {
        formatter: (v) => isMonthly ? v : v.slice(5),
        color: "#666",
        fontFamily: "JetBrains Mono",
        fontSize: 10
      },
      axisLine: { lineStyle: { color: "#ddd" } },
    },
    yAxis: {
      type: "value",
      name: isMonthly ? "DAYS" : "CITIES",
      nameTextStyle: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      axisLabel: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
    },
    legend: { 
      top: 0, 
      textStyle: { color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
      itemWidth: 10,
      itemHeight: 10
    },
    series: props.series.map((s) => ({
      type: "bar",
      name: s.name,
      stack: "level",
      data: s.data,
      barWidth: isMonthly ? "60%" : "60%",
      emphasis: { focus: "series" },
    })),
    // Endfield Yellow Scale
    color: ["#ddd333", "#4d4500", "#665c00", "#998a00", "#ccb800", "#FFE600"],
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
  border-bottom: 1px solid #ddd;
  padding-bottom: 4px;
}
h3 {
  margin: 0;
  font-family: "Oswald", sans-serif;
  font-size: 14px;
  color: #0a0a0a;
  letter-spacing: 1px;
}
.sub {
  color: #666;
  font-family: "JetBrains Mono", monospace;
  font-size: 10px;
}
.chart {
  height: 220px;
}
</style>
