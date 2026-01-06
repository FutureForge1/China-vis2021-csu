<template>
  <div class="controls">
    <div class="field">
      <label>GRANULARITY</label>
      <select :value="granularity" @change="$emit('update:granularity', $event.target.value)">
        <option value="day">DAY</option>
        <option value="month">MONTH</option>
        <option value="year">YEAR</option>
      </select>
    </div>
    <div class="field">
      <label>DATE</label>
      <select :value="currentDate" @change="$emit('update:date', $event.target.value)">
        <option v-for="d in dateOptions" :key="d" :value="d">{{ d }}</option>
      </select>
    </div>
    <div class="field">
      <label>METRIC</label>
      <select :value="metric" @change="$emit('update:metric', $event.target.value)">
        <option value="pm25">PM2.5</option>
        <option value="pm10">PM10</option>
        <option value="so2">SO₂</option>
        <option value="no2">NO₂</option>
        <option value="co">CO</option>
        <option value="o3">O₃</option>
        <option disabled value="temp">TEMP (N/A)</option>
        <option disabled value="rh">RH (N/A)</option>
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
  background: rgba(0, 0, 0, 0.3);
  padding: 4px 8px;
  border: 1px solid var(--c-border);
  border-radius: 0;
}

label {
  color: var(--c-gray);
  font-size: 10px;
  font-family: var(--font-mono);
  font-weight: bold;
}

select {
  background: transparent;
  color: var(--c-white);
  border: none;
  padding: 2px 4px;
  outline: none;
  font-family: var(--font-mono);
  font-size: 12px;
  cursor: pointer;
}

select:focus {
  color: var(--c-yellow);
}
</style>
