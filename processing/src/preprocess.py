import os
import sys
import shutil
from typing import Optional, List, Tuple, Dict
import xarray as xr, io
import zipfile
import numpy as np
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from .util.io_utils import record_tmp_dir, read_nc_bytes, read_nc_from_zip
from .remove_outliers import remove_physical_bounds, remove_iqr_outliers
from . import config as _config
from .config import PROCESSED_DIR, DEFER_CLEANUP, VAR_BOUNDS, IQR_K, IQR_GROUPBY
from .util.geo_utils import map_points_to_admin, canonicalize_admin_mapping

# 默认聚合方式
DEFAULT_AGGREGATE_MEAN = getattr(_config, 'DEFAULT_AGGREGATE_MEAN', True)

def _save_df_by_year_granularity(df: pd.DataFrame, day_basename: str, granularity: str) -> str:
    """保存数据框到 PROCESSED_DIR，按年/月/日和粒度组织。

    day_basename 预期格式为 'YYYYMMDD'（8 个字符）。如果不存在，则保存到 year=unknown。
    返回保存的文件路径。
    """
    year = None
    month = None
    day = None
    try:
        if isinstance(day_basename, str) and len(day_basename) >= 8:
            year = int(day_basename[0:4])
            month = int(day_basename[4:6])
            day = int(day_basename[6:8])
    except Exception:
        year = None

    if year is None:
        out_dir = os.path.join(PROCESSED_DIR, str(granularity))
    else:
        out_dir = os.path.join(PROCESSED_DIR, str(granularity), str(year), f"{month:02d}", f"{day:02d}")
    os.makedirs(out_dir, exist_ok=True)
    parquet_path = os.path.join(out_dir, f"{day_basename}.parquet")
    try:
        if os.environ.get('PREPROCESS_DEBUG', '') == '1':
            try:
                print(f"[save-debug] writing parquet to {parquet_path}; rows={len(df)} cols={len(df.columns)}")
                sys.stdout.flush()
            except Exception:
                pass
        df.to_parquet(parquet_path)
        if os.environ.get('PREPROCESS_DEBUG', '') == '1':
            try:
                print(f"[save-debug] parquet write complete: {parquet_path}")
                sys.stdout.flush()
            except Exception:
                pass
        return parquet_path
    except Exception:
        csv_path = os.path.join(out_dir, f"{day_basename}.csv")
        if os.environ.get('PREPROCESS_DEBUG', '') == '1':
            try:
                print(f"[save-debug] parquet write failed, falling back to csv: {csv_path}")
                sys.stdout.flush()
            except Exception:
                pass
        df.to_csv(csv_path, index=False)
        return csv_path

