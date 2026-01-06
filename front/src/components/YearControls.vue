<template>
  <div class="field">
    <label>YEAR</label>
    <select :value="currentYear" @change="$emit('update:year', $event.target.value)">
      <option v-for="y in availableYears" :key="y" :value="y">{{ y }}</option>
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
  font-size: 10px;
  font-weight: bold;
  color: var(--c-gray);
  text-transform: uppercase;
  font-family: var(--font-mono);
}

select {
  padding: 4px 8px;
  border: 1px solid var(--c-border);
  border-radius: 0;
  background: rgba(0, 0, 0, 0.3);
  color: var(--c-white);
  font-size: 12px;
  font-family: var(--font-mono);
  min-width: 80px;
  cursor: pointer;
  outline: none;
}

select:focus {
  border-color: var(--c-yellow);
}

select:hover {
  border-color: var(--c-white);
}
</style>
