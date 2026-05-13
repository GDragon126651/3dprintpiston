#!/usr/bin/env python3
"""
Build a compact ML payload for an LPBF AlSi10Mg piston concept dashboard.

The source dataset is the open Zenodo process-structure-property table from:
Luo et al., "Processing, microstructure, and mechanical property dataset for
AlSi10Mg fabricated by laser powder bed fusion additive manufacturing".

The script intentionally uses only the Python standard library so the project
can run on a fresh machine without pandas, numpy, or scikit-learn.
"""

from __future__ import annotations

import csv
import json
import math
import os
import random
import statistics
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "AlSi10Mg_PSP_feature_table.xlsx"
CSV_OUT = ROOT / "data" / "processed" / "alsi10mg_psp.csv"
PAYLOAD_OUT = ROOT / "webapp" / "model_payload.json"

ZENODO_URL = (
    "https://zenodo.org/records/10008435/files/"
    "AlSi10Mg%20PSP%20feature%20table.xlsx?download=1"
)

SOURCE = {
    "title": "Processing, microstructure, and mechanical property dataset for AlSi10Mg fabricated by laser powder bed fusion additive manufacturing",
    "authors": "Qixiang Luo, Nancy Huang, Tianyi Fu, Jinying Wang, Dean L. Bartles, Timothy W. Simpson, Allison M. Beese",
    "zenodo": "https://zenodo.org/records/10008435",
    "data_article": "https://doi.org/10.1016/j.dib.2024.110130",
    "license": "Creative Commons Attribution 4.0 International",
}


COLS = {
    "set_id": 0,
    "power_w": 2,
    "scan_speed_mm_s": 3,
    "layer_thickness_mm": 4,
    "hatch_spacing_mm": 5,
    "led_j_mm": 6,
    "ved_j_mm3": 7,
    "med": 8,
    "pv": 9,
    "roughness_avg_um": 10,
    "pore_sphericity": 25,
    "pore_diameter_um": 28,
    "xct_porosity_pct": 32,
    "arch_porosity_pct": 34,
    "hardness_hv": 36,
    "uts_mpa": 38,
    "yield_mpa": 40,
    "elongation_pct": 42,
    "modulus_gpa": 44,
}

FEATURES = [
    "power_w",
    "scan_speed_mm_s",
    "hatch_spacing_mm",
    "led_j_mm",
    "ved_j_mm3",
    "med",
    "pv",
]

TARGETS = [
    "uts_mpa",
    "yield_mpa",
    "elongation_pct",
    "xct_porosity_pct",
    "roughness_avg_um",
    "hardness_hv",
]


def download_dataset() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if RAW.exists() and RAW.stat().st_size > 10_000:
        return
    print(f"Downloading {ZENODO_URL}")
    urllib.request.urlretrieve(ZENODO_URL, RAW)


def _col_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + ord(char.upper()) - 64
    return index - 1


def _shared_strings(zf: zipfile.ZipFile) -> List[str]:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    strings: List[str] = []
    for si in root.findall("a:si", ns):
        strings.append("".join((t.text or "") for t in si.findall(".//a:t", ns)))
    return strings


def read_xlsx_rows(path: Path) -> List[List[str]]:
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        strings = _shared_strings(zf)
        root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows: List[List[str]] = []
        for row in root.findall(".//a:sheetData/a:row", ns):
            values: Dict[int, str] = {}
            for cell in row.findall("a:c", ns):
                ref = cell.attrib.get("r", "A1")
                value_node = cell.find("a:v", ns)
                if value_node is None:
                    continue
                value = value_node.text or ""
                if cell.attrib.get("t") == "s":
                    value = strings[int(value)]
                values[_col_index(ref)] = value
            if values:
                rows.append([values.get(i, "") for i in range(max(values) + 1)])
    return rows


def as_float(row: Sequence[str], index: int) -> float | None:
    if index >= len(row) or row[index] == "":
        return None
    try:
        return float(row[index])
    except ValueError:
        return None


def extract_records(rows: Sequence[Sequence[str]]) -> List[Dict[str, float]]:
    records: List[Dict[str, float]] = []
    for row in rows[4:]:
        record: Dict[str, float] = {}
        ok = True
        for name, idx in COLS.items():
            value = as_float(row, idx)
            if value is None:
                ok = False
                break
            record[name] = value
        if ok:
            records.append(record)
    return records


def write_csv(records: Sequence[Dict[str, float]]) -> None:
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(COLS)
    with CSV_OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record[field] for field in fields})


def mean_std(values: Sequence[float]) -> Tuple[float, float]:
    mu = statistics.fmean(values)
    sigma = statistics.pstdev(values) or 1.0
    return mu, sigma


def transpose(matrix: Sequence[Sequence[float]]) -> List[List[float]]:
    return [list(col) for col in zip(*matrix)]


def matmul(a: Sequence[Sequence[float]], b: Sequence[Sequence[float]]) -> List[List[float]]:
    bt = transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt] for row in a]


