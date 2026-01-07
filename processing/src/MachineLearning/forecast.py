import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from tqdm.auto import tqdm

# ------------------------------
# 数据加载和标准化
# ------------------------------

# 功能遵循前端命名；保持张量的顺序稳定
FEATURES = [
    "pm25",
    "pm10",
    "so2",
    "no2",
    "co",
    "o3",
    "u",
    "v",
    "temp",
    "rh",
    "psfc",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_region_mapping(region_path: Path) -> Dict[str, Tuple[float, float]]:
    """加载region.json，构建 province|city -> (longitude, latitude) 映射。
    
    对于同一个城市有多个区县记录的情况，取第一个区县的经纬度作为城市代表坐标。
    """
    regions = load_json(region_path)
    mapping: Dict[str, Tuple[float, float]] = {}
    for item in regions:
        province = item.get("province", "")
        city = item.get("city", "")
        lon_val = to_float(item.get("longitude", "nan"))
        lat_val = to_float(item.get("latitude", "nan"))
        if math.isnan(lon_val) or math.isnan(lat_val):
            continue  # 跳过缺失或无效经纬度
        key = f"{province}|{city}"
        # 只保留第一个匹配的经纬度（通常是市级或第一个区县）
        if key not in mapping:
            mapping[key] = (lon_val, lat_val)
    return mapping


def to_float(val):
    try:
        return float(val)
    except Exception:
        return float("nan")


def load_city_timeseries(data_root: Path, years: List[str], geo_mapping: Dict[str, Tuple[float, float]]) -> Dict[str, List[Tuple[str, List[float]]]]:
    """加载城市时序数据，特征向量中包含经纬度信息。
    
    Args:
        data_root: 数据根目录
        years: 年份列表
        geo_mapping: province|city -> (longitude, latitude) 映射表
    
    Returns:
        城市时序字典，每个样本特征向量末尾包含经纬度
    """
    series: Dict[str, List[Tuple[str, List[float]]]] = {}
    # 使用全部11个特征
    base_features = FEATURES 
    for year in years:
        days_idx = load_json(data_root / year / "index.json")
        for day in days_idx.get("days", []):
            y, m, d = day.split("-")
            day_path = data_root / year / m / d / f"{y}{m}{d}.json"
            if not day_path.exists():
                continue
            rows = load_json(day_path)
            for row in rows:
                city_key = f"{row.get('province','')}|{row.get('city','')}"
                # 构建基础特征向量
                vec = [to_float(row.get(feat, "nan")) for feat in base_features]
                # 从映射表获取经纬度并附加
                lon, lat = geo_mapping.get(city_key, (0.0, 0.0))
                vec.extend([lon, lat])
                if city_key not in series:
                    series[city_key] = []
                series[city_key].append((day, vec))
    for k in series:
        series[k].sort(key=lambda x: x[0])
    return series


def compute_norm_stats(series: Dict[str, List[Tuple[str, List[float]]]]):
    import numpy as np

    all_vals = []
    for _, items in series.items():
        for _, vec in items:
            all_vals.append(vec)
    arr = np.array(all_vals, dtype=float)
    mean = np.nanmean(arr, axis=0)
    std = np.nanstd(arr, axis=0) + 1e-6
    return mean.tolist(), std.tolist()


def normalize(vec, mean, std):
    return [(v - m) / s for v, m, s in zip(vec, mean, std)]


def denormalize(vec, mean, std):
    return [v * s + m for v, m, s in zip(vec, mean, std)]


# ------------------------------
# 数据集和模型
# ------------------------------
class SeqDataset(Dataset):
    def __init__(self, series: Dict[str, List[Tuple[str, List[float]]]], mean, std, window: int = 30, horizon: int = 1):
        self.samples = []
        for items in series.values():
            if len(items) <= window:
                continue
            for i in range(len(items) - window - horizon + 1):
                # 分离特征和上下文
                seq = [normalize(items[j][1][:11], mean[:11], std[:11]) for j in range(i, i + window)]
                context = items[i][1][11:]  # 经纬度（静态，不需要归一化）
                tgt = normalize(items[i + window][1][:11], mean[:11], std[:11])
                self.samples.append((
                    torch.tensor(seq, dtype=torch.float32),
                    torch.tensor(context, dtype=torch.float32),
                    torch.tensor(tgt, dtype=torch.float32)
                ))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


class GRUForecaster(nn.Module):
    def __init__(self, feature_size: int = 11, context_size: int = 2, hidden: int = 128, layers: int = 2, dropout: float = 0.1):
        super().__init__()
        # GRU只处理时间序列特征（11维）
        self.gru = nn.GRU(feature_size, hidden, num_layers=layers, batch_first=True, dropout=dropout)
        # 融合经纬度作为静态上下文
        self.context_proj = nn.Linear(context_size, hidden)
        self.head = nn.Sequential(
            nn.LayerNorm(hidden),
            nn.Linear(hidden, feature_size)  # 只输出11维
        )
    
    def forward(self, x_seq, x_context):
        # x_seq: [B, 30, 11]  时间序列特征
        # x_context: [B, 2]   经纬度
        out, _ = self.gru(x_seq)
        last = out[:, -1, :]
        context_emb = self.context_proj(x_context)
        combined = last + context_emb  # 融合位置信息
        pred = self.head(combined)  # 只输出11维
        return pred


# ------------------------------
# Training & evaluation helpers
# ------------------------------
def train(model, loader, device, epochs=8, lr=1e-3):
    optim = torch.optim.AdamW(model.parameters(), lr=lr)
    loss_fn = nn.L1Loss()
    model.train()
    for epoch in range(epochs):
        total = 0.0
        progress = tqdm(loader, desc=f"Epoch {epoch+1}/{epochs}", leave=False)
        for seq, context, tgt in progress:
            seq, context, tgt = seq.to(device), context.to(device), tgt.to(device)
            optim.zero_grad()
            pred = model(seq, context)
            loss = loss_fn(pred, tgt)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            total += loss.item() * seq.size(0)
            progress.set_postfix(batch_loss=f"{loss.item():.4f}")
        avg = total / len(loader.dataset)
        print(f"[Epoch {epoch+1}] train L1={avg:.4f}")


@torch.no_grad()
def estimate_mae(model, loader, device, max_batches: int = 16) -> float:
    loss_fn = nn.L1Loss(reduction="sum")
    total_loss = 0.0
    total_count = 0
    model.eval()
    for batch_idx, (seq, context, tgt) in enumerate(loader):
        if batch_idx >= max_batches:
            break
        seq, context, tgt = seq.to(device), context.to(device), tgt.to(device)
        pred = model(seq, context)
        total_loss += loss_fn(pred, tgt).item()
        total_count += tgt.numel() / tgt.size(-1)  # count by samples
    return total_loss / max(total_count, 1)


@torch.no_grad()
def compute_feature_importance(model, dataset: Dataset, device, batches: int = 8, seed: int = 42):
    """保留切片上的排列重要性。

    步骤：
      1) 计算一个小子集的基线 MAE。
      2) 在批次/时间维度上随机排列一项特征并测量 MAE 增加。
      3) 更高的 delta_mae => 更重要的特征。
    """

    torch.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=64, shuffle=True, drop_last=True)

    base_mae = estimate_mae(model, loader, device, max_batches=batches)
    print(f"[FeatureImportance] baseline MAE={base_mae:.4f}")

    results = []
    # 评估所有输入特征的重要性（11个时序特征 + 2个上下文特征）
    all_features = FEATURES + ["longitude", "latitude"]
    for feat_idx, name in enumerate(all_features):
        loss_fn = nn.L1Loss(reduction="sum")
        total_loss = 0.0
        total_count = 0
        for batch_idx, (seq, context, tgt) in enumerate(loader):
            if batch_idx >= batches:
                break
            seq, context, tgt = seq.to(device), context.to(device), tgt.to(device)

            # 判断是时序特征还是上下文特征
            if feat_idx < len(FEATURES):
                # 时序特征：在时间和batch维度上打乱
                shuffled = seq[:, :, feat_idx].flatten()
                perm = torch.randperm(shuffled.numel(), device=device)
                shuffled = shuffled[perm].view_as(seq[:, :, feat_idx])
                perturbed_seq = seq.clone()
                perturbed_seq[:, :, feat_idx] = shuffled
                perturbed_context = context
            else:
                # 上下文特征（经纬度）：在batch维度上打乱
                context_idx = feat_idx - len(FEATURES)
                shuffled = context[:, context_idx].flatten()
                perm = torch.randperm(shuffled.numel(), device=device)
                shuffled = shuffled[perm]
                perturbed_context = context.clone()
                perturbed_context[:, context_idx] = shuffled
                perturbed_seq = seq

            pred = model(perturbed_seq, perturbed_context)
            total_loss += loss_fn(pred, tgt).item()
            total_count += tgt.numel() / tgt.size(-1)

        mae = total_loss / max(total_count, 1)
        delta = max(mae - base_mae, 0.0)
        results.append({"feature": name, "mae": mae, "delta_mae": delta})
        print(f"[FeatureImportance] {name}: MAE={mae:.4f}, Δ={delta:.4f}")

    total_delta = sum(r["delta_mae"] for r in results) or 1e-6
    for r in results:
        r["importance"] = r["delta_mae"] / total_delta

    results.sort(key=lambda x: x["importance"], reverse=True)
    return results


