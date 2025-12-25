<template>
  <div class="wrap">
    <div class="heading">
      <h3>污染物与 AQI 平行坐标</h3>
      <span class="sub">按省均值</span>
    </div>
    <VChart :option="option" autoresize class="chart" @click="handleClick" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  rows: { type: Array, default: () => [] }, // [{name, values:[AQI, pm25...], primaryPollutant}]
});

const emit = defineEmits(["select"]);

const dimensions = ["AQI", "PM2.5", "PM10", "SO2", "NO2", "CO", "O3"];

const option = computed(() => {
  const axis = dimensions.map((d, idx) => ({
    dim: idx,
    name: d,
    nameTextStyle: { color: "#cdd9e5" },
  }));

  const data = props.rows.map((r) => ({
    name: r.name,
    value: r.values,
    primary: r.primaryPollutant?.toUpperCase?.() || "-",
  }));

  return {
    backgroundColor: "transparent",
    parallelAxis: axis,
    parallel: {
      left: 60,
      right: 40,
      bottom: 30,
      top: 40,
    },
    tooltip: {
      trigger: "item",
      formatter: (p) => {
        const d = data[p.dataIndex];
        const lines = [d.name];
        dimensions.forEach((dim, i) => {
          lines.push(`${dim}: ${d.value[i]}`);
        });
        lines.push(`主导: ${d.primary}`);
        return lines.join("<br/>");
      },
    },
    visualMap: {
      type: "continuous",
      min: 0,
      max: Math.max(...(data.map((d) => d.value[0]).filter((n) => Number.isFinite(n))), 50),
      dimension: 0,
      inRange: {
        color: ["#22c55e", "#a3e635", "#facc15", "#f97316", "#ef4444", "#7f1d1d"],
      },
      text: ["高AQI", "低AQI"],
      textStyle: { color: "#cdd9e5" },
    },
    series: [
      {
        type: "parallel",
        lineStyle: { width: 1, opacity: 0.7 },
        data,
      },
    ],
  };
});

function handleClick(p) {
  const idx = p?.dataIndex;
  if (idx != null) emit("select", props.rows[idx]?.name);
}
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
  height: 320px;
}
</style>
