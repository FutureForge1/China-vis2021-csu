<template>
  <div class="wrap">
    <div class="heading">
      <div>
        <h3>污染物线圈图</h3>
        <span class="sub">条数映射值 · 颜色映射当月 AQI 等级</span>
      </div>
      <div class="note">顺序与 AQI 排行一致</div>
    </div>
    <div class="grid" v-if="items && items.length">
      <div class="cell header empty"></div>
      <div
        v-for="m in months"
        :key="m"
        class="cell header month"
      >
        {{ m }}月
      </div>
      <template v-for="row in items" :key="row.name">
        <div class="cell row-label">{{ row.name }}</div>
        <div
          v-for="cell in row.months"
          :key="cell.month + row.name"
          class="cell ring-cell"
          :style="cellStyle(cell)"
          :title="`${row.name} ${cell.month}月\n${metricLabel.toUpperCase()}: ${cell.value}\nAQI: ${cell.aqi.toFixed(1)}`"
        >
          <svg viewBox="0 0 100 100" aria-hidden="true">
            <g :stroke="aqiColor(cell.aqi)" stroke-width="2" stroke-linecap="round">
              <line
                v-for="i in cell.segments"
                :key="i"
                :x1="50"
                :y1="50"
                :x2="50 + 32 * Math.cos((i / cell.segments) * Math.PI * 2)"
                :y2="50 + 32 * Math.sin((i / cell.segments) * Math.PI * 2)"
                :opacity="0.75"
              />
            </g>
            <circle cx="50" cy="50" r="8" :fill="aqiColor(cell.aqi)" fill-opacity="0.8" />
          </svg>
        </div>
      </template>
    </div>
    <div v-else class="placeholder">暂无数据</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{name, months:[{month,value,aqi,segments}]}]
  metric: { type: String, default: "pm25" },
});

const months = Array.from({ length: 12 }, (_, i) => i + 1);
const metricLabel = computed(() => props.metric || "pm25");

const cellStyle = (cell) => {
  const color = aqiColor(cell.aqi);
  return {
    background: `radial-gradient(circle at 50% 50%, ${color}18, rgba(255,255,255,0.85))`,
    borderColor: `${color}55`,
  };
};

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
  gap: 8px;
}
.heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.sub {
  color: #9eb1c7;
  font-size: 12px;
}
.note {
  font-size: 12px;
  color: #475569;
  background: rgba(15, 23, 42, 0.05);
  border: 1px solid rgba(15, 23, 42, 0.08);
  padding: 4px 10px;
  border-radius: 10px;
}
.grid {
  display: grid;
  grid-template-columns: 110px repeat(12, 1fr);
  gap: 6px;
  align-items: center;
}
.cell {
  min-height: 64px;
  border: 1px solid rgba(15, 23, 42, 0.06);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.cell.header {
  height: 32px;
  font-size: 12px;
  color: #475569;
  background: rgba(15, 23, 42, 0.03);
}
.cell.row-label {
  font-weight: 600;
  font-size: 13px;
  color: #111827;
  justify-content: flex-start;
  padding-left: 8px;
}
.cell.ring-cell {
  height: 64px;
  padding: 4px;
}
.cell.ring-cell svg {
  width: 60px;
  height: 60px;
}
.placeholder {
  padding: 16px;
  color: #6b7280;
  text-align: center;
  border: 1px dashed rgba(15, 23, 42, 0.1);
  border-radius: 10px;
}
@media (max-width: 1100px) {
  .grid {
    overflow-x: auto;
    padding-bottom: 6px;
  }
}
</style>
