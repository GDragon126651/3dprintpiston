# LPBF AlSi10Mg Material Performance Predictor

Machine-learning code for predicting LPBF AlSi10Mg material performance from process parameters.

The project downloads an open Zenodo process-structure-property dataset, parses it with the Python standard library, validates an inverse-distance KNN surrogate model, and writes final machine-learning results including R2, MAE, RMSE, bias, and top predicted process windows.

## Data Source

- Luo et al., "Processing, microstructure, and mechanical property dataset for AlSi10Mg fabricated by laser powder bed fusion additive manufacturing"
- Zenodo: https://zenodo.org/records/10008435
- Data article: https://doi.org/10.1016/j.dib.2024.110130
- License: CC BY 4.0

## Run

```bash
python3 scripts/train_material_model.py
```

Main outputs:

- `data/processed/alsi10mg_material_properties.csv`
- `results/model_report.json`
- `results/MODEL_RESULTS.md`

Optional local HTML results viewer:

```bash
python3 -m http.server 8001
```

Open `http://127.0.0.1:8001/webapp/`.

## Engineering Boundary

The model is trained on coupon-level AlSi10Mg data, not on validated engine piston durability data. A real piston requires alloy qualification, heat treatment/HIP, CNC finishing, CT inspection, fatigue testing, and dyno validation.
