<template>
  <div class="field">
    <label>年份</label>
    <select :value="currentYear" @change="$emit('update:year', $event.target.value)">
      <option v-for="y in availableYears" :key="y" :value="y">{{ y }}年</option>
    </select>
  </div>
</template>

<script setup>
defineProps({
  currentYear: { type: String, default: "2013" },
  availableYears: { type: Array, default: () => ["2013"] },
});

defineEmits(["update:year"]);
</script>

<style scoped>
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

select {
  padding: 8px 12px;
  border: 1px solid rgba(18, 24, 40, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.8);
  color: #0f172a;
  font-size: 14px;
  min-width: 80px;
  cursor: pointer;
  transition: all 0.2s ease;
}

select:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(47, 126, 87, 0.1);
}

select:hover {
  border-color: rgba(47, 126, 87, 0.3);
}
</style>
