<template>
  <div class="wrap">
    <div class="heading">
      <h3>{{ mode === 'monthly' ? '月度污染等级分布' : '全年污染等级分布' }}</h3>
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
      formatter: (params) => {
        let total = 0;
        params.forEach(param => total += param.value);
        let result = `${isMonthly ? '第' + params[0].name + '月' : params[0].name}<br/>`;
        params.forEach(param => {
          result += `${param.marker}${param.seriesName}: ${param.value}<br/>`;
        });
        result += `总计: ${total}`;
        return result;
      }
    },
    grid: { top: 30, left: 60, right: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: isMonthly ? ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'] : props.dates,
      axisLabel: {
        formatter: (v) => isMonthly ? v : v.slice(5),
        color: "#9eb1c7"
      },
    },
    yAxis: {
      type: "value",
      name: isMonthly ? "天数" : "城市数",
      axisLabel: { color: "#9eb1c7" },
      splitLine: { lineStyle: { color: "#30363d" } },
    },
    legend: { top: 4, textStyle: { color: "#cdd9e5" } },
    series: props.series.map((s) => ({
      type: "bar",
      name: s.name,
      stack: "level",
      data: s.data,
      barWidth: isMonthly ? "80%" : "60%",
      emphasis: { focus: "series" },
    })),
    color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
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
  height: 220px;
}
</style>
