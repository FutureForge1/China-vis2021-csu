import geopandas as gpd
import pandas as pd
import re
from shapely.geometry import Point
import os

# Simple in-memory cache to avoid re-reading/parsing the same GeoJSON on every call.
# Keyed by absolute path. Stores GeoDataFrame already converted to EPSG:4326.
_GADM_CACHE = {}


def _choose_admin_name_column(gdf):
    # 更喜欢常见的列；首选 NL_NAME_1/NL_NAME_2（本地化/中文）（如果可用）
    for c in ['NL_NAME_2', 'NL_NAME_1', 'NL_NAME', 'NAME_2', 'NAME_1', 'NAME', 'name', 'ADM_NAME', 'CITY_NAME', 'province', '市名', '省名']:
        if c in gdf.columns:
            return c
    # 后备：选择第一个非几何、非数字列
    for c in gdf.columns:
        if c == 'geometry':
            continue
        if gdf[c].dtype == object:
            return c
    # 最后的后备
    return gdf.columns[0]


def map_points_to_admin(df: pd.DataFrame, admin_geojson_path: str, level: str = 'city') -> pd.DataFrame:
    """将 df 中的经纬度点映射到 GeoJSON 中的行政多边形。
    返回原始 df，并添加了列“admin_name”和“admin_level”。
    """
    if 'lat' not in df.columns or 'lon' not in df.columns:
        raise ValueError('DataFrame 必须包含 lat 和 lon 列')

    if not os.path.exists(admin_geojson_path):
        raise FileNotFoundError(admin_geojson_path)

    abs_path = os.path.abspath(admin_geojson_path)
    if abs_path in _GADM_CACHE:
        gdf_admin = _GADM_CACHE[abs_path]
    else:
        gdf_admin = gpd.read_file(abs_path)
        # 确保crs是WGS84
        try:
            gdf_admin = gdf_admin.to_crs(epsg=4326)
        except Exception:
            pass
        _GADM_CACHE[abs_path] = gdf_admin

    # 构建点 gdf
    pts = gpd.GeoDataFrame(df.copy(), geometry=[Point(xy) for xy in zip(df['lon'], df['lat'])], crs='EPSG:4326')

    # 空间连接（多边形内的点）
    joined = gpd.sjoin(pts, gdf_admin, how='left', predicate='within')

    # 将管理 GeoDataFrame 中的管理列标准化/恢复到连接结果中。
    # 空间连接后，geopandas 可能会生成带后缀的列名（例如 NAME_2_right）
    # 或其他变体；尝试将原始管理列复制回可预测的名称
    try:
        admin_cols = [c for c in gdf_admin.columns if c != gdf_admin.geometry.name]
        joined_cols_lower = {jc.lower(): jc for jc in joined.columns}
        for ac in admin_cols:
            ac_lower = ac.lower()
            # 找到与此管理列名称最匹配的连接列
            match = None
            # exact match
            if ac_lower in joined_cols_lower:
                match = joined_cols_lower[ac_lower]
            else:
                # 尝试 sjoin 生成的常见后缀/模式
                for jc_lower, jc in joined_cols_lower.items():
                    if jc_lower.endswith('.' + ac_lower) or jc_lower.endswith('_' + ac_lower) or jc_lower.endswith(ac_lower + '_right'):
                        match = jc
                        break
                # 后备：任何包含标记的连接列
                if match is None:
                    for jc_lower, jc in joined_cols_lower.items():
                        if ac_lower in jc_lower:
                            match = jc
                            break
            if match is not None and match in joined.columns:
                # 复制到与原始管理列匹配的规范列名称
                try:
                    joined[ac] = joined[match]
                except Exception:
                    pass
    except Exception:
        # 非致命：尽力标准化
        pass

    # 相交回退：某些点恰好位于多边形边界上并且位于“内部”
    # 可能会想念他们。对于当前没有填充类似管理列的行，
    # 尝试使用 predicate='intersects' 进行第二次空间连接并填充缺失值。
    try:
        # determine which rows currently have any admin info
        admin_like_cols = [c for c in joined.columns if any(tok.lower() in c.lower() for tok in ['name', 'nl_name', 'province', 'city', 'adm'])]
        if not admin_like_cols:
            admin_like_cols = [c for c in joined.columns if c not in ('index_right', 'geometry')]

        def _row_has_admin(series_row):
            for c in admin_like_cols:
                try:
                    if c in series_row.index and pd.notna(series_row[c]) and str(series_row[c]).strip():
                        return True
                except Exception:
                    continue
            return False

        mask_has = joined.apply(_row_has_admin, axis=1)
        if mask_has.all():
            # everyone matched; no need for fallback
            pass
        else:
            unmatched = joined.loc[~mask_has].copy()
            if not unmatched.empty:
                try:
                    # do intersects join for unmatched subset
                    unmatched = gpd.GeoDataFrame(unmatched, geometry=unmatched.geometry, crs=joined.crs)
                    s2 = gpd.sjoin(unmatched, gdf_admin, how='left', predicate='intersects')
                    # normalize admin columns from s2 into s2 (same logic as above)
                    try:
                        admin_cols2 = [c for c in gdf_admin.columns if c != gdf_admin.geometry.name]
                        joined_cols_lower2 = {jc.lower(): jc for jc in s2.columns}
                        for ac in admin_cols2:
                            ac_lower = ac.lower()
                            match = None
                            if ac_lower in joined_cols_lower2:
                                match = joined_cols_lower2[ac_lower]
                            else:
                                for jc_lower, jc in joined_cols_lower2.items():
                                    if jc_lower.endswith('.' + ac_lower) or jc_lower.endswith('_' + ac_lower) or jc_lower.endswith(ac_lower + '_right') or (ac_lower in jc_lower):
                                        match = jc
                                        break
                            if match is not None and match in s2.columns:
                                try:
                                    s2[ac] = s2[match]
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # for each admin-like column, fill into original joined where missing
                    for ac in admin_cols2:
                        if ac in s2.columns:
                            # s2 index aligns with unmatched index; fill only where joined has null/empty
                            for idx, val in s2[ac].items():
                                try:
                                    if (ac not in joined.columns) or pd.isna(joined.at[idx, ac]) or str(joined.at[idx, ac]).strip() == '':
                                        joined.at[idx, ac] = val
                                except Exception:
                                    continue
                except Exception:
                    # fallback: ignore intersects errors
                    pass
    except Exception:
        pass

    # 尝试从管理 GeoDataFrame 中提取省份和城市列
    # 常见 GADM 字段：NAME_1（省）、NAME_2（城市）
    # 如果存在的话，更喜欢本地化的（NL_NAME_*）中文名称
    province_candidates = ['NL_NAME_1', 'NAME_1', 'province', 'Province', 'PROV', 'ADM1_NAME', 'NAME_0', 'NAME']
    city_candidates = ['NL_NAME_2', 'NAME_2', 'city', 'City', 'ADM2_NAME', 'NAME_1']
    admin_col = _choose_admin_name_column(gdf_admin)

    def _find_join_col(joined_cols, candidates):
        # look for exact match first, then for cols that endwith or contain the candidate (handle suffixes from sjoin)
        for c in candidates:
            if c in joined_cols:
                return c
        for c in candidates:
            for jc in joined_cols:
                if jc.endswith('.' + c) or jc.endswith('_' + c) or jc == c + '_right' or jc.endswith(c + '_right') or (c in jc and jc.count(c) == 1 and jc.startswith(c)):
                    return jc
        return None

    joined_cols = list(joined.columns)
    province_col = _find_join_col(joined_cols, province_candidates)
    city_col = _find_join_col(joined_cols, city_candidates)

    # set province/city columns on joined result if available (prefer localized fields)
    if province_col:
        if province_col != 'province':
            joined = joined.rename(columns={province_col: 'province'})
    else:
        joined['province'] = None

    if city_col:
        if city_col != 'city':
            joined = joined.rename(columns={city_col: 'city'})
    else:
        # fallback: if admin_col corresponds to city-level names and level=='city', use it
        if level == 'city' and admin_col in joined.columns:
            joined = joined.rename(columns={admin_col: 'city'})
            if 'province' not in joined.columns:
                joined['province'] = None
        else:
            joined['city'] = None

    # Ensure admin_name column always exists: prefer admin_col, then city, then province
    if admin_col in joined.columns and admin_col != 'admin_name':
        joined = joined.rename(columns={admin_col: 'admin_name'})
    if 'admin_name' not in joined.columns or joined['admin_name'].isnull().all():
        if 'city' in joined.columns and joined['city'].notna().any():
            joined['admin_name'] = joined['city']
        elif 'province' in joined.columns and joined['province'].notna().any():
            joined['admin_name'] = joined['province']
        else:
            joined['admin_name'] = None

    joined['admin_level'] = level

    # convert back to pandas DataFrame (drop geometry)
    out = pd.DataFrame(joined.drop(columns=['geometry']))
    # ensure string types for province/city/admin_name to avoid encoding issues later
    for col in ('province', 'city', 'admin_name'):
        if col in out.columns:
            out[col] = out[col].astype(object).where(out[col].notna(), None)
    return out


