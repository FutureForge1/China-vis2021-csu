<template>
  <div style="width:100%;height:100vh;display:flex;flex-direction:column;">
    <div style="padding:8px;background:#fff;z-index:20;">
      <button @click="loadSample">加载示例（2018-01-01）</button>
      <label style="margin-left:12px">lengthScale:
        <input type="range" min="0.2" max="20" step="0.2" v-model.number="lengthScale"/>
        {{lengthScale}}
      </label>
    </div>
    <div style="flex:1;position:relative;">
      <WindMap :data="points" :lengthScale="lengthScale" :speedRange="[0,20]" />
      <div>aaa</div>
    </div>
  </div>
</template>

<script>
import WindMap from '../components/WindMap.vue';
import { registerMap } from 'echarts/core';
console.log('载入了winddemo.vue')
export default {
  name: 'WindDemo',
  components: { WindMap },
  data() {
    return {
      points: [],
      lengthScale: 2
    };
  },
  mounted() {
    console.log('[WindDemo] mounted: auto-loading sample');
    // do not await to avoid blocking render; errors will appear in console
    this.loadSample().catch((e) => console.warn('[WindDemo] auto load failed', e));
  },
  methods: {
    async ensureMap() {
      const MAP_PATHS = [
        '/china_city.json',
        'https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json',
      ];
      console.log('[WindDemo] ensureMap: try load paths', MAP_PATHS);
      for (const path of MAP_PATHS) {
        try {
          console.log('[WindDemo] ensureMap: fetching', path);
          const res = await fetch(path);
          console.log('[WindDemo] ensureMap: fetched', path, 'ok=', res.ok, 'status=', res.status);
          if (!res.ok) continue;
          const geo = await res.json();
          console.log('[WindDemo] ensureMap: registerMap china from', path);
          registerMap('china', geo);
          console.log('[WindDemo] ensureMap: registerMap success for china');
          return true;
        } catch (err) {
          console.warn('[WindDemo] ensureMap: failed to load', path, err);
          // try next
        }
      }
      console.warn('无法加载 china 地图，请将 GeoJSON 放到 public/china.json');
      return false;
    },

    async loadSample() {
      // ensure map registered so WindMap using geo coord won't error
      await this.ensureMap();
      console.log('[WindDemo] loadSample: ensureMap completed');
      try {
        console.log('[WindDemo] loadSample: fetching daily data /data/2018/01/01/20180101.json');
        // 日数据文件（public/data 路径）
        const res = await fetch('/data/2018/01/01/20180101.json');
        console.log('[WindDemo] loadSample: daily fetch ok=', res.ok, 'status=', res.status);
        const daily = await res.json();
        console.log('[WindDemo] loadSample: daily length=', Array.isArray(daily)?daily.length:typeof daily);

        // 读取 region 坐标映射
        console.log('[WindDemo] loadSample: fetching region.json');
        const r = await fetch('/region.json');
        console.log('[WindDemo] loadSample: region fetch ok=', r.ok, 'status=', r.status);
        const regions = await r.json();
        console.log('[WindDemo] loadSample: regions length=', Array.isArray(regions)?regions.length:typeof regions);
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
        console.log('[WindDemo] loadSample: cityMap size=', cityMap.size);

        const pts = [];
        const missingCities = new Set();
        for (const item of daily) {
          // city 有时为 "省|市" 或 "省|市|区"，取最后一段或尝试匹配
          let cityRaw = item.city || item.province || '';
          if (cityRaw.includes('|')) {
            const parts = cityRaw.split('|').map(s => s.trim()).filter(Boolean);
            cityRaw = parts[parts.length - 1];
          }
          const cityKey = cityRaw.replace(/市|区|县$/g, '');

          const coord = cityMap.get(cityKey);
          if (!coord) {
            missingCities.add(cityKey);
            continue;
          }

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
        console.log('[WindDemo] loadSample: points sample', pts.slice(0,3));
        console.log('[WindDemo] loadSample: missingCities sample', Array.from(missingCities).slice(0,10), 'total missing:', missingCities.size);
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


