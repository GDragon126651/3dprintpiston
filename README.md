# 3D Printed Piston Optimizer

Research dashboard for screening laser powder bed fusion AlSi10Mg process windows for advanced piston concepts.

The project downloads an open Zenodo process-structure-property dataset, trains standard-library ridge-regression surrogate models, reports metrics such as R2/MAE/RMSE, and builds a static HTML dashboard with process sliders and ranked candidate piston concepts.

## Data Source

- Luo et al., "Processing, microstructure, and mechanical property dataset for AlSi10Mg fabricated by laser powder bed fusion additive manufacturing"
- Zenodo: https://zenodo.org/records/10008435
- Data article: https://doi.org/10.1016/j.dib.2024.110130
- License: CC BY 4.0

## Run

```bash
python3 scripts/build_dataset.py
python3 -m http.server 8000 --directory webapp
```

Open `http://localhost:8000`.

## Engineering Boundary

The model is trained on coupon-level AlSi10Mg data, not on validated engine piston durability data. Piston mass saving, thermal relief, cost, performance, and value scores are concept-ranking estimates. A real piston requires alloy qualification, heat treatment/HIP, CNC finishing, CT inspection, fatigue testing, and dyno validation.
