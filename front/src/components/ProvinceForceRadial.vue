<template>
  <div id="province-force-radial" class="chart-container"></div>
</template>

<script>
import * as d3 from 'd3';

export default {
  name: 'ProvinceForceRadial',
  props: {
    data: {
      type: Array,
      required: true,
    },
  },
  mounted() {
    this.createForceRadialChart();
  },
  methods: {
    createForceRadialChart() {
      const width = 800;
      const height = 800;
      const radius = 300;

      const svg = d3
        .select('#province-force-radial')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .append('g')
        .attr('transform', `translate(${width / 2}, ${height / 2})`);

      const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

      const simulation = d3.forceSimulation(this.data)
        .force('center', d3.forceCenter(0, 0))
        .force('charge', d3.forceManyBody().strength(-50))
        .force(
          'radial',
          d3.forceRadial((d) => radius * d.balanceFactor).strength(0.1)
        )
        .on('tick', ticked);

      const node = svg
        .selectAll('circle')
        .data(this.data)
        .enter()
        .append('circle')
        .attr('r', 5)
        .attr('fill', (d) => colorScale(d.category));

      function ticked() {
        node.attr('cx', (d) => d.x).attr('cy', (d) => d.y);
      }
    },
  },
};
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
}
</style>
