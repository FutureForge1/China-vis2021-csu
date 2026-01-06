<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>CITY POLLUTION STACKED PIE</h3>
        <span class="sub">{{ city || "NO CITY SELECTED" }} · {{ monthLabel }}</span>
      </div>
      <div class="pill">DAILY VS MONTHLY RANGE</div>
    </div>
    <div v-if="!city && Object.keys(dayValues).length === 0" class="no-data">
      <p>Select a city on the map to view detailed pollution data</p>
    </div>
    <VChart v-else :option="option" class="chart" />
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
  belowMin: "#ddd333",
  belowBench: "#665c00",
  bench: "#ccb800",
  aboveMax: "#FFE600",
};

const legend = [
  { label: "<MIN", color: palette.belowMin },
  { label: "<AVG", color: palette.belowBench },
  { label: "<MAX", color: palette.bench },
  { label: ">MAX", color: palette.aboveMax },
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
      backgroundColor: "rgba(255,255,255,0.95)",
      borderColor: "#FFE600",
      borderWidth: 1,
      textStyle: {
        color: "#0a0a0a",
        fontFamily: "JetBrains Mono",
        fontSize: 12
      },
      formatter: (p) => {
        const key = pollutants[p.dataIndex];
        const stats = props.monthStats[key] || { min: 0, avg: 0, max: 0 };
        return `<div style="border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-bottom: 4px; color: #FFE600; font-weight: bold;">${p.name}</div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>DAILY:</span><span style="font-weight: bold; color: #0a0a0a;">${p.value.toFixed(2)}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>AVG:</span><span style="font-weight: bold; color: #0a0a0a;">${stats.avg.toFixed(2)}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>MIN:</span><span style="font-weight: bold; color: #0a0a0a;">${stats.min.toFixed(2)}</span></div>
                <div style="display: flex; justify-content: space-between; gap: 12px;"><span>MAX:</span><span style="font-weight: bold; color: #0a0a0a;">${stats.max.toFixed(2)}</span></div>`;
      },
    },
    angleAxis: {
      type: "category",
      data: pollutants.map((p) => labels[p]),
      startAngle: 90,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: true, color: "#666", fontFamily: "JetBrains Mono", fontSize: 10 },
    },
    radiusAxis: {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { show: false },
      splitLine: {
        show: true,
        lineStyle: { color: "rgba(0,0,0,0.05)" },
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
        itemStyle: { color: "rgba(0,0,0,0.05)" },
        barWidth: 30,
      },
      {
        type: "bar",
        coordinateSystem: "polar",
        data,
        barWidth: 30,
        roundCap: false,
        label: {
          show: false,
        },
        z: 10,
        itemStyle: {
          borderColor: "#000",
          borderWidth: 1
        }
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
  height: 100%;
}
.heading {
  display: flex;
  align-items: baseline;
  gap: 8px;
  justify-content: space-between;
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
.pill {
  background: #FFE600;
  color: #000;
  padding: 4px 8px;
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
.legend {
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
.chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: #666;
  font-family: "JetBrains Mono", monospace;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 0;
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
