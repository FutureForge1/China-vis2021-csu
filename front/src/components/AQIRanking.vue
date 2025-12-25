<template>
  <div class="wrap">
    <div class="heading">
      <h3>AQI 排行</h3>
      <span class="sub">按省均值</span>
    </div>
    <VChart :option="option" autoresize class="chart" />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name, aqi, primaryPollutant}]
});

const emit = defineEmits(["select"]);

const option = computed(() => {
  const names = props.items.map((d) => d.name);
  const values = props.items.map((d) => d.aqi);
  const primary = props.items.map((d) => d.primaryPollutant?.toUpperCase?.() || "-");
  const colors = values.map((v) => aqiColor(v));

  return {
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (p) => {
        const i = p[0].dataIndex;
        return `${names[i]}<br/>AQI: ${values[i]}<br/>主导: ${primary[i]}`;
      },
    },
    grid: { left: 80, right: 20, top: 10, bottom: 10 },
    xAxis: { type: "value", axisLabel: { color: "#cdd9e5" } },
    yAxis: {
      type: "category",
      data: names,
      axisLabel: { color: "#cdd9e5" },
    },
    series: [
      {
        type: "bar",
        data: values,
        itemStyle: {
          color: (p) => colors[p.dataIndex],
        },
        label: { show: true, position: "right", color: "#e6edf3" },
      },
    ],
    on: {
      click: (params) => {
        const idx = params?.dataIndex;
        if (idx != null) emit("select", names[idx]);
      },
    },
  };
});

function aqiColor(v) {
  if (v <= 50) return "#22c55e";
  if (v <= 100) return "#a3e635";
  if (v <= 150) return "#facc15";
  if (v <= 200) return "#f97316";
  if (v <= 300) return "#ef4444";
  return "#7f1d1d";
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
  height: 300px;
}
</style>
