<template>
  <div ref="chart" style="width:100%;height:100%"></div>
</template>

<script>
import * as echarts from 'echarts';

export default {
  name: 'WindMap',
  props: {
    // data: [{lon, lat, u, v, speed?, stationName?}, ...]
    data: { type: Array, required: true },
    // 控制线段长度缩放（像素 / (m/s)）
    lengthScale: { type: Number, default: 2 },
    // 风速颜色映射范围 [min, max]
    speedRange: { type: Array, default: () => [0, 20] },
    // 是否显示箭头末端三角形
    showArrowHead: { type: Boolean, default: true }
  },
  data() {
    return {
      chart: null
    };
  },
  mounted() {
    this.chart = echarts.init(this.$refs.chart);
    window.addEventListener('resize', this.onResize);
    this.renderChart();
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.onResize);
    if (this.chart) this.chart.dispose();
  },
  watch: {
    data: { handler: 'renderChart', deep: true },
    lengthScale: 'renderChart',
    speedRange: 'renderChart'
  },
  methods: {
    onResize() {
      if (this.chart) this.chart.resize();
    },

    // 线性插色（浅橙 -> 深红）
    colorForSpeed(s) {
      const [minS, maxS] = this.speedRange;
      const t = Math.max(0, Math.min(1, (s - minS) / (maxS - minS)));
      if (t < 0.5) {
        const tt = t / 0.5;
        return this.lerpColor('#ffd8b1', '#ff6b6b', tt);
      } else {
        const tt = (t - 0.5) / 0.5;
        return this.lerpColor('#ff6b6b', '#9e1b1b', tt);
      }
    },

    lerpColor(a, b, t) {
      const ah = a.replace('#', ''), bh = b.replace('#', '');
      const ar = parseInt(ah.substring(0,2),16), ag = parseInt(ah.substring(2,4),16), ab = parseInt(ah.substring(4,6),16);
      const br = parseInt(bh.substring(0,2),16), bg = parseInt(bh.substring(2,4),16), bb = parseInt(bh.substring(4,6),16);
      const rr = Math.round(ar + (br-ar)*t);
      const rg = Math.round(ag + (bg-ag)*t);
      const rb = Math.round(ab + (bb-ab)*t);
      return '#' + ((1<<24) + (rr<<16) + (rg<<8) + rb).toString(16).slice(1);
    },

    renderChart() {
      if (!this.chart) return;
      const seriesData = (this.data || []).map(d => ({
        lon: Number(d.lon),
        lat: Number(d.lat),
        u: Number(d.u) || 0,
        v: Number(d.v) || 0,
        speed: d.speed !== undefined ? Number(d.speed) : Math.sqrt((Number(d.u)||0)**2 + (Number(d.v)||0)**2),
        stationName: d.stationName || (d.city || '')
      })).filter(d => !isNaN(d.lon) && !isNaN(d.lat));

      const lengthScale = this.lengthScale;
      const speedRange = this.speedRange;
      const showArrow = this.showArrowHead;
      const colorFn = (s) => this.colorForSpeed(s);

      const option = {
        geo: {
          roam: true,
          silent: true,
          z: 0
        },
        tooltip: {
          trigger: 'item',
          formatter: (params) => {
            const d = params.data || {};
            return `${d.stationName || ''}<br/>speed: ${d.speed?.toFixed ? d.speed.toFixed(2) : d.speed}`;
          }
        },
        series: [{
          type: 'custom',
          name: 'wind-field',
          coordinateSystem: 'geo',
          renderItem: (params, api) => {
            const item = params.data;
            if (!item) return null;
            const coord = api.coord([item.lon, item.lat]);
            const x = coord[0], y = coord[1];

            const u = Number(item.u) || 0;
            const v = Number(item.v) || 0;
            const speed = item.speed !== undefined ? Number(item.speed) : Math.sqrt(u*u + v*v);

            const dx = u * lengthScale;
            const dy = -v * lengthScale; // canvas y downwards

            const x2 = x + dx;
            const y2 = y + dy;

            const color = colorFn(speed);
            const lw = Math.max(1, Math.min(3.5, 0.4 + speed / 6));

            const children = [
              {
                type: 'line',
                shape: { x1: x, y1: y, x2: x2, y2: y2 },
                style: {
                  stroke: color,
                  lineWidth: lw,
                  lineCap: 'round',
                  lineJoin: 'round'
                }
              }
            ];

            if (showArrow) {
              // draw arrowhead triangle
              const len = Math.sqrt(dx*dx + dy*dy) || 1;
              const ux = dx / len, uy = dy / len;
              const baseX = x2 - ux * 4, baseY = y2 - uy * 4;
              const px = -uy * 2, py = ux * 2;
              children.push({
                type: 'polygon',
                shape: {
                  points: [
                    [x2, y2],
                    [baseX + px, baseY + py],
                    [baseX - px, baseY - py]
                  ]
                },
                style: { fill: color, stroke: color }
              });
            }

            return {
              type: 'group',
              children
            };
          },
          data: seriesData,
          silent: false,
          z: 10
        }]
      };

      this.chart.setOption(option, { notMerge: true });
    }
  }
};
</script>

<style scoped>
/* 组件容器应由父元素控制大小 */
</style>


