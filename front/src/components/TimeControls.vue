<template>
  <div class="controls">
    <div class="field">
      <label>粒度</label>
      <select :value="granularity" @change="$emit('update:granularity', $event.target.value)">
        <option value="day">日</option>
        <option value="month" disabled>月（待扩展）</option>
        <option value="year" disabled>年（待扩展）</option>
      </select>
    </div>
    <div class="field">
      <label>日期</label>
      <select :value="currentDate" @change="$emit('update:date', $event.target.value)">
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>
    <div class="field">
      <label>指标</label>
      <select :value="metric" @change="$emit('update:metric', $event.target.value)">
        <option value="pm25">PM2.5</option>
        <option value="pm10">PM10</option>
        <option value="so2">SO₂</option>
        <option value="no2">NO₂</option>
        <option value="co">CO</option>
        <option value="o3">O₃</option>
        <option disabled value="temp">气温（待对齐量纲）</option>
        <option disabled value="rh">相对湿度（待对齐量纲）</option>
      </select>
    </div>
  </div>
 </template>

<script setup>
defineProps({
  granularity: { type: String, default: "day" },
  metric: { type: String, default: "pm25" },
  dateOptions: { type: Array, default: () => [] },
  currentDate: { type: String, default: "" },
});

defineEmits(["update:granularity", "update:metric", "update:date"]);
</script>

<style scoped>
.controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.field {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #0f1621;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid #30363d;
}

label {
  color: #9eb1c7;
  font-size: 13px;
}

select {
  background: #0f1621;
  color: #e6edf3;
  border: 1px solid #30363d;
  border-radius: 6px;
  padding: 4px 8px;
}
</style>
