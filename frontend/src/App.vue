<script setup>
import { ref } from 'vue';
import Demo from './components/Demo.vue';

// show the demo by default when running under Vite (no python server needed)
const showDemo = ref(true);

function openDemo() { showDemo.value = true; }
function closeDemo() { showDemo.value = false; }
</script>

<template>
  <div>
    <div class="app-header">
      <h2>China-VIS2021 — Demo</h2>
      <div style="margin-left:auto;">
        <button @click="showDemo = !showDemo">{{ showDemo ? '关闭 Demo' : '打开 Demo' }}</button>
      </div>
    </div>

    <div v-if="showDemo" style="padding:12px">
      <Demo />
    </div>
  </div>
</template>

<style scoped>
.logo { height: 3.2em; }
h2 { color: #111; }
.app-header { background:#000; color:#fff; padding:12px 16px; display:flex; align-items:center; gap:12px; border-radius:6px; margin:12px; }
.app-header h2 { color:#fff; margin:0 }
</style>
