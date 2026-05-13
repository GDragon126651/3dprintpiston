#!/usr/bin/env python3
"""
Material/performance prediction for LPBF AlSi10Mg.

This script downloads/parses the open Zenodo process-structure-property table,
builds a standard-library machine-learning model, validates it with leave-one-
out cross validation, and writes final prediction reports.

No external packages are required.
"""

from __future__ import annotations

import csv
import json
import math
import statistics
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "AlSi10Mg_PSP_feature_table.xlsx"
DATA_CSV = ROOT / "data" / "processed" / "alsi10mg_material_properties.csv"
REPORT_JSON = ROOT / "results" / "model_report.json"
REPORT_MD = ROOT / "results" / "MODEL_RESULTS.md"

ZENODO_URL = (
    "https://zenodo.org/records/10008435/files/"
    "AlSi10Mg%20PSP%20feature%20table.xlsx?download=1"
)

SOURCE = {
    "dataset": "Processing, microstructure, and mechanical property dataset for AlSi10Mg fabricated by laser powder bed fusion additive manufacturing",
    "authors": "Qixiang Luo, Nancy Huang, Tianyi Fu, Jinying Wang, Dean L. Bartles, Timothy W. Simpson, Allison M. Beese",
    "zenodo": "https://zenodo.org/records/10008435",
    "data_article": "https://doi.org/10.1016/j.dib.2024.110130",
    "license": "CC BY 4.0",
}

COLS = {
    "set_id": 0,
    "power_w": 2,
    "scan_speed_mm_s": 3,
    "layer_thickness_mm": 4,
    "hatch_spacing_mm": 5,
    "linear_energy_density_j_mm": 6,
    "volumetric_energy_density_j_mm3": 7,
    "modified_energy_density": 8,
    "power_speed_product": 9,
    "surface_roughness_avg_um": 10,
    "xct_porosity_pct": 32,
    "archimedes_porosity_pct": 34,
    "vickers_hardness_hv": 36,
    "ultimate_tensile_strength_mpa": 38,
    "yield_strength_mpa": 40,
    "elongation_to_fracture_pct": 42,
    "youngs_modulus_gpa": 44,
}

FEATURES = [
    "power_w",
    "scan_speed_mm_s",
    "hatch_spacing_mm",
    "linear_energy_density_j_mm",
    "volumetric_energy_density_j_mm3",
    "modified_energy_density",
    "power_speed_product",
]

TARGETS = [
    "ultimate_tensile_strength_mpa",
    "yield_strength_mpa",
    "elongation_to_fracture_pct",
    "xct_porosity_pct",
    "vickers_hardness_hv",
    "youngs_modulus_gpa",
]


def download_dataset() -> None:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if RAW.exists() and RAW.stat().st_size > 10_000:
        return
    urllib.request.urlretrieve(ZENODO_URL, RAW)


def col_index(cell_ref: str) -> int:
    value = 0
    for char in "".join(ch for ch in cell_ref if ch.isalpha()):
        value = value * 26 + ord(char.upper()) - 64
    return value - 1


def read_xlsx(path: Path) -> List[List[str]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        shared = []
        strings_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for item in strings_root.findall("x:si", ns):
            shared.append("".join((node.text or "") for node in item.findall(".//x:t", ns)))

        rows = []
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        for row in sheet.findall(".//x:sheetData/x:row", ns):
            values: Dict[int, str] = {}
            for cell in row.findall("x:c", ns):
                node = cell.find("x:v", ns)
                if node is None:
                    continue
                value = node.text or ""
                if cell.attrib.get("t") == "s":
                    value = shared[int(value)]
                values[col_index(cell.attrib["r"])] = value
            if values:
                rows.append([values.get(i, "") for i in range(max(values) + 1)])
    return rows


def to_float(row: Sequence[str], idx: int) -> float | None:
    if idx >= len(row) or row[idx] == "":
        return None
    try:
        return float(row[idx])
    except ValueError:
        return None


def extract_records(rows: Sequence[Sequence[str]]) -> List[Dict[str, float]]:
    records: List[Dict[str, float]] = []
    for row in rows[4:]:
        record: Dict[str, float] = {}
        for name, idx in COLS.items():
            value = to_float(row, idx)
            if value is None:
                record = {}
                break
            record[name] = value
        if record:
            records.append(record)
    return records


def write_dataset(records: Sequence[Dict[str, float]]) -> None:
    DATA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with DATA_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, list(COLS))
        writer.writeheader()
        writer.writerows(records)


