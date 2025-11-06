"""异常值检测与剔除工具

功能：
- remove_physical_bounds(df, var_bounds) - 基于变量物理上下限剔除
- remove_iqr_outliers(df, value_cols, groupby=None, k=1.5, return_mask=False) - 基于分组 IQR 剔除离群点

输出：返回清洗后的 DataFrame（并可选返回布尔掩码或被移除的统计信息）
"""
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
from . import config as _config
GROUPBY_UNIQUE_THRESHOLD = getattr(_config, 'GROUPBY_UNIQUE_THRESHOLD', 150000)


def remove_physical_bounds(df: pd.DataFrame, var_bounds: Dict[str, Tuple[float, float]], inplace: bool = False) -> pd.DataFrame:
    """移除超出物理边界的点（将值替换为 NaN）。

    Args:
        df: 输入 DataFrame
        var_bounds: dict，键为列名，值为 (min, max)
        inplace: 是否就地操作

    Returns:
        经过物理边界处理后的 DataFrame
    """
    if not inplace:
        df = df.copy()
    for col, (lo, hi) in var_bounds.items():
        if col in df.columns:
            mask = (df[col] < lo) | (df[col] > hi) | pd.isna(df[col])
            # 把不合法的值设为 NaN
            df.loc[mask, col] = np.nan
    return df


def remove_iqr_outliers(df: pd.DataFrame, value_cols: List[str], groupby: Optional[List[str]] = None, k: float = 1.5, return_mask: bool = False) -> Tuple[pd.DataFrame, Optional[pd.Series]]:
    """基于 IQR 的离群点剔除。对于每个 group（或全局），逐列计算 Q1/Q3 并剔除小于 Q1-k*IQR 或大于 Q3+k*IQR 的点（设置为 NaN）。

    Args:
        df: 输入 DataFrame
        value_cols: 需要检测的数值列
        groupby: 分组键，例如 ['lat','lon'] 或 ['province','city']。如果 None 则不分组。
        k: IQR 扩展倍数，常用 1.5
        return_mask: 如果 True，返回一个布尔 Series，标识哪些行被认为是离群并被替换为 NaN（任一列触发）

    Returns:
        (cleaned_df, mask_series 或 None)
    """
    # Work on a copy to avoid mutating caller data
    df = df.copy()

    # Prepare mask Series (False by default)
    row_mask = pd.Series(False, index=df.index)

    # Determine valid numeric columns to process
    valid_value_cols = [c for c in value_cols if c in df.columns]
    if not valid_value_cols:
        if return_mask:
            return df, row_mask
        return df, None

    # If grouping is provided, compute groupwise Q1/Q3 using transform which avoids explicit Python loops
    if groupby is None or len(groupby) == 0:
        # Global quantiles
        Q1 = df[valid_value_cols].quantile(0.25)
        Q3 = df[valid_value_cols].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - k * IQR
        upper = Q3 + k * IQR
        for col in valid_value_cols:
            col_vals = df[col]
            m = (col_vals < lower[col]) | (col_vals > upper[col])
            m = m.fillna(False)
            if m.any():
                df.loc[m, col] = np.nan
                row_mask = row_mask | m
    else:
        # Group-based quantiles (vectorized via transform)
        # If grouping would create an extremely large number of groups, skip heavy group-wise quantiles
        try:
            gb = df.groupby(groupby)
            n_groups = gb.ngroups
        except Exception:
            n_groups = None

        # If group count too large, fall back to global percentile clipping for speed
        if n_groups is not None and GROUPBY_UNIQUE_THRESHOLD and n_groups > GROUPBY_UNIQUE_THRESHOLD:
            # global quantile clipping per column
            for col in valid_value_cols:
                ser = pd.to_numeric(df[col], errors='coerce')
                q1 = ser.quantile(0.25)
                q3 = ser.quantile(0.75)
                iqr = q3 - q1
                lower = q1 - k * iqr
                upper = q3 + k * iqr
                m = (ser < lower) | (ser > upper)
                m = m.fillna(False)
                if m.any():
                    df.loc[m, col] = np.nan
                    row_mask = row_mask | m
        else:
            for col in valid_value_cols:
                try:
                    q1 = gb[col].transform(lambda s: s.quantile(0.25))
                    q3 = gb[col].transform(lambda s: s.quantile(0.75))
                except Exception:
                    # fallback to global quantiles for this column if group transform fails
                    q1 = df[col].quantile(0.25)
                    q3 = df[col].quantile(0.75)
                    q1 = pd.Series(q1, index=df.index)
                    q3 = pd.Series(q3, index=df.index)
                iqr = q3 - q1
                lower = q1 - k * iqr
                upper = q3 + k * iqr
                col_vals = df[col]
                m = (col_vals < lower) | (col_vals > upper)
                m = m.fillna(False)
                if m.any():
                    df.loc[m, col] = np.nan
                    row_mask = row_mask | m

    if return_mask:
        return df, row_mask
    return df, None
