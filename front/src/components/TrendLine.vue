<template>
  <div class="wrap">
    <div class="heading">
      <h3>TREND</h3>
      <span class="sub"
        >{{ metric.toUpperCase() }} · {{ granularityLabel }}粒度</span
      >
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  series: { type: Array, default: () => [] }, // [{date, value}]
  dates: { type: Array, default: () => [] },
  metric: { type: String, default: "pm25" },
  granularity: { type: String, default: "day" }, // 新增：时间粒度
});

const granularityLabel = computed(() => {
  const labels = { day: "日", month: "月", year: "年" };
  return labels[props.granularity] || "日";
});

const option = computed(() => {
  // 根据粒度调整x轴标签间隔
  let labelInterval = 0;
  if (props.granularity === "day") {
    labelInterval = Math.max(0, Math.floor(props.dates.length / 12));
  } else if (props.granularity === "month") {
    labelInterval = 0; // 月份数据较少，全部显示
  } else {
    labelInterval = 0; // 年份数据更少
  }

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "rgba(0, 0, 0, 0.08)",
      textStyle: { color: "#0a0a0a", fontFamily: "JetBrains Mono" },
      formatter: (params) => {
        const p = params[0];
        return `${
          p.axisValueLabel
        }<br/>${props.metric.toUpperCase()}: <strong>${
          p.value?.toFixed(2) || 0
        }</strong>`;
      },
    },
    grid: { top: 30, left: 40, right: 20, bottom: 50 },
    xAxis: {
      type: "category",
      data: props.dates,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "rgba(0,0,0,0.1)" } },
      axisLabel: {
        color: "#666",
        fontFamily: "JetBrains Mono",
        fontSize: 10,
        interval: labelInterval,
        rotate: props.granularity === "day" && props.dates.length > 30 ? 45 : 0,
      },
      axisTick: { show: true, lineStyle: { color: "rgba(0,0,0,0.1)" } },
    },
    yAxis: {
      type: "value",
      name: props.metric.toUpperCase(),
      splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
      axisLabel: { color: "#666", fontFamily: "JetBrains Mono" },
      nameTextStyle: { color: "#666", fontFamily: "JetBrains Mono" },
    },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      {
        type: "slider",
        start: 0,
        end: 100,
        borderColor: "transparent",
        backgroundColor: "rgba(0,0,0,0.05)",
        fillerColor: "rgba(255, 230, 0, 0.1)",
        handleStyle: { color: "#FFE600" },
        textStyle: { color: "#666", fontFamily: "JetBrains Mono" },
      },
    ],
    series: [
      {
        type: "line",
        data: props.series.map((s) => s.value),
        smooth: true,
        showSymbol: false,
        areaStyle: {
          opacity: 0.2,
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "#FFE600" },
              { offset: 1, color: "transparent" },
            ],
          },
        },
        lineStyle: { width: 2, color: "#FFE600" },
      },
    ],
  };
});
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
  height: 250px;
}
</style>
