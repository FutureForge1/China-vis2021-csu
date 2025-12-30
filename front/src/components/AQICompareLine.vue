<template>
  <div class="wrap">
    <div class="heading">
      <h3>{{ mode === 'monthly' ? '多年月均 AQI 对比' : '多年 AQI 折线对比' }}</h3>
      <span class="sub">{{ mode === 'monthly' ? '月均值对比' : '1 月逐日均值' }}</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  days: { type: Array, default: () => [] }, // ["1","2",...] 或 ["1月","2月",...]
  series: { type: Array, default: () => [] }, // [{name, data}]
  mode: { type: String, default: "daily" }, // "daily" or "monthly"
});

const option = computed(() => {
  const isMonthly = props.mode === 'monthly';

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const dateLabel = isMonthly ? params[0].name : `第${params[0].name}天`;
        let result = `${dateLabel}<br/>`;
        params.forEach(param => {
          result += `${param.marker}${param.seriesName}: ${param.value.toFixed(1)}<br/>`;
        });
        return result;
      }
    },
    legend: { top: 4, textStyle: { color: "#cdd9e5" } },
    grid: { top: 40, left: 60, right: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: props.days,
      axisLabel: {
        color: "#9eb1c7",
        formatter: (value) => isMonthly ? value : value
      },
    },
    yAxis: {
      type: "value",
      name: "AQI",
      axisLabel: { color: "#9eb1c7" },
      splitLine: { lineStyle: { color: "#30363d" } },
    },
    series: props.series.map((s) => ({
      type: "line",
      name: s.name,
      data: s.data,
      smooth: isMonthly ? false : true, // 月度数据不需要平滑
      showSymbol: isMonthly ? true : false, // 月度数据显示数据点
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
