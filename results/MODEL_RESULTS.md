# Material Performance Model Results

Model: inverse-distance weighted KNN surrogate, k=5, leave-one-out cross validation.

## Validation Metrics

| Target | R2 | MAE | RMSE | Bias |
|---|---:|---:|---:|---:|
| ultimate_tensile_strength_mpa | 0.649 | 21.038 | 29.796 | 2.056 |
| yield_strength_mpa | 0.606 | 11.011 | 14.499 | 1.078 |
| elongation_to_fracture_pct | 0.560 | 0.344 | 0.484 | -0.007 |
| xct_porosity_pct | 0.620 | 1.173 | 1.876 | -0.216 |
| vickers_hardness_hv | 0.275 | 6.140 | 8.196 | 0.601 |
| youngs_modulus_gpa | 0.604 | 3.414 | 4.476 | -0.036 |

## Top Predicted Material Process Windows

| Rank | Power W | Speed mm/s | Hatch mm | UTS MPa | Yield MPa | Elongation % | Porosity % | Score |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 200 | 450 | 0.100 | 383.3 | 226.0 | 3.67 | 0.142 | 170.1 |
| 2 | 220 | 500 | 0.100 | 382.3 | 225.7 | 3.65 | 0.138 | 169.7 |
| 3 | 200 | 500 | 0.100 | 382.0 | 225.7 | 3.64 | 0.139 | 169.5 |
| 4 | 180 | 400 | 0.100 | 383.0 | 225.6 | 3.61 | 0.177 | 169.4 |
| 5 | 220 | 550 | 0.100 | 381.8 | 225.5 | 3.63 | 0.138 | 169.3 |
| 6 | 200 | 400 | 0.100 | 382.9 | 225.2 | 3.62 | 0.187 | 169.3 |
| 7 | 200 | 450 | 0.090 | 382.9 | 225.3 | 3.61 | 0.190 | 169.2 |
| 8 | 220 | 300 | 0.100 | 380.6 | 223.0 | 3.72 | 0.201 | 169.2 |
| 9 | 220 | 450 | 0.100 | 382.2 | 224.8 | 3.63 | 0.181 | 169.2 |
| 10 | 200 | 400 | 0.110 | 382.8 | 225.2 | 3.60 | 0.195 | 169.1 |
| 11 | 420 | 450 | 0.100 | 385.8 | 236.8 | 3.53 | 0.295 | 169.0 |
| 12 | 180 | 400 | 0.110 | 382.8 | 225.5 | 3.59 | 0.194 | 169.0 |
| 13 | 200 | 300 | 0.090 | 382.0 | 222.8 | 3.65 | 0.220 | 169.0 |
| 14 | 180 | 350 | 0.100 | 383.1 | 224.4 | 3.58 | 0.208 | 169.0 |
| 15 | 240 | 300 | 0.100 | 379.2 | 223.0 | 3.75 | 0.181 | 168.9 |
| 16 | 220 | 300 | 0.110 | 381.5 | 223.4 | 3.66 | 0.212 | 168.9 |
| 17 | 180 | 400 | 0.090 | 382.8 | 225.2 | 3.58 | 0.200 | 168.9 |
| 18 | 220 | 500 | 0.090 | 381.8 | 223.9 | 3.61 | 0.180 | 168.9 |
| 19 | 200 | 400 | 0.090 | 382.8 | 224.6 | 3.59 | 0.211 | 168.9 |
| 20 | 220 | 450 | 0.110 | 381.8 | 224.0 | 3.61 | 0.184 | 168.9 |

## Boundary

These are coupon-level AlSi10Mg LPBF predictions, not validated piston durability predictions.
A real piston still requires alloy qualification, heat treatment/HIP, CNC finishing, CT inspection, fatigue testing, and dyno validation.
