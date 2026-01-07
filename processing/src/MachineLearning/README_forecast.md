# Forecast Pipeline (PyTorch)

## What it does
- Trains a GRU forecaster on 2013-2018 city daily data under `front/public/data`.
- Predicts 2019 daily pollutants, wind (u,v), meteorology and saves to `front/public/data/predictions/<year>/<month>/<day>/<yyyymmdd>.json`.
- Keeps field names aligned with the frontend (`pm25`, `pm10`, `so2`, `no2`, `co`, `o3`, `u`, `v`, `temp`, `rh`, `psfc`).

## Quick start (recommended conda env)
```bash
conda create -n aqi-forecast python=3.10 -y
conda activate aqi-forecast
# Install PyTorch (GPU version, CUDA 12.1) using pip (faster than conda)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install numpy
cd processing/src/MachineLearning
python forecast.py --data-root ../../front/public/data --out ../../front/public/data/predictions
```
Notes:
- GPU will be used automatically if available (`--device` flag).
- Adjust `--epochs`, `--window`, `--hidden` for quality/perf trade-offs.

## Visualization ideas (hook into frontend)
- **Map overlay**: add a toggle to MapPanel to load `front/public/data/predictions/2019/...` instead of actuals, color by `pm25` and use predicted `u,v` for arrows.
- **Existing charts**: reuse MonthlyRing/TrendLine by pointing the data loader at the predictions directory when "Predicted" mode is on.
- **3D view**: use Three.js (via Vite) to extrude bars on the map grid; height = AQI or pm25, arrow = wind vector; animate through dates.
- **Side-by-side**: add a compare toggle to show actual vs predicted for 2019 using the existing line/rain charts.

## How it works (code map)
- `forecast.py`: end-to-end train + inference. Key pieces:
  - `load_city_timeseries`: reads all JSON daily files for selected years.
  - `SeqDataset`: sliding window dataset (default window=30 days, horizon=1 day).
  - `GRUForecaster`: lightweight GRU with LayerNorm head.
  - `autoregressive_predict`: rolls predictions over 2019 days using previous predictions as context.
  - `save_predictions`: writes per-day JSON arrays (append if multiple cities share a file).

## Practical tips
- If RAM is tight, lower `--batch-size` (e.g., 16) or `--window`.
- To resume faster experiments, cut `--epochs` to 3-4 then bump once it trains end-to-end.
- To focus on AQI only, change `FEATURES` in `forecast.py` to just `pm25` or `aqi` (after adding it to the loader if needed).