def solve_linear_system(a: List[List[float]], b: List[float]) -> List[float]:
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if abs(aug[col][col]) < 1e-12:
            aug[col][col] = 1e-12
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [v - factor * p for v, p in zip(aug[row], aug[col])]
    return [row[-1] for row in aug]


def polynomial_terms(x: Sequence[float]) -> List[float]:
    terms = [1.0]
    terms.extend(x)
    terms.extend(value * value for value in x)
    for i in range(len(x)):
        for j in range(i + 1, len(x)):
            terms.append(x[i] * x[j])
    return terms


@dataclass
class RidgeModel:
    target: str
    coef: List[float]
    feature_mean: List[float]
    feature_std: List[float]
    alpha: float

    def predict(self, features: Sequence[float]) -> float:
        scaled = [
            (value - self.feature_mean[i]) / self.feature_std[i]
            for i, value in enumerate(features)
        ]
        terms = polynomial_terms(scaled)
        return sum(c * t for c, t in zip(self.coef, terms))


def fit_ridge(x_rows: Sequence[Sequence[float]], y: Sequence[float], target: str, alpha: float) -> RidgeModel:
    means_stds = [mean_std([row[i] for row in x_rows]) for i in range(len(x_rows[0]))]
    means = [m for m, _ in means_stds]
    stds = [s for _, s in means_stds]
    design = [
        polynomial_terms([(value - means[i]) / stds[i] for i, value in enumerate(row)])
        for row in x_rows
    ]
    xt = transpose(design)
    xtx = matmul(xt, design)
    xty = [sum(row[i] * y[row_idx] for row_idx, row in enumerate(design)) for i in range(len(xtx))]
    for i in range(1, len(xtx)):
        xtx[i][i] += alpha
    return RidgeModel(target, solve_linear_system(xtx, xty), means, stds, alpha)


def metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> Dict[str, float]:
    mean_y = statistics.fmean(y_true)
    ss_res = sum((a - b) ** 2 for a, b in zip(y_true, y_pred))
    ss_tot = sum((a - mean_y) ** 2 for a in y_true) or 1.0
    mae = statistics.fmean(abs(a - b) for a, b in zip(y_true, y_pred))
    rmse = math.sqrt(statistics.fmean((a - b) ** 2 for a, b in zip(y_true, y_pred)))
    return {
        "r2": 1.0 - ss_res / ss_tot,
        "mae": mae,
        "rmse": rmse,
    }


def feature_stats(records: Sequence[Dict[str, float]]) -> Dict[str, List[float]]:
    stats = [mean_std([row[feature] for row in records]) for feature in FEATURES]
    return {
        "mean": [item[0] for item in stats],
        "std": [item[1] for item in stats],
    }


def knn_predict(
    records: Sequence[Dict[str, float]],
    stats: Dict[str, List[float]],
    features: Sequence[float],
    target: str,
    k: int = 5,
    power: float = 2.0,
) -> float:
    distances: List[Tuple[float, float]] = []
    for record in records:
        distance = math.sqrt(
            sum(
                ((features[i] - record[FEATURES[i]]) / stats["std"][i]) ** 2
                for i in range(len(FEATURES))
            )
        )
        distances.append((distance, record[target]))
    distances.sort(key=lambda item: item[0])
    nearest = distances[:k]
    if nearest and nearest[0][0] < 1e-12:
        return nearest[0][1]
    weights = [1.0 / (distance**power + 1e-9) for distance, _ in nearest]
    return sum(weight * value for weight, (_, value) in zip(weights, nearest)) / sum(weights)


def evaluate_models(records: Sequence[Dict[str, float]]) -> Tuple[Dict[str, RidgeModel], Dict[str, Dict[str, float]], Dict[str, List[float]]]:
    """Return ridge coefficients for auditability and KNN LOOCV metrics for runtime use."""
    stats = feature_stats(records)
    ridge_models: Dict[str, RidgeModel] = {}
    model_metrics: Dict[str, Dict[str, float]] = {}
    x_all = [[row[f] for f in FEATURES] for row in records]
    for target in TARGETS:
        y_all = [row[target] for row in records]
        ridge_models[target] = fit_ridge(x_all, y_all, target, alpha=2.5)
        pred = []
        for i, record in enumerate(records):
            train = list(records[:i]) + list(records[i + 1 :])
            pred.append(knn_predict(train, stats, [record[f] for f in FEATURES], target))
        model_metrics[target] = metrics(y_all, pred)
    return ridge_models, model_metrics, stats


def piston_cost_index(power_w: float, speed: float, hatch: float, layer: float = 0.06) -> float:
    deposition_rate = max(speed * hatch * layer, 0.001)
    normalized_machine_time = 1.0 / deposition_rate
    energy_factor = power_w / 260.0
    powder_risk = 1.0 + 0.18 * max(0.0, hatch - 0.12) / 0.03
    return normalized_machine_time * energy_factor * powder_risk


