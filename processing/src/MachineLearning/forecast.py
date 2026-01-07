import argparse
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

# ------------------------------
# Data loading & normalization
# ------------------------------

# Features follow frontend naming; keep order stable for tensors
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


def to_float(val):
    try:
        return float(val)
    except Exception:
        return float("nan")


def load_city_timeseries(data_root: Path, years: List[str]) -> Dict[str, List[Tuple[str, List[float]]]]:
    series: Dict[str, List[Tuple[str, List[float]]]] = {}
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
                vec = [to_float(row.get(feat, "nan")) for feat in FEATURES]
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
# Dataset & model
# ------------------------------
class SeqDataset(Dataset):
    def __init__(self, series: Dict[str, List[Tuple[str, List[float]]]], mean, std, window: int = 30, horizon: int = 1):
        self.samples = []
        for items in series.values():
            if len(items) <= window:
                continue
            for i in range(len(items) - window - horizon + 1):
                seq = [normalize(items[j][1], mean, std) for j in range(i, i + window)]
                tgt = normalize(items[i + window][1], mean, std)
                self.samples.append((torch.tensor(seq, dtype=torch.float32), torch.tensor(tgt, dtype=torch.float32)))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


class GRUForecaster(nn.Module):
    def __init__(self, input_size: int, hidden: int = 128, layers: int = 2, dropout: float = 0.1):
        super().__init__()
        self.gru = nn.GRU(input_size, hidden, num_layers=layers, batch_first=True, dropout=dropout)
        self.head = nn.Sequential(
            nn.LayerNorm(hidden),
            nn.Linear(hidden, input_size),
        )

    def forward(self, x):
        # x: [B, T, F]
        out, _ = self.gru(x)
        last = out[:, -1, :]
        pred = self.head(last)
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
        for seq, tgt in loader:
            seq, tgt = seq.to(device), tgt.to(device)
            optim.zero_grad()
            pred = model(seq)
            loss = loss_fn(pred, tgt)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optim.step()
            total += loss.item() * seq.size(0)
        avg = total / len(loader.dataset)
        print(f"[Epoch {epoch+1}] train L1={avg:.4f}")


@torch.no_grad()
def estimate_mae(model, loader, device, max_batches: int = 16) -> float:
    loss_fn = nn.L1Loss(reduction="sum")
    total_loss = 0.0
    total_count = 0
    model.eval()
    for batch_idx, (seq, tgt) in enumerate(loader):
        if batch_idx >= max_batches:
            break
        seq, tgt = seq.to(device), tgt.to(device)
        pred = model(seq)
        total_loss += loss_fn(pred, tgt).item()
        total_count += tgt.numel() / tgt.size(-1)  # count by samples
    return total_loss / max(total_count, 1)


@torch.no_grad()
def compute_feature_importance(model, dataset: Dataset, device, batches: int = 8, seed: int = 42):
    """Permutation importance on a held-out slice.

    Steps:
      1) Compute baseline MAE on a small subset.
      2) Shuffle one feature across the batch/time dimension and measure MAE increase.
      3) Higher delta_mae => more important feature.
    """

    torch.manual_seed(seed)
    loader = DataLoader(dataset, batch_size=64, shuffle=True, drop_last=True)

    base_mae = estimate_mae(model, loader, device, max_batches=batches)
    print(f"[FeatureImportance] baseline MAE={base_mae:.4f}")

    results = []
    for feat_idx, name in enumerate(FEATURES):
        loss_fn = nn.L1Loss(reduction="sum")
        total_loss = 0.0
        total_count = 0
        for batch_idx, (seq, tgt) in enumerate(loader):
            if batch_idx >= batches:
                break
            seq, tgt = seq.to(device), tgt.to(device)

            # permute this feature across batch and time to break its signal
            shuffled = seq[:, :, feat_idx].flatten()
            perm = torch.randperm(shuffled.numel(), device=device)
            shuffled = shuffled[perm].view_as(seq[:, :, feat_idx])
            perturbed = seq.clone()
            perturbed[:, :, feat_idx] = shuffled

            pred = model(perturbed)
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
        buffer = [normalize(vec, mean, std) for _, vec in items[-window:]]
        if len(buffer) < window:
            continue
        for day in predict_days:
            x = torch.tensor([buffer[-window:]], dtype=torch.float32, device=device)
            with torch.no_grad():
                y = model(x).squeeze(0).cpu().tolist()
            denorm = denormalize(y, mean, std)
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
    for city, items in actual_series.items():
        if len(items) <= window:
            continue
        items_sorted = sorted(items, key=lambda x: x[0])
        for idx in range(window, len(items_sorted)):
            # 用前 window 天预测第 idx 天
            window_slice = [normalize(vec, mean, std) for _, vec in items_sorted[idx - window : idx]]
            target_day = items_sorted[idx][0]
            x = torch.tensor([window_slice], dtype=torch.float32, device=device)
            with torch.no_grad():
                y = model(x).squeeze(0).cpu().tolist()
            denorm = denormalize(y, mean, std)
            preds.setdefault(city, []).append((target_day, denorm))
    return preds


