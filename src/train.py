"""Reentrena el modelo y exporta model/xgb_model.joblib y model/model_metadata.json.

Reproduce el notebook notebooks/Modelo_XGBoost_Rechazo_botellas_0_2.ipynb
(mismo split, semilla e hiperparámetros) con versiones fijas de librerías.

Uso: python -m src.train
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "data" / "dataset_inspeccion_0_2_limpio.csv"
MODEL_PATH = ROOT / "model" / "xgb_model.joblib"
METADATA_PATH = ROOT / "model" / "model_metadata.json"
FEATURES = ["fill_level_ml", "label_present_num"]
SEED = 42


def metrics_at(y_true, proba, threshold):
    y_pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def main():
    df = pd.read_csv(DATASET)
    X = df[FEATURES]
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    scale_pos_weight = float((y_train == 0).sum() / (y_train == 1).sum())
    model = xgb.XGBClassifier(
        scale_pos_weight=scale_pos_weight,
        random_state=SEED,
        eval_metric="logloss",
        n_estimators=100,
        learning_rate=0.1,
    )
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]

    precisions, recalls, thresholds = precision_recall_curve(y_test, proba)
    f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-10)
    best_idx = int(np.argmax(f1_scores))
    best_threshold = float(thresholds[best_idx]) if best_idx < len(thresholds) else 0.5

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")

    metadata = {
        "model_version": "1.0.0",
        "features": FEATURES,
        "threshold": best_threshold,
        "scale_pos_weight": scale_pos_weight,
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_rejects": int(y_train.sum()),
        "test_rejects": int(y_test.sum()),
        "roc_auc_test": round(float(roc_auc_score(y_test, proba)), 4),
        "cv_roc_auc_mean": round(float(cv_scores.mean()), 4),
        "cv_roc_auc_std": round(float(cv_scores.std()), 4),
        "metrics_threshold_0_5": metrics_at(y_test, proba, 0.5),
        "metrics_threshold_optimo": metrics_at(y_test, proba, best_threshold),
        "versions": {
            "xgboost": xgb.__version__,
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
        },
    }

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