def generate_candidates(records: Sequence[Dict[str, float]], stats: Dict[str, List[float]]) -> List[Dict[str, float]]:
    candidates: List[Dict[str, float]] = []
    for power in range(120, 421, 20):
        for speed in range(300, 1601, 50):
            for hatch in [0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15]:
                layer = 0.06
                led = power / speed
                ved = power / (speed * hatch * layer)
                med = power / math.sqrt(speed)
                pv = power * speed / 1000.0
                features = [power, speed, hatch, led, ved, med, pv]
                pred = {target: knn_predict(records, stats, features, target) for target in TARGETS}
                if pred["xct_porosity_pct"] < 0:
                    pred["xct_porosity_pct"] = 0.0
                cost = piston_cost_index(power, speed, hatch, layer)
                density_g_cm3 = 2.67 * (1 - min(pred["xct_porosity_pct"], 20) / 100.0)
                strength_to_weight = pred["uts_mpa"] / density_g_cm3
                printable_mass_saving_pct = max(0.0, min(18.0, 4.0 + 0.03 * (pred["yield_mpa"] - 180) + 0.2 * pred["elongation_pct"]))
                thermal_relief_score = max(0.0, min(100.0, 100.0 - 10.0 * pred["roughness_avg_um"] - 16.0 * pred["xct_porosity_pct"]))
                performance = (
                    0.33 * strength_to_weight
                    + 2.1 * pred["elongation_pct"]
                    + 1.4 * printable_mass_saving_pct
                    + 0.22 * thermal_relief_score
                    - 4.5 * pred["xct_porosity_pct"]
                )
                value_score = performance / (1.0 + 0.012 * cost)
                candidates.append(
                    {
                        "power_w": power,
                        "scan_speed_mm_s": speed,
                        "hatch_spacing_mm": round(hatch, 3),
                        "layer_thickness_mm": layer,
                        "led_j_mm": led,
                        "ved_j_mm3": ved,
                        "cost_index": cost,
                        "predicted_mass_saving_pct": printable_mass_saving_pct,
                        "thermal_relief_score": thermal_relief_score,
                        "performance_index": performance,
                        "value_score": value_score,
                        **pred,
                    }
                )
    return sorted(candidates, key=lambda row: row["value_score"], reverse=True)[:80]


def correlations(records: Sequence[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    for target in TARGETS:
        y = [row[target] for row in records]
        y_mu, y_std = mean_std(y)
        result[target] = {}
        for feature in FEATURES:
            x = [row[feature] for row in records]
            x_mu, x_std = mean_std(x)
            corr = statistics.fmean(
                ((a - x_mu) / x_std) * ((b - y_mu) / y_std) for a, b in zip(x, y)
            )
            result[target][feature] = corr
    return result


def build_payload(records: Sequence[Dict[str, float]]) -> Dict[str, object]:
    models, model_metrics, stats = evaluate_models(records)
    candidates = generate_candidates(records, stats)
    summaries = {
        field: {
            "min": min(row[field] for row in records),
            "mean": statistics.fmean(row[field] for row in records),
            "max": max(row[field] for row in records),
        }
        for field in FEATURES + TARGETS
    }
    return {
        "source": SOURCE,
        "generated_by": "scripts/build_dataset.py",
        "notes": [
            "Models are material/process surrogates trained on AlSi10Mg coupon data, not validated piston durability models.",
            "Piston mass saving, thermal relief, performance, and cost scores are engineering estimates for concept ranking.",
            "Do not manufacture or run an engine piston from this dashboard without full alloy qualification, HIP/heat treatment, CT inspection, and dyno validation.",
        ],
        "features": FEATURES,
        "targets": TARGETS,
        "rows": records,
        "metrics": model_metrics,
        "summaries": summaries,
        "correlations": correlations(records),
        "top_candidates": candidates,
        "knn": {
            "k": 5,
            "distance_power": 2.0,
            "feature_mean": stats["mean"],
            "feature_std": stats["std"],
        },
        "models": {
            target: {
                "coef": model.coef,
                "feature_mean": model.feature_mean,
                "feature_std": model.feature_std,
                "alpha": model.alpha,
            }
            for target, model in models.items()
        },
    }


def main() -> None:
    download_dataset()
    rows = read_xlsx_rows(RAW)
    records = extract_records(rows)
    if len(records) < 50:
        raise SystemExit(f"Expected at least 50 complete records, found {len(records)}")
    write_csv(records)
    payload = build_payload(records)
    PAYLOAD_OUT.parent.mkdir(parents=True, exist_ok=True)
    PAYLOAD_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {CSV_OUT.relative_to(ROOT)} with {len(records)} rows")
    print(f"Wrote {PAYLOAD_OUT.relative_to(ROOT)}")
    for target, m in payload["metrics"].items():
        print(f"{target:18s} R2={m['r2']:.3f} MAE={m['mae']:.3f} RMSE={m['rmse']:.3f}")
    best = payload["top_candidates"][0]
    print(
        "Best concept: "
        f"P={best['power_w']} W, v={best['scan_speed_mm_s']} mm/s, "
        f"h={best['hatch_spacing_mm']} mm, UTS={best['uts_mpa']:.1f} MPa, "
        f"cost index={best['cost_index']:.1f}"
    )


if __name__ == "__main__":
    main()
