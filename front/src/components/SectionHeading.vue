<template>
  <div class="section-heading">
    <div class="section-badge">{{ badge }}</div>
    <div class="section-meta">{{ meta }}</div>
  </div>
</template>

<script setup>
defineProps({
  badge: {
    type: String,
    required: true
  },
  meta: {
    type: String,
    required: true
  }
});
</script>

<style scoped>
.section-heading {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 10px;
}

.section-badge {
  background: #FFE600;
  color: #000;
  padding: 2px 8px;
  font-family: "Oswald", sans-serif;
  font-weight: bold;
  font-size: 18px;
  letter-spacing: 1px;
  white-space: nowrap;
}

.section-meta {
  color: #444;
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
  white-space: nowrap;
}
</style>
