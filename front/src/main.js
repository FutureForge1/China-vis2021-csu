import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { UniversalTransition } from "echarts/features";
import {
  LineChart,
  BarChart,
  RadarChart,
  MapChart,
  ScatterChart,
  ParallelChart,
  HeatmapChart,
  LinesChart,
} from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  TitleComponent,
  TimelineComponent,
  DatasetComponent,
  GeoComponent,
  DataZoomComponent,
  ParallelComponent,
  PolarComponent,
} from "echarts/components";
import VChart from "vue-echarts";

use([
  CanvasRenderer,
  UniversalTransition,
  LineChart,
  BarChart,
  RadarChart,
  MapChart,
  ScatterChart,
  ParallelChart,
  HeatmapChart,
  LinesChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  TitleComponent,
  TimelineComponent,
  DatasetComponent,
  GeoComponent,
  DataZoomComponent,
  ParallelComponent,
  PolarComponent,
]);

const app = createApp(App);
app.component("VChart", VChart);
app.use(router);
app.mount("#app");
