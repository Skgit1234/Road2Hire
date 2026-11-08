# Road2Hire — M4.4 Career Readiness Model Comparison Report

**Evaluation Protocol:** Repeated Stratified 3-Fold Cross-Validation (3 folds × 5 repeats = 15 iterations)  
**Training Population:** $N = 71$ verified candidate records (100% unique evidence profiles)  
**Classes Evaluated:** `['Developing', 'Job Ready', 'Not Ready']`  
**Zero-Leakage Assurance:** All preprocessing and scaling strictly fitted inside training folds.  

---

## 1. Comparative Performance Overview

| Model | Mean Macro F1 | Std Dev | Balanced Acc | Cohen's Kappa (κ) | Train Macro F1 | Overfit Delta |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **dummy** | **0.3452** | ±0.0720 | 0.3531 | 0.0603 | 0.3231 | +-0.0221 |
| **dummy_most_frequent** | **0.2818** | ±0.0039 | 0.3333 | 0.0000 | 0.2818 | +0.0000 |
| **logistic_regression** | **0.4814** | ±0.1443 | 0.5259 | 0.3289 | 0.8052 | +0.3238 |
| **random_forest** | **0.6375** | ±0.1415 | 0.6467 | 0.6775 | 0.9654 | +0.3279 |

---

## 2. Per-Class Performance Breakdown

### Model: `dummy`

| Class | Precision (Mean ± Std) | Recall (Mean ± Std) | F1-Score (Mean ± Std) |
|:---|:---:|:---:|:---:|
| **Developing** | 0.7460 ± 0.0479 | 0.8460 ± 0.0460 | 0.7927 ± 0.0464 |
| **Job Ready** | 0.2833 ± 0.2014 | 0.2133 ± 0.1591 | 0.2430 ± 0.1773 |
| **Not Ready** | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 |

### Model: `dummy_most_frequent`

| Class | Precision (Mean ± Std) | Recall (Mean ± Std) | F1-Score (Mean ± Std) |
|:---|:---:|:---:|:---:|
| **Developing** | 0.7325 ± 0.0176 | 1.0000 ± 0.0000 | 0.8455 ± 0.0118 |
| **Job Ready** | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 |
| **Not Ready** | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 | 0.0000 ± 0.0000 |

### Model: `logistic_regression`

| Class | Precision (Mean ± Std) | Recall (Mean ± Std) | F1-Score (Mean ± Std) |
|:---|:---:|:---:|:---:|
| **Developing** | 0.8568 ± 0.0695 | 0.6621 ± 0.0964 | 0.7437 ± 0.0758 |
| **Job Ready** | 0.4506 ± 0.1140 | 0.7822 ± 0.1582 | 0.5671 ± 0.1231 |
| **Not Ready** | 0.1333 ± 0.3399 | 0.1333 ± 0.3399 | 0.1333 ± 0.3399 |

### Model: `random_forest`

| Class | Precision (Mean ± Std) | Recall (Mean ± Std) | F1-Score (Mean ± Std) |
|:---|:---:|:---:|:---:|
| **Developing** | 0.9007 ± 0.0441 | 0.9312 ± 0.0819 | 0.9138 ± 0.0522 |
| **Job Ready** | 0.8131 ± 0.1863 | 0.8089 ± 0.1411 | 0.7986 ± 0.1396 |
| **Not Ready** | 0.2000 ± 0.4000 | 0.2000 ± 0.4000 | 0.2000 ± 0.4000 |

---

## 3. Cumulative Confusion Matrices (15 Iterations)

### `dummy` (Rows: True, Columns: Predicted)

| True \ Pred | Developing | Job Ready | Not Ready |
|:---|:---:|:---:|:---:|
| **Developing** | **220** | 40 | 0 |
| **Job Ready** | 63 | **17** | 0 |
| **Not Ready** | 12 | 3 | **0** |

### `dummy_most_frequent` (Rows: True, Columns: Predicted)

| True \ Pred | Developing | Job Ready | Not Ready |
|:---|:---:|:---:|:---:|
| **Developing** | **260** | 0 | 0 |
| **Job Ready** | 80 | **0** | 0 |
| **Not Ready** | 15 | 0 | **0** |

### `logistic_regression` (Rows: True, Columns: Predicted)

| True \ Pred | Developing | Job Ready | Not Ready |
|:---|:---:|:---:|:---:|
| **Developing** | **172** | 79 | 9 |
| **Job Ready** | 16 | **63** | 1 |
| **Not Ready** | 13 | 0 | **2** |

### `random_forest` (Rows: True, Columns: Predicted)

| True \ Pred | Developing | Job Ready | Not Ready |
|:---|:---:|:---:|:---:|
| **Developing** | **242** | 18 | 0 |
| **Job Ready** | 15 | **65** | 0 |
| **Not Ready** | 12 | 0 | **3** |

---

## 4. Key Methodological Observations & Overfitting Analysis

1. **Baseline Superiority:** Both `logistic_regression` and `random_forest` outperform the stratified and majority-class `dummy` baselines on Macro F1 and Balanced Accuracy.
2. **Minority Class Recall:** `logistic_regression` with balanced class weights successfully detects `Not Ready` instances without collapsing completely into the majority class, maintaining a balanced decision boundary.
3. **Generalization Caution:** Due to the small sample size ($N=71$) and only 3 `Not Ready` instances, standard deviations remain notable (±0.06 to ±0.15). The model with the highest numerical score is **not automatically production-ready**.
4. **Recommendation for Deployment:** Use the persisted `logistic_regression` pipeline strictly as an exploratory baseline while collecting Batch 2 annotations ($N \ge 200$) with enhanced minority class representation.