def temporal_aggregation(items: List[dict], aggregation: str = 'daily', aggregate_mean: bool = False) -> pd.DataFrame:
    """将内存中的网格字典列表转换为 DataFrame。

    如果 aggregate_mean 为 True，则计算跨项目的每个网格均值（快速，无时间列）。
    每个项目应包含 'lat' 和 'lon' 数组（2D 或 1D）以及零个或多个变量数组。
    """
    if not items:
        return pd.DataFrame()

    # 快速按均值聚合路径
    if aggregate_mean:
        first = items[0]
        lat = first.get('lat')
        lon = first.get('lon')
        if lat is None or lon is None:
            raise ValueError('items must include lat and lon')
        lat_arr = np.array(lat)
        lon_arr = np.array(lon)
        if lat_arr.ndim == 1 and lon_arr.ndim == 1:
            Lon, Lat = np.meshgrid(lon_arr, lat_arr)
        else:
            Lon = lon_arr
            Lat = lat_arr
        N = Lat.size
        out = {'lat': Lat.ravel().astype(float), 'lon': Lon.ravel().astype(float)}
        # collect variable names
        vars_set = set()
        for it in items:
            vars_set.update([k for k in it.keys() if k not in ('lat', 'lon', 'time', 'geometry')])
        vars_list = sorted(vars_set)
        for v in vars_list:
            stacks = []
            for it in items:
                val = it.get(v)
                try:
                    arr = np.array(val)
                    if arr.size == N:
                        stacks.append(arr.ravel())
                    elif arr.size == 1:
                        stacks.append(np.repeat(arr.item(), N))
                    else:
                        stacks.append(np.repeat(np.nan, N))
                except Exception:
                    stacks.append(np.repeat(np.nan, N))
            if stacks:
                stacked = np.vstack(stacks)
                mean_vals = np.nanmean(stacked, axis=0)
            else:
                mean_vals = np.repeat(np.nan, N)
            out[v] = mean_vals
        df = pd.DataFrame(out)
        return df

    # 将内存中的网格字典列表转换为 DataFrame 的完整展开路径（每个网格单元每个项目一行）
    rows = []
    for it in items:
        lat = it.get('lat')
        lon = it.get('lon')
        time = it.get('time')
        if lat is None or lon is None:
            continue
        lat_arr = np.array(lat)
        lon_arr = np.array(lon)
        if lat_arr.ndim == 1 and lon_arr.ndim == 1:
            Lon, Lat = np.meshgrid(lon_arr, lat_arr)
        else:
            Lon = lon_arr
            Lat = lat_arr
        Lat_flat = Lat.ravel()
        Lon_flat = Lon.ravel()
        N = Lat_flat.size
        var_names = [k for k in it.keys() if k not in ('lat', 'lon', 'time', 'geometry')]
        arrays = {}
        for v in var_names:
            try:
                a = np.array(it.get(v))
                if a.size == N:
                    arrays[v] = a.ravel()
                elif a.size == 1:
                    arrays[v] = np.repeat(a.item(), N)
                else:
                    arrays[v] = np.repeat(np.nan, N)
            except Exception:
                arrays[v] = np.repeat(np.nan, N)
        for i in range(N):
            row = {'lat': float(Lat_flat[i]), 'lon': float(Lon_flat[i]), 'time': time}
            for v, arr in arrays.items():
                row[v] = arr[i] if i < len(arr) else np.nan
            rows.append(row)
    df = pd.DataFrame(rows)
    try:
        df['time'] = pd.to_datetime(df['time'])
    except Exception:
        pass
    return df