def save_predictions(preds: Dict[str, List[Tuple[str, List[float]]]], out_root: Path):
    out_root.mkdir(parents=True, exist_ok=True)
    for city_key, items in preds.items():
        province, city = city_key.split("|")
        for day, vec in items:
            y, m, d = day.split("-")
            day_dir = out_root / y / m / d
            day_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "province": province,
                "city": city,
                **{feat: float(val) for feat, val in zip(FEATURES, vec)},
            }
            out_file = day_dir / f"{y}{m}{d}.json"
            if out_file.exists():
                existing = load_json(out_file)
                if isinstance(existing, list):
                    existing.append(payload)
                    with out_file.open("w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                    continue
            with out_file.open("w", encoding="utf-8") as f:
                json.dump([payload], f, ensure_ascii=False, indent=2)


def save_feature_importance(results, out_root: Path):
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / "feature_importance.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[FeatureImportance] saved to {path}")


def compute_mae(preds: Dict[str, List[Tuple[str, List[float]]]], actual: Dict[str, List[Tuple[str, List[float]]]]):
    """Compute MAE per feature over all overlapping city-day pairs."""

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
            for i, p in enumerate(pred_vec):
                if math.isnan(p) or math.isnan(gt[i]):
                    continue
                total[i] += abs(p - gt[i])
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

    print(f"Loading training data: {train_years}")
    train_series = load_city_timeseries(args.data_root, train_years)
    mean, std = compute_norm_stats(train_series)

    dataset = SeqDataset(train_series, mean, std, window=args.window)
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, drop_last=True)

    device = torch.device(args.device)
    model = GRUForecaster(input_size=len(FEATURES), hidden=args.hidden, layers=args.layers, dropout=args.dropout).to(device)
    train(model, loader, device, epochs=args.epochs, lr=args.lr)

    predict_series = load_city_timeseries(args.data_root, [predict_year])

    if args.prediction_mode == "teacher":
        preds = teacher_forced_predict(model, predict_series, mean, std, args.window, device)
    else:
        seed_series = load_city_timeseries(args.data_root, train_years)
        predict_days = load_json(args.data_root / predict_year / "index.json").get("days", [])
        preds = autoregressive_predict(model, seed_series, mean, std, predict_days, args.window, device)

    out_root = args.out
    save_predictions(preds, out_root)

    # Feature importance (permutation)
    fi_results = compute_feature_importance(model, dataset, device, batches=args.importance_batches)
    save_feature_importance(fi_results, out_root)

    # Metrics vs actual (only if predict year exists)
    if predict_series:
        metrics = compute_mae(preds, predict_series)
        save_metrics(metrics, out_root)

    # Optional: save weights for downstream / serving
    if args.save_weights:
        weights_path = out_root / args.weights_name
        torch.save(model.state_dict(), weights_path)
        print(f"[Weights] saved to {weights_path}")

    print(f"Saved predictions, metrics, and feature importance to {out_root}")


if __name__ == "__main__":
    main()
