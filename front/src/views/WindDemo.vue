<template>
  <div style="width:100%;height:100vh;display:flex;flex-direction:column;">
    <div style="padding:8px;background:#fff;z-index:20;">
      <button @click="loadSample">加载示例（2018-01-01）</button>
      <label style="margin-left:12px">lengthScale:
        <input type="range" min="0.2" max="6" step="0.2" v-model.number="lengthScale"/>
        {{lengthScale}}
      </label>
    </div>
    <div style="flex:1;position:relative;">
      <WindMap :data="points" :lengthScale="lengthScale" :speedRange="[0,20]" />
    </div>
  </div>
</template>

<script>
import WindMap from '../components/WindMap.vue';
import { registerMap } from 'echarts/core';

export default {
  name: 'WindDemo',
  components: { WindMap },
  data() {
    return {
      points: [],
      lengthScale: 2
    };
  },
  methods: {
    async ensureMap() {
      const MAP_PATHS = [
        '/china.json',
        '/data/china.json',
        'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json',
      ];
      for (const path of MAP_PATHS) {
        try {
          const res = await fetch(path);
          if (!res.ok) continue;
          const geo = await res.json();
          registerMap('china', geo);
          return true;
        } catch (err) {
          // try next
        }
      }
      console.warn('无法加载 china 地图，请将 GeoJSON 放到 public/china.json');
      return false;
    },

    async loadSample() {
      // ensure map registered so WindMap using geo coord won't error
      await this.ensureMap();
      try {
        // 日数据文件（public/data 路径）
        const res = await fetch('/data/2018/01/01/20180101.json');
        const daily = await res.json();

        // 读取 region 坐标映射
        const r = await fetch('/region.json');
        const regions = await r.json();
        const cityMap = new Map();
        for (const rec of regions) {
          // 使用 city 字段为 key（保留可能的简写）
          if (rec.city) {
            cityMap.set(rec.city.replace(/市|区|县$/g, ''), {
              lon: Number(rec.longitude),
              lat: Number(rec.latitude)
            });
          }
        }

        const pts = [];
        for (const item of daily) {
          // city 有时为 "省|市" 或 "省|市|区"，取最后一段或尝试匹配
          let cityRaw = item.city || item.province || '';
          if (cityRaw.includes('|')) {
            const parts = cityRaw.split('|').map(s => s.trim()).filter(Boolean);
            cityRaw = parts[parts.length - 1];
          }
          const cityKey = cityRaw.replace(/市|区|县$/g, '');

          const coord = cityMap.get(cityKey);
          if (!coord) continue;

          const u = Number(item.u);
          const v = Number(item.v);
          if (isNaN(u) || isNaN(v)) continue;

          pts.push({
            lon: coord.lon,
            lat: coord.lat,
            u, v,
            speed: Math.sqrt(u*u + v*v),
            stationName: item.city || item.province
          });
        }

        this.points = pts;
        console.log('loaded points', pts.length);
      } catch (e) {
        console.error('load sample failed', e);
        alert('加载失败，请检查控制台');
      }
    }
  }
};
</script>

<style scoped>
/* demo 页面样式最小化，交由项目样式管理 */
</style>


