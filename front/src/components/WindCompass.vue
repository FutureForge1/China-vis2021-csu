<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>扩散 / 风廓线</h3>
        <span class="sub">当日 u / v 均值形成的风向玫瑰</span>
      </div>
      <div class="badge">风速 m/s</div>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{dir,value}]
});

const option = computed(() => {
  const dirs = props.data.map((d) => d.dir);
  const values = props.data.map((d) => d.value);
  const max = values.length ? Math.max(...values) : 1;
  const gradient = ["#7cc5ff", "#5aa0f7", "#3f7ae0", "#3059c8"];

  return {
    backgroundColor: "transparent",
    tooltip: {
      backgroundColor: "rgba(15,23,42,0.9)",
      borderColor: "rgba(255,255,255,0.08)",
      textStyle: { color: "#e5ecf4" },
      formatter: (p) =>
        `${dirs[p.dataIndex]}<br/>风速：${values[p.dataIndex].toFixed(2)} m/s`,
    },
    polar: { radius: ["12%", "78%"] },
    angleAxis: {
      type: "category",
      data: dirs,
      boundaryGap: false,
      axisLine: { lineStyle: { color: "rgba(15,23,42,0.25)" } },
      axisLabel: { color: "#475569", fontSize: 11 },
      axisTick: { show: false },
    },
    radiusAxis: {
      min: 0,
      max: Math.max(max, 1),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(15,23,42,0.08)" } },
    },
    series: [
      {
        type: "bar",
        coordinateSystem: "polar",
        data: values.map((v, i) => ({
          value: v,
          itemStyle: {
            color: {
              type: "linear",
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: gradient[0] },
                { offset: 1, color: gradient[2] },
              ],
            },
            opacity: 0.78,
          },
          name: dirs[i],
        })),
        barWidth: 14,
        roundCap: true,
        emphasis: { focus: "self" },
        label: {
          show: true,
          position: "outside",
          formatter: ({ value }) => (value > 0 ? value.toFixed(1) : ""),
          color: "#475569",
          fontSize: 10,
        },
      },
      {
        type: "line",
        coordinateSystem: "polar",
        data: values,
        smooth: true,
        areaStyle: { color: "rgba(63,122,224,0.14)" },
        lineStyle: { color: gradient[3], width: 2 },
        symbol: "circle",
        symbolSize: 5,
        itemStyle: { color: gradient[3] },
        z: 3,
      },
    ],
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
  align-items: center;
  gap: 6px;
  justify-content: space-between;
  flex-wrap: wrap;
}
.sub {
  color: #9eb1c7;
  font-size: 12px;
}
.badge {
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(63, 122, 224, 0.12);
  border: 1px solid rgba(63, 122, 224, 0.32);
  color: #1f2a44;
}
.chart {
  height: 280px;
}
</style>