def autoregressive_predict(model, seed_series: Dict[str, List[Tuple[str, List[float]]]], mean, std, predict_days: List[str], window: int, device) -> Dict[str, List[Tuple[str, List[float]]]]:
    model.eval()
    preds: Dict[str, List[Tuple[str, List[float]]]] = {}
    for city, items in seed_series.items():
        # 分离特征和上下文
        buffer = [normalize(vec[:11], mean[:11], std[:11]) for _, vec in items[-window:]]
        context = items[-1][1][11:]  # 使用城市的经纬度（静态）
        if len(buffer) < window:
            continue
        for day in predict_days:
            x_seq = torch.tensor([buffer[-window:]], dtype=torch.float32, device=device)
            x_context = torch.tensor([context], dtype=torch.float32, device=device)
            with torch.no_grad():
                y = model(x_seq, x_context).squeeze(0).cpu().tolist()
            denorm = denormalize(y, mean[:11], std[:11])
            if city not in preds:
                preds[city] = []
            preds[city].append((day, denorm))
            buffer.append(y)
    return preds


def teacher_forced_predict(model, actual_series: Dict[str, List[Tuple[str, List[float]]]], mean, std, window: int, device) -> Dict[str, List[Tuple[str, List[float]]]]:
    """Next-day forecast using真实前30天历史 (更贴合题意)。

    对每个城市：从实际序列中滑动窗口取前30天，预测下一天；覆盖全年。
    需要 actual_series 中包含预测年全量日序列。
    """

    model.eval()
    preds: Dict[str, List[Tuple[str, List[float]]]] = {}
    for city, items in tqdm(actual_series.items(), desc="Teacher predict cities", leave=False):
        if len(items) <= window:
            continue
        items_sorted = sorted(items, key=lambda x: x[0])
        for idx in range(window, len(items_sorted)):
            # 用前 window 天预测第 idx 天
            window_slice = [normalize(vec[:11], mean[:11], std[:11]) for _, vec in items_sorted[idx - window : idx]]
            target_day = items_sorted[idx][0]
            # 提取经纬度上下文（静态，使用当前城市的）
            context = items_sorted[idx][1][11:]  # [lon, lat]
            x_seq = torch.tensor([window_slice], dtype=torch.float32, device=device)
            x_context = torch.tensor([context], dtype=torch.float32, device=device)
            with torch.no_grad():
                y = model(x_seq, x_context).squeeze(0).cpu().tolist()
            denorm = denormalize(y, mean[:11], std[:11])
            preds.setdefault(city, []).append((target_day, denorm))
    return preds


