<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染物线圈图</h3>
      <span class="sub">均值</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  data: { type: Array, default: () => [] }, // [{indicator, value}]
});

const option = computed(() => {
  const values = props.data.map((d) => Number(d.value ?? 0));
  const rawMax = values.length ? Math.max(...values) : 10;
  const roundedMax = Math.max(10, Math.ceil((rawMax || 10) / 10) * 10);
  return {
    backgroundColor: "transparent",
    tooltip: { trigger: "item" },
    radar: {
      indicator: props.data.map((d) => ({
        name: d.indicator,
        min: 0,
        max: roundedMax,
      })),
      splitNumber: 5,
      splitArea: { areaStyle: { color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.04)"] } },
      axisName: { color: "#cdd9e5" },
      axisLabel: { show: false },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: values,
            name: "均值",
            areaStyle: { opacity: 0.2 },
            lineStyle: { width: 2 },
          },
        ],
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
  align-items: baseline;
  gap: 6px;
}

.sub {
  color: #9eb1c7;
  font-size: 12px;
}

.chart {
  height: 200px;
}
</style>
