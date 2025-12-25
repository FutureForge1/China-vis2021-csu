<template>
  <div class="wrap">
    <div class="heading">
      <h3>全年污染等级</h3>
      <span class="sub">按天计数</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  levels: { type: Array, default: () => [] }, // [{level, value}]
});

const option = computed(() => ({
  backgroundColor: "transparent",
  tooltip: { trigger: "item" },
  grid: { top: 20, left: 40, right: 10, bottom: 20 },
  xAxis: {
    type: "value",
  },
  yAxis: {
    type: "category",
    data: props.levels.map((l) => l.level),
  },
  series: [
    {
      type: "bar",
      data: props.levels.map((l) => l.value),
      label: { show: true, position: "right" },
      itemStyle: {
        color: (p) => {
          const palette = ["#22c55e", "#a3e635", "#f59e0b", "#f97316", "#ef4444", "#7f1d1d"];
          return palette[p.dataIndex % palette.length];
        },
      },
    },
  ],
}));
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
  height: 160px;
}
</style>
