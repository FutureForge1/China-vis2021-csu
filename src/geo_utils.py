import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os


def _choose_admin_name_column(gdf):
    # prefer common columns; prefer NL_NAME_1/NL_NAME_2 (localized/Chinese) when available
    for c in ['NL_NAME_2', 'NL_NAME_1', 'NL_NAME', 'NAME_2', 'NAME_1', 'NAME', 'name', 'ADM_NAME', 'CITY_NAME', 'province', '市名', '省名']:
        if c in gdf.columns:
            return c
    # fallback: pick first non-geometry, non-numeric column
    for c in gdf.columns:
        if c == 'geometry':
            continue
        if gdf[c].dtype == object:
            return c
    # final fallback
    return gdf.columns[0]


def map_points_to_admin(df: pd.DataFrame, admin_geojson_path: str, level: str = 'city') -> pd.DataFrame:
    """Map lat/lon points in df to administrative polygons from a GeoJSON.
    Returns original df with an added column 'admin_name' and 'admin_level'.
    """
    if 'lat' not in df.columns or 'lon' not in df.columns:
        raise ValueError('DataFrame 必须包含 lat 和 lon 列')

    if not os.path.exists(admin_geojson_path):
        raise FileNotFoundError(admin_geojson_path)

    gdf_admin = gpd.read_file(admin_geojson_path)
    # ensure crs is WGS84
    try:
        gdf_admin = gdf_admin.to_crs(epsg=4326)
    except Exception:
        pass

    # build points gdf
    pts = gpd.GeoDataFrame(df.copy(), geometry=[Point(xy) for xy in zip(df['lon'], df['lat'])], crs='EPSG:4326')

    # spatial join (points within polygons)
    joined = gpd.sjoin(pts, gdf_admin, how='left', predicate='within')

    # Normalize/restore admin columns from the admin GeoDataFrame into the joined result.
    # After spatial join geopandas may produce column names with suffixes (e.g. NAME_2_right)
    # or other variations; try to copy original admin columns back to predictable names
    try:
        admin_cols = [c for c in gdf_admin.columns if c != gdf_admin.geometry.name]
        joined_cols_lower = {jc.lower(): jc for jc in joined.columns}
        for ac in admin_cols:
            ac_lower = ac.lower()
            # find a joined column that best matches this admin col name
            match = None
            # exact match
            if ac_lower in joined_cols_lower:
                match = joined_cols_lower[ac_lower]
            else:
                # try common suffix/patterns produced by sjoin
                for jc_lower, jc in joined_cols_lower.items():
                    if jc_lower.endswith('.' + ac_lower) or jc_lower.endswith('_' + ac_lower) or jc_lower.endswith(ac_lower + '_right'):
                        match = jc
                        break
                # fallback: any joined column that contains the token
                if match is None:
                    for jc_lower, jc in joined_cols_lower.items():
                        if ac_lower in jc_lower:
                            match = jc
                            break
            if match is not None and match in joined.columns:
                # copy to a canonical column name matching the original admin col
                try:
                    joined[ac] = joined[match]
                except Exception:
                    pass
    except Exception:
        # non-fatal: best-effort normalization
        pass

    # try to extract province and city columns from the admin GeoDataFrame
    # common GADM fields: NAME_1 (province), NAME_2 (city)
    # prefer localized (NL_NAME_*) Chinese names if present
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
    """Aggregate numeric variables to admin unit (group by 'admin_name').
    Returns DataFrame with admin_name and mean of numeric columns.
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
    """Normalize admin-related columns on a mapped DataFrame.

    - Picks best province/city columns preferring columns containing Chinese characters.
    - Ensures 'province', 'city', 'admin_name' exist.
    - If fill_english_if_missing is True, rows missing Chinese characters in province/city
      will be filled using English-name candidates (NAME_1/NAME_2 etc.) instead of being dropped.

    Returns tuple (df_out, stats) where stats contains counts and a small sample of english fallbacks used.
    """
    out = df.copy()
    cols = list(out.columns)

    def _cols_matching(tokens, cols_list):
        outc = []
        for c in cols_list:
            low = c.lower()
            for t in tokens:
                if t.lower() in low:
                    outc.append(c)
                    break
        return outc

    def _chinese_fraction(series):
        try:
            s = series.dropna().astype(str)
            if s.empty:
                return 0.0
            return float((s.str.contains(r'[\u4e00-\u9fff]')).sum()) / float(len(s))
        except Exception:
            return 0.0

    # pick admin_name if exists or candidate
    admin_candidates = _cols_matching(['admin_name', 'nl_name_2', 'name_2', 'name_1', 'province', 'city'], cols)
    if 'admin_name' not in out.columns and admin_candidates:
        out['admin_name'] = out[admin_candidates[0]]

    # province
    prov_candidates = _cols_matching(['nl_name_1', 'name_1', 'province', 'province_x', 'province_y', 'name'], cols)
    prov_choice = None
    best_score = -1.0
    for c in prov_candidates:
        try:
            score = _chinese_fraction(out[c])
        except Exception:
            score = 0.0
        if score > best_score:
            best_score = score
            prov_choice = c
    if prov_choice:
        out['province'] = out[prov_choice]
    else:
        out['province'] = out[prov_candidates[0]] if prov_candidates else None

    # city
    city_candidates = _cols_matching(['nl_name_2', 'name_2', 'city', 'city_x', 'city_y', 'name_1'], cols)
    city_choice = None
    best_score = -1.0
    for c in city_candidates:
        try:
            score = _chinese_fraction(out[c])
        except Exception:
            score = 0.0
        if score > best_score:
            best_score = score
            city_choice = c
    if city_choice:
        out['city'] = out[city_choice]
    else:
        out['city'] = out[city_candidates[0]] if city_candidates else None

    # ensure admin_name exists (prefer existing admin_name, else city, else province)
    if 'admin_name' not in out.columns or out['admin_name'].isnull().all():
        if 'city' in out.columns:
            out['admin_name'] = out['city']
        elif 'province' in out.columns:
            out['admin_name'] = out['province']
        else:
            out['admin_name'] = None

    before_rows = len(out)

    # mask mapped rows: those with any admin_name/province/city info
    mask_mapped = (~out['admin_name'].isna()) | (~out['province'].isna()) | (~out['city'].isna()) if 'admin_name' in out.columns else ((~out['province'].isna()) | (~out['city'].isna()))
    out = out[mask_mapped].copy()

    filled_count = 0
    english_samples = set()

    if fill_english_if_missing:
        # determine which rows have Chinese in province/city
        def _contains_cn(s):
            try:
                return s.fillna('').astype(str).str.contains(r'[\u4e00-\u9fff]')
            except Exception:
                return pd.Series(False, index=s.index)

        prov_has_cn = _contains_cn(out['province']) if 'province' in out.columns else pd.Series(False, index=out.index)
        city_has_cn = _contains_cn(out['city']) if 'city' in out.columns else pd.Series(False, index=out.index)

        def _pick_english_name(row, prov=True):
            if prov:
                cand = ('NAME_1', 'province', 'province_x', 'province_y')
            else:
                cand = ('NAME_2', 'NAME_1', 'city', 'city_x', 'city_y')
            for k in cand:
                if k in row.index and pd.notna(row[k]) and str(row[k]).strip():
                    return row[k]
            if 'admin_name' in row.index and pd.notna(row['admin_name']):
                return row['admin_name']
            return ''

        # iterate rows to fill
        for idx, row in out.iterrows():
            if not prov_has_cn.loc[idx]:
                en = _pick_english_name(row, prov=True)
                out.at[idx, 'province'] = en
                filled_count += 1
                english_samples.add((str(en), ''))
            if not city_has_cn.loc[idx]:
                en = _pick_english_name(row, prov=False)
                out.at[idx, 'city'] = en
                filled_count += 1
                english_samples.add(('', str(en)))

    after_rows = len(out)
    stats = {'before_rows': before_rows, 'after_rows': after_rows, 'filled_count': filled_count, 'english_samples': list(english_samples)[:sample_limit]}
    return out, stats
