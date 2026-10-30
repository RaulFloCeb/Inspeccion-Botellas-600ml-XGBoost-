"""Compara el modelo solo contra la decisión final de la API (regla + modelo).

Uso: python scripts/evaluate_model.py
"""
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
model = joblib.load(ROOT / "model" / "xgb_model.joblib")
meta = json.loads((ROOT / "model" / "model_metadata.json").read_text(encoding="utf-8"))
threshold = meta["threshold"]


def proba(fill, label):
    features = np.column_stack([fill, label]).astype(float)
    return model.predict_proba(features)[:, 1]


def rule(fill, label):
    return (fill < 588) | (fill > 612) | (label == 0)


print(f"Umbral del modelo: {threshold:.6f}\n")

print("CASOS DE PRUEBA")
print(f"{'caso':24}{'ml':>8}{'etq':>5}{'p_rechazo':>11}{'esperado':>11}{'modelo solo':>13}{'modelo 0.5':>12}{'API':>11}")
cases = [
    ("TC-01 conforme", 598.35, 1), ("TC-02 bajo llenado", 580.0, 1), ("TC-03 alto llenado", 618.5, 1),
    ("TC-04 sin etiqueta", 600.0, 0), ("TC-05 defecto doble", 575.0, 0), ("Limite 588.0", 588.0, 1),
    ("Limite 612.0", 612.0, 1), ("Outlier 999.0", 999.0, 1),
]
name = {True: "RECHAZADO", False: "ACEPTADO"}
for case, fill, label in cases:
    p = float(proba(np.array([fill]), np.array([label]))[0])
    expected = bool(rule(np.array([fill]), np.array([label]))[0])
    final = expected or p >= threshold
    print(f"{case:24}{fill:>8}{label:>5}{p:>11.6f}{name[expected]:>11}{name[p >= threshold]:>13}{name[p >= 0.5]:>12}{name[final]:>11}")

print("\nBARRIDO 570-630 ml, paso 0.01 ml, con etiqueta (espacio que el dataset no cubre)")
grid = np.round(np.arange(570, 630.005, 0.01), 2)
ones = np.ones_like(grid)
p_grid = proba(grid, ones)
spec = rule(grid, ones)
print(f"{'decision':24}{'defectos aceptados':>20}{'conformes rechazadas':>22}")
for label, pred in [
    ("Modelo umbral optimo", p_grid >= threshold),
    ("Modelo umbral 0.5", p_grid >= 0.5),
    ("API (regla + modelo)", spec | (p_grid >= threshold)),
]:
    print(f"{label:24}{int((spec & ~pred).sum()):>20}{int((~spec & pred).sum()):>22}")
print(f"Puntos evaluados: {len(grid)} ({int(spec.sum())} fuera de especificacion)")

changes = grid[1:][(p_grid >= 0.5)[1:] != (p_grid >= 0.5)[:-1]]
print(f"Cortes del modelo con umbral 0.5: {changes.tolist()} ml (especificacion: 588 y 612 ml)")

print("\nDATASET COMPLETO (5,000 registros, incluye entrenamiento)")
df = pd.read_csv(ROOT / "data" / "dataset_inspeccion_0_2_limpio.csv")
fill, label, y = df["fill_level_ml"].to_numpy(), df["label_present_num"].to_numpy(), df["target"].to_numpy() == 1
p_df = proba(fill, label)
print(f"{'decision':24}{'FN':>6}{'FP':>6}{'TP':>6}{'TN':>7}")
for label_name, pred in [
    ("Modelo umbral optimo", p_df >= threshold),
    ("Modelo umbral 0.5", p_df >= 0.5),
    ("API (regla + modelo)", rule(fill, label) | (p_df >= threshold)),
]:
    print(f"{label_name:24}{int((y & ~pred).sum()):>6}{int((~y & pred).sum()):>6}{int((y & pred).sum()):>6}{int((~y & ~pred).sum()):>7}")