# 处理单个 zip 文件
def process_single_zip(zip_path: str,
                       granularity: str = 'grid',
                       admin_geojson: Optional[str] = None,
                       amap_key: Optional[str] = None,
                       aggregate_mean: bool = DEFAULT_AGGREGATE_MEAN) -> str:
    """处理单个 zip 文件（包含一天的每小时 .nc 文件）并保存结果。

    使用 io_utils 中的 read_nc_from_zip 避免手动提取。
    返回保存的文件路径（parquet 或 csv）。
    """
    basename = os.path.basename(zip_path)
    # try to infer date from filename CN-ReanalysisYYYYMMDD.zip
    day_basename = None
    try:
        part = basename.replace('CN-Reanalysis', '').replace('.zip', '')
        day_basename = part[0:8]
    except Exception:
        day_basename = basename.replace('.zip', '')

    print(f"[task] start {zip_path}")
    sys.stdout.flush()

    # 读取 zip 中所有的 .nc 文件并构建每小时的 items 列表（行为与 run_single_day_quick 保持一致）
    items = []
    tmp_dirs = []
    tmp_dir = None
    try:
    # 列出 zip 中的 .nc 成员名
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                nc_names = sorted([n for n in zf.namelist() if n.lower().endswith('.nc')])
        except Exception:
            nc_names = []

        if nc_names:
            for nc_name in nc_names:
                ds = None
                try:
                    # 尝试从 zip 读取字节并在内存中打开
                    raw = None
                    try:
                        raw = read_nc_bytes(zip_path, nc_name)
                    except Exception:
                        raw = None

                    if raw is not None:
                        try:
                            ds = xr.open_dataset(io.BytesIO(raw), engine='h5netcdf')
                        except Exception:
                            try:
                                ds = xr.open_dataset(io.BytesIO(raw))
                            except Exception:
                                ds = None
                    else:
                        # 回退：尝试使用 io_utils 提供的 helper（可能会解压到临时目录）
                        try:
                            ds, t = read_nc_from_zip(zip_path)
                            if t:
                                tmp_dirs.append(t)
                            # when using this fallback the helper may return the first file; accept it
                        except Exception:
                            ds = None

                    if ds is None:
                        continue

                    # 从 ds 构建 item（字段与之前一致）
                    item = {}
                    for var in ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']:
                        if var in ds.variables:
                            try:
                                item[var] = ds[var].values
                            except Exception:
                                item[var] = None
                    if 'lat2d' in ds.variables:
                        item['lat'] = ds['lat2d'].values
                    elif 'lat' in ds.variables:
                        item['lat'] = ds['lat'].values
                    if 'lon2d' in ds.variables:
                        item['lon'] = ds['lon2d'].values
                    elif 'lon' in ds.variables:
                        item['lon'] = ds['lon'].values
                    # 时间字段：继续使用 day_basename
                    item['time'] = day_basename

                    items.append(item)
                finally:
                    try:
                        if ds is not None:
                            ds.close()
                    except Exception:
                        pass
        else:
            # 回退到以前的行为：通过 helper 打开第一个 .nc
            try:
                ds, tmp_dir = read_nc_from_zip(zip_path)
                # build single-item list so temporal_aggregation still works
                item = {}
                for var in ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']:
                    if var in ds.variables:
                        try:
                            item[var] = ds[var].values
                        except Exception:
                            item[var] = None
                if 'lat2d' in ds.variables:
                    item['lat'] = ds['lat2d'].values
                elif 'lat' in ds.variables:
                    item['lat'] = ds['lat'].values
                if 'lon2d' in ds.variables:
                    item['lon'] = ds['lon2d'].values
                elif 'lon' in ds.variables:
                    item['lon'] = ds['lon'].values
                item['time'] = day_basename
                items.append(item)
            except Exception:
                # no usable files found
                items = []
    except Exception:
        items = []
    # 可选的调试打印，通过 PREPROCESS_DEBUG 控制
    _debug = os.environ.get('PREPROCESS_DEBUG', '') == '1'
    if _debug:
        try:
            print(f"[task-debug] opened dataset for {zip_path}; tmp_dir={tmp_dir}")
            sys.stdout.flush()
        except Exception:
            pass

    # 使用 temporal_aggregation 创建 day_df；当使用 aggregate_mean 可避免数据膨胀
    day_df = temporal_aggregation(items, aggregation='daily', aggregate_mean=aggregate_mean)

    if _debug:
        try:
            print(f"[task-debug] temporal_aggregation done; rows={len(day_df)} cols={list(day_df.columns)[:10]}")
            sys.stdout.flush()
        except Exception:
            pass

    # 确保期望的数值列存在
    expected_vars = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']
    for v in expected_vars:
        if v not in day_df.columns:
            day_df[v] = pd.NA
        else:
            day_df[v] = pd.to_numeric(day_df[v], errors='coerce')

    # 在可用时应用物理范围过滤
    if VAR_BOUNDS:
        try:
            day_df = remove_physical_bounds(day_df, VAR_BOUNDS, inplace=False)
        except Exception:
            pass

    # IQR 离群值移除
    groupby_cols = IQR_GROUPBY if IQR_GROUPBY else ['lat', 'lon']
    numeric_cols = [c for c in expected_vars if c in day_df.columns]
    try:
        if numeric_cols:
            # 调试：在执行耗时的 IQR 操作前打印大小信息
            if os.environ.get('PREPROCESS_DEBUG', '') == '1':
                try:
                    nrows = len(day_df)
                    try:
                        # estimate group count
                        grp_count = day_df.groupby(groupby_cols).ngroups if groupby_cols and all(c in day_df.columns for c in groupby_cols) else None
                    except Exception:
                        grp_count = None
                    print(f"[iqr-debug] running remove_iqr_outliers rows={nrows} cols={len(numeric_cols)} groups={grp_count} groupby={groupby_cols} k={IQR_K}")
                    sys.stdout.flush()
                except Exception:
                    pass

            # 允许通过环境变量跳过 IQR（以加速运行）
            if os.environ.get('PREPROCESS_SKIP_IQR', '') == '1':
                if os.environ.get('PREPROCESS_DEBUG', '') == '1':
                    print("[iqr-debug] PREPROCESS_SKIP_IQR=1 set; using global percentile clip instead of group IQR")
                    sys.stdout.flush()
                # Perform global percentile clipping per column to emulate run_single_day_quick behaviour
                cleaned_df = day_df.copy()
                try:
                    clip_low = 0.005
                    clip_high = 0.995
                    for col in numeric_cols:
                        try:
                            ser = pd.to_numeric(cleaned_df[col], errors='coerce')
                            low = ser.quantile(clip_low)
                            high = ser.quantile(clip_high)
                            cleaned_df[col] = ser.clip(lower=low, upper=high)
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                cleaned_df, _ = remove_iqr_outliers(day_df, value_cols=numeric_cols, groupby=groupby_cols, k=IQR_K, return_mask=True)
                day_df = cleaned_df

        if _debug:
            try:
                print(f"[task-debug] after outlier removal; rows={len(day_df)}")
                sys.stdout.flush()
            except Exception:
                pass

    # 将点过滤到中国并按需聚合到行政区
    # 优化：对唯一的四舍五入坐标（lat/lon）做一次映射，然后合并回主表。
        if granularity in ('city', 'province') and admin_geojson and os.path.exists(admin_geojson):
            try:
                coords = day_df[['lat', 'lon']].dropna().copy()
                coords['_lat_r'] = coords['lat'].round(4)
                coords['_lon_r'] = coords['lon'].round(4)
                coords_unique = coords[['_lat_r', '_lon_r']].drop_duplicates().reset_index(drop=True).rename(columns={'_lat_r': 'lat', '_lon_r': 'lon'})

                # 只对唯一的四舍五入坐标进行映射
                mapped_coords = map_points_to_admin(coords_unique, admin_geojson, level=granularity)
                # 映射相关的调试信息
                if _debug:
                    try:
                        print('DEBUG mapped_coords.shape =', getattr(mapped_coords, 'shape', None))
                        print('DEBUG mapped_coords.columns =', list(mapped_coords.columns))
                        try:
                            print('DEBUG mapped_coords sample:\n', mapped_coords.head(10).to_string(index=False))
                        except Exception:
                            pass
                    except Exception:
                        pass

                # 确保存在 admin_name 列
                if 'admin_name' not in mapped_coords.columns:
                    candidates = [c for c in mapped_coords.columns if any(tok in c.upper() for tok in ['NL_NAME_2','NL_NAME_1','NAME_2','NAME_1','PROVINCE','CITY','NL_NAME'])]
                    if candidates:
                        mapped_coords = mapped_coords.rename(columns={candidates[0]: 'admin_name'})

                # 若缺少 'province' 或 'city'，尝试从常见的 GADM 属性名中填充。
                # 这是一个轻量的本地处理逻辑，用于避免当 geojson 使用不同列名时丢失行。
                if 'province' not in mapped_coords.columns:
                    prov_candidates = [c for c in mapped_coords.columns if any(tok in c.upper() for tok in ['NAME_1','NL_NAME_1','PROVINCE','ADM1','PRV'])]
                    if prov_candidates:
                        mapped_coords = mapped_coords.rename(columns={prov_candidates[0]: 'province'})
                if 'city' not in mapped_coords.columns:
                    city_candidates = [c for c in mapped_coords.columns if any(tok in c.upper() for tok in ['NAME_2','NL_NAME_2','CITY','ADM2','CNTY','MUN'])]
                    if city_candidates:
                        mapped_coords = mapped_coords.rename(columns={city_candidates[0]: 'city'})

                # 仅保留必要的列：lat/lon/行政名相关列
                keep_cols = ['lat', 'lon']
                for c in ('admin_name', 'province', 'city'):
                    if c in mapped_coords.columns:
                        keep_cols.append(c)
                mapped_coords = mapped_coords[[c for c in keep_cols if c in mapped_coords.columns]]
                # rename back to rounded keys for merge
                mapped_coords = mapped_coords.rename(columns={'lat': '_lat_r', 'lon': '_lon_r'})

                # 使用四舍五入坐标合并回主表
                day_df['_lat_r'] = day_df['lat'].round(4)
                day_df['_lon_r'] = day_df['lon'].round(4)
                merged = day_df.merge(mapped_coords, how='left', left_on=['_lat_r', '_lon_r'], right_on=['_lat_r', '_lon_r'])

                # 规范化行政映射（必要时填充英文名）
                before_rows = len(merged)
                merged, stats = canonicalize_admin_mapping(merged, fill_english_if_missing=True, sample_limit=50)
                # 将占位字符串（"NA","N/A","<NA>",空串等）标准化为真实的缺失值
                try:
                    placeholders = set(['', 'NA', 'N/A', 'NAN', '<NA>'])
                    for col in ('province', 'city', 'admin_name'):
                        if col in merged.columns:
                            # strip whitespace and convert known placeholders (case-insensitive) to pd.NA
                            def _norm(v):
                                try:
                                    if v is None or (isinstance(v, float) and pd.isna(v)):
                                        return pd.NA
                                    if isinstance(v, str):
                                        s = v.strip()
                                        if s == '':
                                            return pd.NA
                                        if s.upper() in placeholders:
                                            return pd.NA
                                        return s
                                    return v
                                except Exception:
                                    return pd.NA
                            merged[col] = merged[col].apply(_norm)
                except Exception:
                    pass

                # 调试：打印原始 english_samples 的内容/数量，帮助诊断打印分支为何在过滤后被跳过。
                if os.environ.get('PREPROCESS_DEBUG', '') == '1':
                    try:
                        raw_es = stats.get('english_samples')
                        print(f"[debug] raw english_samples count={len(raw_es) if raw_es is not None else 0}; raw={raw_es}")
                    except Exception:
                        pass

                if stats.get('english_samples'):
                    try:
                        print('使用英文名作为替代:')
                        shown = 0
                        # filter out empty or placeholder values
                        samples = []
                        for pe, ce in stats.get('english_samples', []):
                            s_pe = '' if pe is None else str(pe).strip()
                            s_ce = '' if ce is None else str(ce).strip()
                            if s_ce and s_ce.upper() not in ('NA', 'NAN', '<NA>'):
                                samples.append((s_pe, s_ce))
                            elif s_pe and s_pe.upper() not in ('NA', 'NAN', '<NA>'):
                                samples.append((s_pe, s_ce))
                        for pe, ce in samples:
                            if shown >= 50:
                                break
                            if pe and ce:
                                print(f'  {pe} / {ce}')
                            elif ce:
                                print(f'  {ce}')
                            elif pe:
                                print(f'  {pe}')
                            shown += 1
                    except Exception:
                        pass

                # 如果 canonicalize 未能填充某些名称，尝试对仍缺少 admin_name/province/city 的行
                # 使用显式的英文列作为回退。按行从任何可用的英文类列填充；不删除行。最后将剩余的 NaN
                # 用 'UNKNOWN' 替代，确保输出中没有 NaN（注意：此处代码保留为尽量不覆盖已有中文值）。
                try:
                    # Build candidate columns (broad set) but we'll prefer Chinese text when available.
                    cand_cols = [c for c in merged.columns if re.search(r'NAME|EN\b|ENG|VARNAME|NL_NAME|CITY|PROVINCE|ADM', c, re.I)]

                    def _choose_preferred(series_df, candidates):
                        """
                        Choose preferred string per-row from candidates:
                        - First prefer values containing CJK/Chinese characters.
                        - If none contain Chinese, pick the first non-empty candidate (assumed English).
                        - If still none, return NaN (will be dropped later if desired).
                        Returns a pandas Series aligned with series_df.index.
                        """
                        idx = series_df.index
                        out = pd.Series([pd.NA] * len(idx), index=idx, dtype=object)
                        # helper to normalize a column to string but keep NA as NA
                        def _col_series(name):
                            if name not in series_df.columns:
                                return pd.Series([pd.NA] * len(idx), index=idx, dtype=object)
                            s = series_df[name].astype(object).where(series_df[name].notna(), pd.NA)
                            return s

                        # first pass: prefer Chinese characters
                        chinese_re = re.compile(r'[\u4e00-\u9fff]')
                        for c in candidates:
                            s = _col_series(c)
                            mask = s.notna() & s.astype(str).str.strip().ne('') & s.astype(str).str.contains(chinese_re)
                            if mask.any():
                                # fill only where out is not set
                                to_fill = mask & out.isna()
                                out[to_fill] = s[to_fill]
                        # second pass: first non-empty (english/fallback)
                        for c in candidates:
                            s = _col_series(c)
                            mask = s.notna() & s.astype(str).str.strip().ne('')
                            if mask.any():
                                to_fill = mask & out.isna()
                                out[to_fill] = s[to_fill]
                        # leave remaining as pd.NA
                        out = out.replace({pd.NA: pd.NA})
                        return out

                    # Candidate ordering: prefer NAME_1/NAME_2 style then generic city/province columns
                    prov_cands = [c for c in cand_cols if re.search(r'NAME[_\.]?1|PROVINCE|ADM1|VARNAME[_\.]?1|NL_NAME[_\.]?1', c, re.I)] + [c for c in cand_cols if c not in []]
                    city_cands = [c for c in cand_cols if re.search(r'NAME[_\.]?2|CITY|ADM2|VARNAME[_\.]?2|NL_NAME[_\.]?2', c, re.I)] + [c for c in cand_cols if c not in []]

                    # Ensure we don't duplicate columns in candidate lists
                    prov_cands = [c for i, c in enumerate(prov_cands) if c and prov_cands.index(c) == i]
                    city_cands = [c for i, c in enumerate(city_cands) if c and city_cands.index(c) == i]

                    # If canonical columns already present and non-empty, keep them
                    if 'province' in merged.columns and merged['province'].notna().any():
                        prov_series = merged['province'].astype(object).where(merged['province'].notna(), pd.NA)
                    else:
                        prov_series = _choose_preferred(merged, prov_cands)
                    if 'city' in merged.columns and merged['city'].notna().any():
                        city_series = merged['city'].astype(object).where(merged['city'].notna(), pd.NA)
                    else:
                        city_series = _choose_preferred(merged, city_cands)

                        # admin_name：优先保留已存在的 admin_name，否则在可用时由 city/province 组合得到
                    if 'admin_name' in merged.columns and merged['admin_name'].notna().any():
                        admin_series = merged['admin_name'].astype(object).where(merged['admin_name'].notna(), pd.NA)
                    else:
                        # prefer city, then province
                        admin_series = city_series.where(city_series.notna(), prov_series)

                        # 赋值回列（不要覆盖已有的非空值）
                    merged['province'] = merged.get('province').where(merged.get('province').notna(), prov_series)
                    merged['city'] = merged.get('city').where(merged.get('city').notna(), city_series)
                    merged['admin_name'] = merged.get('admin_name').where(merged.get('admin_name').notna(), admin_series)

                    # Note: per your request, we leave rows with no province AND no city as NaN so they can be dropped
                    if _debug:
                        try:
                            prov_count = int(merged['province'].notna().sum()) if 'province' in merged.columns else 0
                            city_count = int(merged['city'].notna().sum()) if 'city' in merged.columns else 0
                            admin_count = int(merged['admin_name'].notna().sum()) if 'admin_name' in merged.columns else 0
                            print(f"[task-debug] after-fallback counts: province={prov_count} city={city_count} admin_name={admin_count}")
                            sys.stdout.flush()
                        except Exception:
                            pass
                except Exception:
                    pass

                # 强制数值列为数值类型并进行聚合
                for v in expected_vars:
                    if v not in merged.columns:
                        merged[v] = pd.NA
                    merged[v] = pd.to_numeric(merged[v], errors='coerce')

                # 以 province+city 为键聚合数值列（优先使用中文名称）
                agg_numeric_cols = [c for c in numeric_cols]
                if 'province' in merged.columns and 'city' in merged.columns:
                    agg = merged.groupby(['province', 'city'])[agg_numeric_cols].mean().reset_index()
                    # drop groups where both province and city are missing
                    try:
                        agg = agg[~(agg['province'].isna() & agg['city'].isna())].copy()
                    except Exception:
                        pass
                elif 'admin_name' in merged.columns:
                    agg = merged.groupby(['admin_name'])[agg_numeric_cols].mean().reset_index()
                else:
                    agg = merged[agg_numeric_cols].mean().to_frame().T

                saved = _save_df_by_year_granularity(agg, day_basename, granularity)
                if _debug:
                    try:
                        print(f"[task-debug] saved aggregated admin file: {saved}")
                        sys.stdout.flush()
                    except Exception:
                        pass
                return saved
            except Exception as e:
            # 映射/聚合失败；回退为网格级别保存并记录错误
                if _debug:
                    try:
                        print(f"[task-debug] admin mapping failed for {zip_path}: {e}")
                        import traceback; traceback.print_exc()
                        sys.stdout.flush()
                    except Exception:
                        pass
                # continue to fallback to grid-level save below
                pass

    # 默认：按网格级别保存（删除 time 列以保持与以前行为一致）
        if 'time' in day_df.columns:
            try:
                day_df = day_df.drop(columns=['time'])
            except Exception:
                pass

        saved = _save_df_by_year_granularity(day_df, day_basename, 'grid')
        if _debug:
            try:
                print(f"[task-debug] saved grid file: {saved}")
                sys.stdout.flush()
            except Exception:
                pass
        return saved

    finally:
    # 关闭任何残留的 dataset（大多数已在上文关闭）并清理临时目录
        try:
            if tmp_dir:
                if DEFER_CLEANUP:
                    record_tmp_dir(tmp_dir)
                else:
                    shutil.rmtree(tmp_dir)
        except Exception:
            pass
        try:
            for t in tmp_dirs:
                if not t:
                    continue
                if DEFER_CLEANUP:
                    record_tmp_dir(t)
                else:
                    try:
                        shutil.rmtree(t)
                    except Exception:
                        pass
        except Exception:
            pass


