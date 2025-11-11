import os
import json
import pandas as pd
import re

def convert_to_echarts_format(province_data: pd.DataFrame, output_dir: str = 'Data/output/echarts') -> str:
    """从省级时间序列导出简单的 ECharts 兼容 JSON。

    Province_data：每个省份包含“时间”列和数字列或已按时间聚合的 DataFrame。
    该函数写入两个 JSON 文件：timeseries 和 map_series（简化）并返回 output_dir。
    """
    os.makedirs(output_dir, exist_ok=True)

    # 确保时间是日期时间（如果存在）。如果不存在，则继续，但生成单个聚合地图（无时间序列）。
    has_time = 'time' in province_data.columns
    if has_time:
        province_data['time'] = pd.to_datetime(province_data['time'])
    else:
        # 扫描字符串/对象列以查找类似文件名的模式
        for col in province_data.select_dtypes(include=['object']).columns:
            try:
                sample_vals = province_data[col].dropna().astype(str)
                if sample_vals.empty:
                    continue
                # 尝试在整个列中应用推理；如果我们找到至少一个日期就停止
                parsed = sample_vals.map(lambda x: _infer_date_from_string(x))
                if parsed.notna().any():
                    # 使用解析值（NaT 未找到）
                    province_data = province_data.copy()
                    province_data['time'] = pd.to_datetime(parsed)
                    has_time = True
                    print(f"[visualize] 提示: 从列 '{col}' 中推断出时间并添加到 'time' 列（一些行可能为 NaT）。")
                    break
            except Exception:
                continue

        if not has_time:
            print("[visualize] 警告: 输入数据中不包含 'time' 列，且未能从字段中推断出日期；将生成非时序的 map_series，timeseries 为空。")
            pass

    # map_series_data：映射日期 -> 所选指标的 {name, value} 列表（使用第一个数字列）
    numeric_cols = province_data.select_dtypes(include=['number']).columns.tolist()
    if not numeric_cols:
        raise ValueError('province_data 必须包含数值列用于可视化')
    metric = numeric_cols[0]

    map_series = {}
    if has_time:
        for t, grp in province_data.groupby(province_data['time'].dt.strftime('%Y-%m')):
            items = []
            # 假设有一列“admin_name”或按 province+city 组合标识省/市
            if 'admin_name' in province_data.columns:
                for _, row in grp.iterrows():
                    name = row.get('admin_name')
                    val = row.get(metric, 0)
                    items.append({'name': name, 'value': float(val) if pd.notna(val) else None})
            elif 'province' in province_data.columns and 'city' in province_data.columns:
                # 使用 province|city 作为名称（与聚合输出一致）
                agg = grp.groupby(['province', 'city'])[metric].mean().reset_index()
                for _, row in agg.iterrows():
                    name = f"{row['province']}|{row['city']}"
                    items.append({'name': name, 'value': float(row[metric]) if pd.notna(row[metric]) else None})
            else:
                # 后备：宽格式或无法推断时保留空列表
                items = []
            map_series[t] = items
    else:
        # 聚合所有行以生成单个地图快照
        grp = province_data
        items = []
        if 'admin_name' in province_data.columns:
            agg = grp.groupby('admin_name')[metric].mean().reset_index()
            for _, row in agg.iterrows():
                items.append({'name': row['admin_name'], 'value': float(row[metric]) if pd.notna(row[metric]) else None})
        elif 'province' in province_data.columns and 'city' in province_data.columns:
            agg = grp.groupby(['province', 'city'])[metric].mean().reset_index()
            for _, row in agg.iterrows():
                name = f"{row['province']}|{row['city']}"
                items.append({'name': name, 'value': float(row[metric]) if pd.notna(row[metric]) else None})
        map_series['ALL'] = items

    timeseries = []
    # 如果我们有时间，请为每个 admin/省市 生成时间序列；否则将时间序列留空
    if has_time:
        if 'admin_name' in province_data.columns:
            for name, grp in province_data.groupby('admin_name'):
                series = {'name': name, 'type': 'line', 'data': []}
                for _, row in grp.sort_values('time').iterrows():
                    ts = int(pd.to_datetime(row['time']).timestamp() * 1000)
                    series['data'].append([ts, float(row.get(metric, 0)) if pd.notna(row.get(metric, None)) else None])
                timeseries.append(series)
        elif 'province' in province_data.columns and 'city' in province_data.columns:
            # 使用 province|city 组合作为系列名称
            for (prov, city), grp in province_data.groupby(['province', 'city']):
                name = f"{prov}|{city}"
                series = {'name': name, 'type': 'line', 'data': []}
                for _, row in grp.sort_values('time').iterrows():
                    ts = int(pd.to_datetime(row['time']).timestamp() * 1000)
                    series['data'].append([ts, float(row.get(metric, 0)) if pd.notna(row.get(metric, None)) else None])
                timeseries.append(series)

    with open(os.path.join(output_dir, 'map_series_data.json'), 'w', encoding='utf-8') as f:
        json.dump(map_series, f, ensure_ascii=False, indent=2)

    with open(os.path.join(output_dir, 'timeseries_data.json'), 'w', encoding='utf-8') as f:
        json.dump(timeseries, f, ensure_ascii=False, indent=2)

    print(f"ECharts 数据已保存到: {output_dir}")
    return output_dir

# 尝试从可能包含文件名或路径的字符串列中推断日期（例如文件名中包含 20130101 / 2013-01-01 / 201301）
def _infer_date_from_string(s: str):
    if not isinstance(s, str):
        return None
    s = s.strip()
    # 年月日
    m = re.search(r"(\d{8})", s)
    if m:
        try:
            return pd.to_datetime(m.group(1), format='%Y%m%d')
        except Exception:
            pass
    # YYYY-MM-DD 或 YYYY_MM_DD 或 YYYY.MM.DD
    m = re.search(r"(\d{4}[-_.]\d{2}[-_.]\d{2})", s)
    if m:
        try:
            return pd.to_datetime(m.group(1).replace('_', '-').replace('.', '-'))
        except Exception:
            pass
    # YYYYMM（视为 YYYY-MM-01）
    m = re.search(r"(\d{6})", s)
    if m:
        try:
            return pd.to_datetime(m.group(1), format='%Y%m')
        except Exception:
            pass
    return None