def mean_std(values: Sequence[float]) -> Tuple[float, float]:
    mean = statistics.fmean(values)
    std = statistics.pstdev(values) or 1.0
    return mean, std


def feature_stats(records: Sequence[Dict[str, float]]) -> Dict[str, List[float]]:
    pairs = [mean_std([row[name] for row in records]) for name in FEATURES]
    return {"mean": [p[0] for p in pairs], "std": [p[1] for p in pairs]}


def predict_knn(
    train: Sequence[Dict[str, float]],
    stats: Dict[str, List[float]],
    feature_values: Sequence[float],
    target: str,
    k: int = 5,
    distance_power: float = 2.0,
) -> float:
    distances = []
    for row in train:
        d = math.sqrt(
            sum(
                ((feature_values[i] - row[FEATURES[i]]) / stats["std"][i]) ** 2
                for i in range(len(FEATURES))
            )
        )
        distances.append((d, row[target]))
    distances.sort(key=lambda item: item[0])
    nearest = distances[:k]
    if nearest[0][0] < 1e-12:
        return nearest[0][1]
    weights = [1 / (d**distance_power + 1e-9) for d, _ in nearest]
    return sum(w * y for w, (_, y) in zip(weights, nearest)) / sum(weights)


def metrics(actual: Sequence[float], predicted: Sequence[float]) -> Dict[str, float]:
    mean_actual = statistics.fmean(actual)
    ss_res = sum((a - p) ** 2 for a, p in zip(actual, predicted))
    ss_tot = sum((a - mean_actual) ** 2 for a in actual) or 1.0
    errors = [p - a for a, p in zip(actual, predicted)]
    return {
        "r2": 1 - ss_res / ss_tot,
        "mae": statistics.fmean(abs(e) for e in errors),
        "rmse": math.sqrt(statistics.fmean(e * e for e in errors)),
        "bias": statistics.fmean(errors),
    }