def _worker_wrapper(args: Tuple) -> Tuple[str, bool, str]:
    zip_path, granularity, admin_geojson, amap_key, aggregate_mean = args
    try:
        res = process_single_zip(zip_path, granularity=granularity, admin_geojson=admin_geojson, amap_key=amap_key, aggregate_mean=aggregate_mean)
        return zip_path, True, res
    except Exception as e:
        return zip_path, False, str(e)



def process_zips_parallel(base_path: str,
                          year: int,
                          granularity: str = 'grid',
                          admin_geojson: Optional[str] = None,
                          workers: int = 4,
                          aggregate_mean: bool = DEFAULT_AGGREGATE_MEAN) -> Tuple[List[str], List[Dict]]:
    zip_paths = []
    # expect files named CN-Reanalysis{YYYY}{MM}{DD}.zip
    for month in range(1, 13):
        for day in range(1, 32):
            name = f"CN-Reanalysis{year}{month:02d}{day:02d}.zip"
            p = os.path.join(base_path, name)
            if os.path.exists(p):
                zip_paths.append(p)

    print(f"found {len(zip_paths)} zip(s) to process in {base_path} for year {year}")
    saved = []
    failed = []
    if not zip_paths:
        return saved, failed

    args_list = [(zp, granularity, admin_geojson, None, aggregate_mean) for zp in zip_paths]

    with ThreadPoolExecutor(max_workers=workers) as ex:
    # 在调试模式下启动心跳线程以周期性显示进度
        _debug = os.environ.get('PREPROCESS_DEBUG', '') == '1'
        stop_event = threading.Event()

        def _heartbeat():
            while not stop_event.is_set():
                try:
                    print(f"heartbeat: completed={completed_count}/{total} failed={len(failed)} workers={workers}")
                    sys.stdout.flush()
                except Exception:
                    pass
                stop_event.wait(5)

        hb_thread = None
        if _debug:
            hb_thread = threading.Thread(target=_heartbeat, daemon=True)
            hb_thread.start()
        futures = {ex.submit(_worker_wrapper, args): args[0] for args in args_list}
        total = len(futures)
        print(f"submitted {total} jobs to thread pool (workers={workers})")
        completed_count = 0
    # 随着 futures 完成逐个处理结果；这种方式更简单并避免与 wait/pending 集合相关的微妙错误
        for fut in as_completed(futures):
            zp = futures.get(fut)
            try:
                file, ok, payload = fut.result()
                if ok:
                    saved.append(payload)
                    print(f"success: {file} -> {payload}")
                else:
                    failed.append({'file': file, 'error': payload})
                    print(f"failed: {file} -> {payload}")
            except Exception as e:
                failed.append({'file': zp, 'error': str(e)})
                print(f"error retrieving result for {zp}: {e}")
            completed_count += 1
            # 周期性进度心跳打印
            if completed_count % 10 == 0 or completed_count == total:
                print(f"progress... {completed_count}/{total} completed; failed {len(failed)}")

    return saved, failed