def aggregate_to_admin(mapped_df: pd.DataFrame, level: str = 'city') -> pd.DataFrame:
    """按行政单位聚合数值变量（按 'admin_name' 分组）。
    返回包含 admin_name 和数值列均值的 DataFrame。
    """
    if 'admin_name' not in mapped_df.columns:
        raise ValueError('mapped_df must contain admin_name column')

    # numeric columns to aggregate
    numeric_cols = mapped_df.select_dtypes(include=['number']).columns.tolist()
    # Exclude lon/lat if present
    numeric_cols = [c for c in numeric_cols if c not in ('lat', 'lon')]

    grouped = mapped_df.groupby('admin_name')[numeric_cols].mean().reset_index()
    # Optionally add level indicator
    grouped['admin_level'] = level
    return grouped


def canonicalize_admin_mapping(df: pd.DataFrame, fill_english_if_missing: bool = True, sample_limit: int = 50):
    """规范化映射 DataFrame 中的行政区相关列。

    行为（改进版）:
    - 优先选择包含中文字符的省/市列；如果找不到中文且 fill_english_if_missing 为 True，
      则使用候选英文列（NAME_1/NAME_2 等）作为回退；否则保持缺失。
    - 保证不会把 city 的值误用为 province（候选列会区分优先级并去重）。
    - 返回 (df_out, stats)，其中 stats 包含 before_rows/after_rows、filled_count（使用英文回退的次数）和 english_samples。
    """
    out = df.copy()
    cols = list(out.columns)

    def _cols_matching(tokens):
        outc = []
        for c in cols:
            low = c.lower()
            for t in tokens:
                if t.lower() in low:
                    outc.append(c)
                    break
        return outc

    # build candidate lists (distinct)
    prov_candidates = _cols_matching(['nl_name_1', 'name_1', 'province', 'province_x', 'province_y', 'prov', 'adm1'])
    city_candidates = _cols_matching(['nl_name_2', 'name_2', 'city', 'city_x', 'city_y', 'adm2', 'cnty', 'mun'])

    # remove overlaps so we don't accidentally pick the same column for both
    prov_candidates = [c for c in prov_candidates if c not in city_candidates]
    city_candidates = [c for c in city_candidates if c not in prov_candidates]

    # helper to pick chinese-first, then english-only-if-allowed
    def _choose_per_row(df_frame, candidates, allow_english=True):
        idx = df_frame.index
        out_s = pd.Series([pd.NA] * len(idx), index=idx, dtype=object)

        def col_series(name):
            if name in df_frame.columns:
                return df_frame[name].astype(object).where(df_frame[name].notna(), pd.NA)
            else:
                return pd.Series([pd.NA] * len(idx), index=idx, dtype=object)

        chinese_re = r'[\u4e00-\u9fff]'
        # prefer Chinese values first
        for c in candidates:
            s = col_series(c)
            try:
                mask = s.notna() & s.astype(str).str.strip().ne('') & s.astype(str).str.contains(chinese_re)
            except Exception:
                mask = s.notna() & s.astype(str).str.strip().ne('')
            if mask.any():
                to_fill = mask & out_s.isna()
                out_s[to_fill] = s[to_fill]

        # then allow english fallback if requested
        if allow_english:
            for c in candidates:
                s = col_series(c)
                mask = s.notna() & s.astype(str).str.strip().ne('')
                if mask.any():
                    to_fill = mask & out_s.isna()
                    out_s[to_fill] = s[to_fill]

        return out_s

    prov_series = _choose_per_row(out, prov_candidates, allow_english=fill_english_if_missing) if prov_candidates else pd.Series([pd.NA] * len(out), index=out.index)
    city_series = _choose_per_row(out, city_candidates, allow_english=fill_english_if_missing) if city_candidates else pd.Series([pd.NA] * len(out), index=out.index)

    # existing admin_name column preference
    if 'admin_name' in out.columns:
        admin_existing = out['admin_name'].astype(object).where(out['admin_name'].notna(), pd.NA)
    else:
        admin_existing = pd.Series([pd.NA] * len(out), index=out.index)

    admin_series = admin_existing.where(admin_existing.notna(), city_series)
    admin_series = admin_series.where(admin_series.notna(), prov_series)

    out['province'] = prov_series
    out['city'] = city_series
    out['admin_name'] = admin_series

    before_rows = len(out)

    # keep rows that have at least one of province/city/admin_name after fallback
    mask_keep = out['province'].notna() | out['city'].notna() | out['admin_name'].notna()
    out = out.loc[mask_keep].copy()

    # compute filled_count and examples where english fallback was used
    filled_count = 0
    english_samples = []
    try:
        def _has_chinese(s):
            try:
                return bool(pd.notna(s) and bool(re.search(r'[\u4e00-\u9fff]', str(s))))
            except Exception:
                return False

        for idx in out.index:
            orig = df.loc[idx] if idx in df.index else None
            if orig is None:
                continue
            # province
            prov_orig_has_cn = False
            if 'province' in orig.index and pd.notna(orig['province']):
                prov_orig_has_cn = _has_chinese(orig['province'])
            prov_now = out.at[idx, 'province'] if 'province' in out.columns else None
            if not prov_orig_has_cn and pd.notna(prov_now):
                filled_count += 1
                if len(english_samples) < sample_limit:
                    english_samples.append((None, str(prov_now)))
            # city
            city_orig_has_cn = False
            if 'city' in orig.index and pd.notna(orig['city']):
                city_orig_has_cn = _has_chinese(orig['city'])
            city_now = out.at[idx, 'city'] if 'city' in out.columns else None
            if not city_orig_has_cn and pd.notna(city_now):
                filled_count += 1
                if len(english_samples) < sample_limit:
                    english_samples.append((None, str(city_now)))
    except Exception:
        filled_count = int(filled_count) if 'filled_count' in locals() else 0

    after_rows = len(out)
    stats = {'before_rows': before_rows, 'after_rows': after_rows, 'filled_count': int(filled_count), 'english_samples': english_samples}
    return out, stats
