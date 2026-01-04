import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";

import { use, registerMap } from "echarts/core";
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
  CalendarComponent,
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
  CalendarComponent,
]);

// Try to register local GeoJSON map before mounting app so components relying on 'china' exist early.
const MAP_PATHS = [
  "/china_city.json",
  "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
];

async function tryRegisterMap() {
  for (const path of MAP_PATHS) {
    try {
      // fetch with timeout
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      const res = await fetch(path, { signal: controller.signal });
      clearTimeout(timeout);
      if (!res.ok) continue;
      const geo = await res.json();
      registerMap("china", geo);
      console.log("[main] registerMap success from", path);
      return;
    } catch (err) {
      console.warn("[main] registerMap failed for", path, err?.message || err);
    }
  }
  console.warn("[main] could not register any china GeoJSON from MAP_PATHS");
}

(async () => {
  await tryRegisterMap();
  const app = createApp(App);
  app.component("VChart", VChart);
  app.use(router);
  app.mount("#app");
})();