def save_predictions(preds: Dict[str, List[Tuple[str, List[float]]]], out_root: Path):
    """保存预测结果，仅保存污染和气象特征（不含经纬度，因经纬度是城市静态属性）。"""
    out_root.mkdir(parents=True, exist_ok=True)
    output_features = FEATURES
    
    # 先按日期分组所有城市的预测数据
    day_data: Dict[str, List[dict]] = {}
    for city_key, items in preds.items():
        province, city = city_key.split("|")
        for day, vec in items:
            # 过滤 NaN 值
            vals = {}
            for i, feat in enumerate(output_features):
                if i < len(vec):
                    v = vec[i]
                    if not math.isnan(v):
                        vals[feat] = float(v)
            
            payload = {
                "province": province,
                "city": city,
                **vals
            }
            
            if day not in day_data:
                day_data[day] = []
            day_data[day].append(payload)
    
    # 然后一次性写入每个日期的所有城市数据
    for day, payloads in tqdm(day_data.items(), desc="Saving predictions"):
        y, m, d = day.split("-")
        day_dir = out_root / y / m / d
        day_dir.mkdir(parents=True, exist_ok=True)
        out_file = day_dir / f"{y}{m}{d}.json"
        
        with out_file.open("w", encoding="utf-8") as f:
            json.dump(payloads, f, ensure_ascii=False, indent=2)


def save_feature_importance(results, out_root: Path):
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / "feature_importance.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[FeatureImportance] saved to {path}")


