import os
import json
import pandas as pd


def convert_to_echarts_format(province_data: pd.DataFrame, output_dir: str = 'Data/output/echarts') -> str:
    """Export simple ECharts-compatible JSONs from province-level timeseries.

    province_data: DataFrame with 'time' column and numeric columns per province or already-aggregated by time.
    The function writes two JSON files: timeseries and map_series (simplified) and returns output_dir.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Ensure time is datetime
    if 'time' in province_data.columns:
        province_data['time'] = pd.to_datetime(province_data['time'])
    else:
        raise ValueError('province_data 必须包含 time 列')

    # map_series_data: map date -> list of {name, value} for a selected metric (use first numeric column)
    numeric_cols = province_data.select_dtypes(include=['number']).columns.tolist()
    if not numeric_cols:
        raise ValueError('province_data 必须包含数值列用于可视化')
    metric = numeric_cols[0]

    map_series = {}
    for t, grp in province_data.groupby(province_data['time'].dt.strftime('%Y-%m')):
        items = []
        # assume there is a column 'admin_name' or index corresponds to province names
        if 'admin_name' in province_data.columns:
            for _, row in grp.iterrows():
                name = row.get('admin_name')
                val = row.get(metric, 0)
                items.append({'name': name, 'value': float(val) if pd.notna(val) else None})
        else:
            # fallback: use columns as province names if wide-format
            # produce empty list in this fallback
            items = []
        map_series[t] = items

    timeseries = []
    # If data is long-format with admin_name, produce one series per admin
    if 'admin_name' in province_data.columns:
        for name, grp in province_data.groupby('admin_name'):
            series = {'name': name, 'type': 'line', 'data': []}
            for _, row in grp.sort_values('time').iterrows():
                ts = int(pd.to_datetime(row['time']).timestamp() * 1000)
                series['data'].append([ts, float(row.get(metric, 0)) if pd.notna(row.get(metric, None)) else None])
            timeseries.append(series)
    else:
        # wide-format not supported for per-province lines in this simple helper
        pass

    with open(os.path.join(output_dir, 'map_series_data.json'), 'w', encoding='utf-8') as f:
        json.dump(map_series, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'timeseries_data.json'), 'w', encoding='utf-8') as f:
        json.dump(timeseries, f, ensure_ascii=False, indent=2)

    print(f"ECharts 数据已保存到: {output_dir}")
    return output_dir
