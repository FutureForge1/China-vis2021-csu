<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>城市污染变化堆叠饼图</h3>
        <span class="sub">{{ city || "未选城市" }} · {{ monthLabel }}</span>
      </div>
      <div class="pill">当日 vs 当月区间</div>
    </div>
    <VChart :option="option" autoresize class="chart" />
    <div class="legend">
      <span v-for="item in legend" :key="item.label" class="chip">
        <span class="dot" :style="{ background: item.color }"></span>{{ item.label }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  city: { type: String, default: "" },
  dayValues: { type: Object, default: () => ({}) }, // {pm25: v,...}
  monthStats: { type: Object, default: () => ({}) }, // {pm25:{avg,min,max},...}
  month: { type: String, default: "" },
});

const pollutants = ["pm25", "pm10", "so2", "no2", "co", "o3"];
const labels = { pm25: "PM2.5", pm10: "PM10", so2: "SO2", no2: "NO2", co: "CO", o3: "O3" };
const palette = {
  belowMin: "#d6d8dc",
  belowBench: "#e8c2b8",
  bench: "#e07a5f",
  aboveMax: "#b23a48",
};

const legend = [
  { label: "<min", color: palette.belowMin },
  { label: "<bench", color: palette.belowBench },
  { label: "<max", color: palette.bench },
  { label: ">max", color: palette.aboveMax },
];

const monthLabel = computed(() => props.month || new Date().toISOString().slice(0, 7));

function sectorColor(val, stats) {
  if (!stats) return palette.belowMin;
  if (val <= stats.min) return palette.belowMin;
  if (val <= stats.avg) return palette.belowBench;
  if (val <= stats.max) return palette.bench;
  return palette.aboveMax;
}

const option = computed(() => {
  const data = pollutants.map((p) => {
    const v = Number(props.dayValues[p] ?? 0);
    const stats = props.monthStats[p] || { min: 0, avg: 0, max: 0 };
    return {
      name: labels[p],
      value: v,
      itemStyle: { color: sectorColor(v, stats) },
      emphasis: { scale: false },
      tooltip: {
        show: false,
      },
    };
  });

  return {
    backgroundColor: "transparent",
    tooltip: {
      formatter: (p) => {
        const key = pollutants[p.dataIndex];
        const stats = props.monthStats[key] || { min: 0, avg: 0, max: 0 };
        return `${p.name}<br/>日值: ${p.value.toFixed(2)}<br/>月均: ${stats.avg.toFixed(
          2
        )}<br/>月最小: ${stats.min.toFixed(2)}<br/>月最大: ${stats.max.toFixed(2)}`;
      },
    },
    angleAxis: {
      type: "category",
      data: pollutants.map((p) => labels[p]),
      startAngle: 90,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: true, color: "#475569" },
    },
    radiusAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: {
        show: true,
        lineStyle: { color: "rgba(15,23,42,0.08)" },
      },
    },
    polar: { radius: "75%" },
    series: [
      {
        type: "bar",
        coordinateSystem: "polar",
        data: pollutants.map(() => 1),
        barGap: "-100%",
        silent: true,
        itemStyle: { color: "rgba(15,23,42,0.04)" },
        barWidth: 30,
      },
      {
        type: "bar",
        coordinateSystem: "polar",
        data,
        barWidth: 30,
        roundCap: true,
        label: {
          show: false,
        },
        z: 10,
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
  gap: 8px;
  justify-content: space-between;
}
.sub {
  color: #94a3b8;
  font-size: 12px;
}
.pill {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  color: #0f172a;
  background: rgba(15, 23, 42, 0.06);
  border: 1px solid rgba(15, 23, 42, 0.08);
}
.chart {
  height: 320px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 10px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(15, 23, 42, 0.02);
  font-size: 12px;
  color: #0f172a;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
</style>
