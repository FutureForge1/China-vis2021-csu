# China VIS Frontend (Vue + ECharts)

## 开发启动
```bash
cd front
npm install
npm run dev
```

## 数据准备
- 将转换后的日级 JSON 放到 `front/public/data/2013/1/DD/201301DD.json`。推荐直接从仓库根目录运行：
  ```bash
  python processing/convert_processed_city_month_to_json.py --month resources/processed/city/2013/01 --out front/public/data/2013/1
  ```
- 确保索引文件存在：`front/public/data/2013/1/index.json`（已提供 1 月 31 天列表）。
- 在 `front/public/china.json` 放置全国 GeoJSON，用于地图底图。

## 页面
- `src/App.vue` 组织布局（地图、等级条、趋势线、线圈图、筛选控件）。
- 组件位于 `src/components/`，数据加载与聚合逻辑在 `src/utils/dataLoader.js`。

## 下一步可扩展
- 增加月/年粒度数据源与聚合逻辑。
- 引入小时级数据，在趋势图中切换粒度。
- 为地图添加城市/省份点击联动其他图表。