def validate(records: Sequence[Dict[str, float]], stats: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
    output: Dict[str, Dict[str, float]] = {}
    for target in TARGETS:
        actual = []
        predicted = []
        for i, row in enumerate(records):
            train = list(records[:i]) + list(records[i + 1 :])
            x = [row[name] for name in FEATURES]
            actual.append(row[target])
            predicted.append(predict_knn(train, stats, x, target))
        output[target] = metrics(actual, predicted)
    return output


def correlations(records: Sequence[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    result: Dict[str, Dict[str, float]] = {}
    for target in TARGETS:
        y = [row[target] for row in records]
        y_mean, y_std = mean_std(y)
        result[target] = {}
        for feature in FEATURES:
            x = [row[feature] for row in records]
            x_mean, x_std = mean_std(x)
            corr = statistics.fmean(
                ((a - x_mean) / x_std) * ((b - y_mean) / y_std)
                for a, b in zip(x, y)
            )
            result[target][feature] = corr
    return result


def predict_grid(records: Sequence[Dict[str, float]], stats: Dict[str, List[float]]) -> List[Dict[str, float]]:
    candidates: List[Dict[str, float]] = []
    for power in range(120, 421, 20):
        for speed in range(300, 1601, 50):
            for hatch in [0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15]:
                layer = 0.06
                x = [
                    power,
                    speed,
                    hatch,
                    power / speed,
                    power / (speed * hatch * layer),
                    power / math.sqrt(speed),
                    power * speed / 1000.0,
                ]
                pred = {target: predict_knn(records, stats, x, target) for target in TARGETS}
                pred["xct_porosity_pct"] = max(0.0, pred["xct_porosity_pct"])
                density = 2.67 * (1 - min(pred["xct_porosity_pct"], 20) / 100)
                strength_to_density = pred["ultimate_tensile_strength_mpa"] / density
                ductility_factor = pred["elongation_to_fracture_pct"]
                defect_penalty = 8.0 * pred["xct_porosity_pct"]
                performance_score = strength_to_density + 7.5 * ductility_factor - defect_penalty
                candidates.append(
                    {
                        "power_w": power,
                        "scan_speed_mm_s": speed,
                        "hatch_spacing_mm": hatch,
                        "layer_thickness_mm": layer,
                        "material_performance_score": performance_score,
                        **pred,
                    }
                )
    return sorted(candidates, key=lambda item: item["material_performance_score"], reverse=True)[:20]


def summaries(records: Sequence[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
    return {
        name: {
            "min": min(row[name] for row in records),
            "mean": statistics.fmean(row[name] for row in records),
            "max": max(row[name] for row in records),
        }
        for name in FEATURES + TARGETS
    }


def write_reports(report: Dict[str, object]) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# Material Performance Model Results",
        "",
        "Model: inverse-distance weighted KNN surrogate, k=5, leave-one-out cross validation.",
        "",
        "## Validation Metrics",
        "",
        "| Target | R2 | MAE | RMSE | Bias |",
        "|---|---:|---:|---:|---:|",
    ]
    for target, m in report["metrics"].items():
        lines.append(
            f"| {target} | {m['r2']:.3f} | {m['mae']:.3f} | {m['rmse']:.3f} | {m['bias']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Top Predicted Material Process Windows",
            "",
            "| Rank | Power W | Speed mm/s | Hatch mm | UTS MPa | Yield MPa | Elongation % | Porosity % | Score |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for i, row in enumerate(report["top_predictions"], 1):
        lines.append(
            f"| {i} | {row['power_w']:.0f} | {row['scan_speed_mm_s']:.0f} | {row['hatch_spacing_mm']:.3f} | "
            f"{row['ultimate_tensile_strength_mpa']:.1f} | {row['yield_strength_mpa']:.1f} | "
            f"{row['elongation_to_fracture_pct']:.2f} | {row['xct_porosity_pct']:.3f} | "
            f"{row['material_performance_score']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "These are coupon-level AlSi10Mg LPBF predictions, not validated piston durability predictions.",
            "A real piston still requires alloy qualification, heat treatment/HIP, CNC finishing, CT inspection, fatigue testing, and dyno validation.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    download_dataset()
    records = extract_records(read_xlsx(RAW))
    if len(records) < 50:
        raise SystemExit(f"Expected at least 50 records, found {len(records)}")
    write_dataset(records)
    stats = feature_stats(records)
    report = {
        "source": SOURCE,
        "model": {
            "type": "inverse_distance_weighted_knn",
            "k": 5,
            "validation": "leave_one_out_cross_validation",
            "features": FEATURES,
            "targets": TARGETS,
        },
        "record_count": len(records),
        "metrics": validate(records, stats),
        "summaries": summaries(records),
        "correlations": correlations(records),
        "top_predictions": predict_grid(records, stats),
    }
    write_reports(report)
    print(f"Rows: {len(records)}")
    print(f"Wrote {DATA_CSV.relative_to(ROOT)}")
    print(f"Wrote {REPORT_JSON.relative_to(ROOT)}")
    print(f"Wrote {REPORT_MD.relative_to(ROOT)}")
    for target, m in report["metrics"].items():
        print(f"{target:34s} R2={m['r2']:.3f} MAE={m['mae']:.3f} RMSE={m['rmse']:.3f}")


if __name__ == "__main__":
    main()