def compute_mae(preds: Dict[str, List[Tuple[str, List[float]]]], actual: Dict[str, List[Tuple[str, List[float]]]]):
    """计算所有重叠城市日对中每个要素的 MAE。"""

    # Build lookup for actual
    actual_map: Dict[Tuple[str, str], List[float]] = {}
    for city, items in actual.items():
        for day, vec in items:
            actual_map[(city, day)] = vec

    total = [0.0 for _ in FEATURES]
    count = 0
    for city, items in preds.items():
        for day, pred_vec in items:
            gt = actual_map.get((city, day))
            if not gt:
                continue
            # 仅计算 FEATURES 中定义的特征的 MAE，忽略经纬度（虽然它们在向量末尾）
            for i in range(len(FEATURES)):
                if i >= len(pred_vec) or i >= len(gt):
                    continue
                p = pred_vec[i]
                g = gt[i]
                if math.isnan(p) or math.isnan(g):
                    continue
                total[i] += abs(p - g)
            count += 1

    if count == 0:
        return {"mae": {}, "per_feature": []}

    per_feature = []
    for i, name in enumerate(FEATURES):
        per_feature.append({"feature": name, "mae": total[i] / max(count, 1)})
    avg_mae = sum(t["mae"] for t in per_feature) / len(per_feature)
    return {"mae": avg_mae, "per_feature": per_feature}


def save_metrics(summary, out_root: Path):
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / "metrics_summary.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[Metrics] saved to {path}")


def parse_args():
    p = argparse.ArgumentParser(description="Train GRU forecaster for AQI/pollution and wind")
    p.add_argument("--data-root", type=Path, default=Path("front/public/data"))
    p.add_argument("--train-years", type=str, default="2013,2014,2015,2016,2017,2018")
    p.add_argument("--predict-year", type=str, default="2019")
    p.add_argument("--window", type=int, default=30)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--epochs", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--layers", type=int, default=2)
    p.add_argument("--dropout", type=float, default=0.1)
    p.add_argument("--out", type=Path, default=Path("front/public/data/predictions"))
    p.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--importance-batches", type=int, default=8, help="Batches to sample for permutation importance")
    p.add_argument(
        "--prediction-mode",
        type=str,
        default="teacher",
        choices=["teacher", "autoregressive"],
        help="teacher=使用真实前30天预测下一天；autoregressive=使用模型自回归滚动预测",
    )
    p.add_argument("--save-weights", action="store_true", help="保存模型权重到输出目录")
    p.add_argument("--weights-name", type=str, default="gru_forecaster.pt")
    return p.parse_args()


def main():
    args = parse_args()
    train_years = args.train_years.split(",")
    predict_year = args.predict_year

    # 加载地理映射（经纬度信息）
    region_path = args.data_root.parent / "region.json"
    if not region_path.exists():
        print(f"Warning: {region_path} not found, using default (0,0) for all cities")
        geo_mapping = {}
    else:
        print(f"Loading geo mapping from {region_path}")
        geo_mapping = load_region_mapping(region_path)
        print(f"Loaded {len(geo_mapping)} city coordinates")

    print(f"Loading training data: {train_years}")
    train_series = load_city_timeseries(args.data_root, train_years, geo_mapping)
    mean, std = compute_norm_stats(train_series)

    dataset = SeqDataset(train_series, mean, std, window=args.window)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)

    device = torch.device(args.device)
    # 输入特征: FEATURES (11) 时间序列 + Longitude + Latitude (2) 静态上下文
    feature_dim = len(FEATURES)
    context_dim = 2
    model = GRUForecaster(feature_size=feature_dim, context_size=context_dim, hidden=args.hidden, layers=args.layers, dropout=args.dropout).to(device)
    train(model, loader, device, epochs=args.epochs, lr=args.lr)

    predict_series = load_city_timeseries(args.data_root, [predict_year], geo_mapping)

    print("Running predictions...")
    if args.prediction_mode == "teacher":
        preds = teacher_forced_predict(model, predict_series, mean, std, args.window, device)
    else:
        seed_series = load_city_timeseries(args.data_root, train_years, geo_mapping)
        predict_days = load_json(args.data_root / predict_year / "index.json").get("days", [])
        preds = autoregressive_predict(model, seed_series, mean, std, predict_days, args.window, device)
    print("Predictions done. Saving...")

    out_root = args.out
    save_predictions(preds, out_root)
    print("Predictions saved.")

    # 特征重要性（排列）
    print("Computing feature importance...")
    fi_results = compute_feature_importance(model, dataset, device, batches=args.importance_batches)
    save_feature_importance(fi_results, out_root)
    print("Feature importance saved.")

    # 指标与实际（仅当预测年份存在时）
    if predict_series:
        print("Computing metrics vs actual...")
        metrics = compute_mae(preds, predict_series)
        save_metrics(metrics, out_root)
        print("Metrics saved.")

    # 保存下游/服务的权重
    if args.save_weights:
        weights_path = out_root / args.weights_name
        torch.save(model.state_dict(), weights_path)
        print(f"[Weights] saved to {weights_path}")

    print(f"Saved predictions, metrics, and feature importance to {out_root}")


if __name__ == "__main__":
    main()
