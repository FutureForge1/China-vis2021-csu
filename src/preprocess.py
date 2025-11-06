import os
import sys
import shutil
from typing import Optional, List, Tuple, Dict
import xarray as xr, io
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import threading
import time
from .io_utils import record_tmp_dir, read_nc_bytes, read_nc_from_zip
from .remove_outliers import remove_physical_bounds, remove_iqr_outliers
from . import config as _config
from .config import PROCESSED_DIR, DEFER_CLEANUP, VAR_BOUNDS, IQR_K, IQR_GROUPBY

# Fallback default
DEFAULT_AGGREGATE_MEAN = getattr(_config, 'DEFAULT_AGGREGATE_MEAN', True)


def _save_df_by_year_granularity(df: pd.DataFrame, day_basename: str, granularity: str) -> str:
    """Save dataframe into PROCESSED_DIR organized by year/month/day and granularity.

    day_basename expected format 'YYYYMMDD' (8 chars). If not present, save under year=unknown.
    Returns the saved file path.
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
    """Turn a list of in-memory grid dicts into a DataFrame.

    If aggregate_mean is True, compute per-grid mean across items (fast, no time column).
    Each item should include 'lat' and 'lon' arrays (2D or 1D) and zero or more variable arrays.
    """
    if not items:
        return pd.DataFrame()

    # Fast mean-aggregation path
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

    # Full flattening path (one row per grid cell per item)
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


def process_single_zip(zip_path: str,
                       granularity: str = 'grid',
                       admin_geojson: Optional[str] = None,
                       amap_key: Optional[str] = None,
                       aggregate_mean: bool = DEFAULT_AGGREGATE_MEAN) -> str:
    """Process one zip file (contains a day's hourly .nc files) and save result.

    Uses read_nc_from_zip from io_utils to avoid manual extraction when possible.
    Returns saved file path (parquet or csv).
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

    # read the first .nc in zip (io_utils can return ds and tmp_dir)
    ds, tmp_dir = read_nc_from_zip(zip_path)
    # optional debug prints controlled by PREPROCESS_DEBUG
    _debug = os.environ.get('PREPROCESS_DEBUG', '') == '1'
    if _debug:
        try:
            print(f"[task-debug] opened dataset for {zip_path}; tmp_dir={tmp_dir}")
            sys.stdout.flush()
        except Exception:
            pass
    try:
        # build hourly item from ds following run_single_day_quick pattern
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
        # time: try to infer from filename, keep simple date string
        item['time'] = day_basename

        if _debug:
            try:
                print(f"[task-debug] built item arrays; vars_present={[k for k in item.keys() if k not in ('lat','lon','time','geometry')]}")
                sys.stdout.flush()
            except Exception:
                pass

        # create day_df using temporal_aggregation; use aggregate_mean to avoid explosion
        day_df = temporal_aggregation([item], aggregation='daily', aggregate_mean=aggregate_mean)

        if _debug:
            try:
                print(f"[task-debug] temporal_aggregation done; rows={len(day_df)} cols={list(day_df.columns)[:10]}")
                sys.stdout.flush()
            except Exception:
                pass

        # 地理上合理性过滤：移除缺失或明显超出经纬度范围的点（以减少后续分组/统计的异常开销）
        try:
            if 'lat' in day_df.columns and 'lon' in day_df.columns:
                # drop rows with missing coordinates
                before_geo = len(day_df)
                day_df = day_df.dropna(subset=['lat', 'lon'])
                # valid ranges
                lat_mask = (day_df['lat'] >= -90.0) & (day_df['lat'] <= 90.0)
                lon_mask = (day_df['lon'] >= -180.0) & (day_df['lon'] <= 180.0)
                day_df = day_df[lat_mask & lon_mask]
                if _debug:
                    try:
                        print(f"[geo-debug] filtered geographic rows: before={before_geo} after={len(day_df)}")
                        sys.stdout.flush()
                    except Exception:
                        pass
        except Exception:
            pass

        # ensure expected numeric vars exist
        expected_vars = ['pm25', 'pm10', 'so2', 'no2', 'co', 'o3', 'temp', 'rh', 'psfc', 'u', 'v']
        for v in expected_vars:
            if v not in day_df.columns:
                day_df[v] = pd.NA
            else:
                day_df[v] = pd.to_numeric(day_df[v], errors='coerce')

        # apply physical bounds where available
        if VAR_BOUNDS:
            try:
                day_df = remove_physical_bounds(day_df, VAR_BOUNDS, inplace=False)
            except Exception:
                pass

        # IQR outlier removal
        groupby_cols = IQR_GROUPBY if IQR_GROUPBY else ['lat', 'lon']
        numeric_cols = [c for c in expected_vars if c in day_df.columns]
        try:
            if numeric_cols:
                # debug: show sizes before heavy IQR operation
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

                # allow skipping IQR via env var for faster runs
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
        except Exception:
            pass

        if _debug:
            try:
                print(f"[task-debug] after outlier removal; rows={len(day_df)}")
                sys.stdout.flush()
            except Exception:
                pass

        # filter to China and aggregate to admin if requested
        # Optimization: map UNIQUE rounded coordinates (lat/lon) once, then merge back.
        # This mirrors run_single_day_quick behavior and avoids repeated heavy spatial joins
        if granularity in ('city', 'province') and admin_geojson and os.path.exists(admin_geojson):
            from .geo_utils import map_points_to_admin, canonicalize_admin_mapping

            try:
                coords = day_df[['lat', 'lon']].dropna().copy()
                coords['_lat_r'] = coords['lat'].round(4)
                coords['_lon_r'] = coords['lon'].round(4)
                coords_unique = coords[['_lat_r', '_lon_r']].drop_duplicates().reset_index(drop=True).rename(columns={'_lat_r': 'lat', '_lon_r': 'lon'})

                # map only unique rounded coords
                mapped_coords = map_points_to_admin(coords_unique, admin_geojson, level=granularity)
                # debug information about mapping
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

                # ensure admin name column exists
                if 'admin_name' not in mapped_coords.columns:
                    candidates = [c for c in mapped_coords.columns if any(tok in c.upper() for tok in ['NL_NAME_2','NL_NAME_1','NAME_2','NAME_1','PROVINCE','CITY','NL_NAME'])]
                    if candidates:
                        mapped_coords = mapped_coords.rename(columns={candidates[0]: 'admin_name'})

                # keep only necessary columns lat/lon/admin
                keep_cols = ['lat', 'lon']
                for c in ('admin_name', 'province', 'city'):
                    if c in mapped_coords.columns:
                        keep_cols.append(c)
                mapped_coords = mapped_coords[[c for c in keep_cols if c in mapped_coords.columns]]
                # rename back to rounded keys for merge
                mapped_coords = mapped_coords.rename(columns={'lat': '_lat_r', 'lon': '_lon_r'})

                # merge back using rounded coords
                day_df['_lat_r'] = day_df['lat'].round(4)
                day_df['_lon_r'] = day_df['lon'].round(4)
                merged = day_df.merge(mapped_coords, how='left', left_on=['_lat_r', '_lon_r'], right_on=['_lat_r', '_lon_r'])

                # canonicalize admin mapping (fill english if needed)
                before_rows = len(merged)
                merged, stats = canonicalize_admin_mapping(merged, fill_english_if_missing=True, sample_limit=50)

                # Mirror run_single_day_quick: report mapping stats and english-samples used to fill missing Chinese names
                after_rows = stats.get('after_rows', len(merged))
                filled_count = stats.get('filled_count', 0)
                try:
                    print(f'空间映射后保留 {after_rows} / {before_rows} 行 (其中用英文替代中文名的填充次数: {filled_count})')
                except Exception:
                    pass
                if stats.get('english_samples'):
                    try:
                        print('使用英文名作为替代（示例，不含经纬）:')
                        shown = 0
                        for pe, ce in stats.get('english_samples', []):
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

                # If canonicalize missed some names, try explicit english-column fallback for rows
                # where admin_name/province/city are still missing. If still missing after fallback, drop the row.
                try:
                    # candidate english-like columns
                    cand_tokens = ['NAME_2', 'NAME_1', 'VARNAME', 'EN', 'ENG', 'NL_NAME', 'CITY', 'PROVINCE']
                    cand_cols = [c for c in merged.columns if any(tok in c.upper() for tok in cand_tokens)]
                    fill_from_english = 0
                    # rows where all admin identifiers are missing
                    missing_idx = merged[merged[['admin_name', 'province', 'city']].isna().all(axis=1)].index.tolist()
                    for idx in missing_idx:
                        for c in cand_cols:
                            try:
                                v = merged.at[idx, c]
                            except Exception:
                                v = None
                            if pd.notna(v) and str(v).strip():
                                cu = c.upper()
                                if 'NAME_2' in cu or 'VARNAME' in cu or 'CITY' in cu:
                                    merged.at[idx, 'city'] = v
                                elif 'NAME_1' in cu or 'PROVINCE' in cu:
                                    merged.at[idx, 'province'] = v
                                else:
                                    merged.at[idx, 'admin_name'] = v
                                fill_from_english += 1
                                break
                    # after attempting fill, drop rows that still lack any admin identifier
                    before_drop = len(merged)
                    mask_keep = (~merged['admin_name'].isna()) | (~merged['province'].isna()) | (~merged['city'].isna())
                    merged = merged[mask_keep].copy()
                    dropped = before_drop - len(merged)
                    if _debug:
                        try:
                            print(f"[task-debug] english-fallback filled: {fill_from_english}; dropped rows with no admin info: {dropped}")
                            sys.stdout.flush()
                        except Exception:
                            pass
                except Exception:
                    pass

                # ensure numeric and aggregate
                for v in expected_vars:
                    if v not in merged.columns:
                        merged[v] = pd.NA
                    merged[v] = pd.to_numeric(merged[v], errors='coerce')

                # aggregate numeric columns by province + city (Chinese names preferred)
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
                # mapping/aggregation failed; fallback to grid-level save and log the error
                if _debug:
                    try:
                        print(f"[task-debug] admin mapping failed for {zip_path}: {e}")
                        import traceback; traceback.print_exc()
                        sys.stdout.flush()
                    except Exception:
                        pass
                # continue to fallback to grid-level save below
                pass

        # default: grid-level save (drop time column to match previous behaviour)
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
        try:
            ds.close()
        except Exception:
            pass
        try:
            if tmp_dir:
                if DEFER_CLEANUP:
                    record_tmp_dir(tmp_dir)
                else:
                    shutil.rmtree(tmp_dir)
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
    """
    使用 ThreadPoolExecutor 以避免 netCDF / HDF5 在多进程下的锁竞争问题（Windows 下常见）。
    保持原有接口与返回值： (saved_list, failures)
    """
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
        # start a heartbeat thread when debugging to show periodic progress
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
        # Iterate as futures complete; this is simpler and avoids subtle bugs with wait/pending sets
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
            # periodic progress heartbeat
            if completed_count % 10 == 0 or completed_count == total:
                print(f"progress... {completed_count}/{total} completed; failed {len(failed)}")

    return saved, failed

