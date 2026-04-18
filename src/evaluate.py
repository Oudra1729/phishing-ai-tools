"""
Métriques de classification, courbes ROC, matrices de confusion, comparaison de modèles.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    auc,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_curve,
)
from sklearn.pipeline import Pipeline


def classification_metrics(
    y_true: np.ndarray, y_pred: np.ndarray, y_score: Optional[np.ndarray] = None
) -> Dict[str, float]:
    """Retourne accuracy, precision, recall, F1 et AUC (si scores fournis)."""
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if y_score is not None and len(np.unique(y_true)) > 1:
        fpr, tpr, _ = roc_curve(y_true, y_score)
        out["auc"] = float(auc(fpr, tpr))
    else:
        out["auc"] = float("nan")
    return out


def plot_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    labels: Tuple[str, str] = ("Benign", "Phishing"),
    title: str = "Confusion matrix",
    save_path: Optional[Path] = None,
) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(5, 4))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=labels,
        yticklabels=labels,
        ax=ax,
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    plt.tight_layout()
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    plt.close(fig)


def plot_roc_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    title: str = "ROC curve",
    save_path: Optional[Path] = None,
) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"AUC = {roc_auc:.3f}")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(title)
    ax.legend(loc="lower right")
    plt.tight_layout()
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    plt.close(fig)


def compare_models_table(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Construit un tableau comparatif trié par F1 décroissant."""
    df = pd.DataFrame(rows)
    if "f1" in df.columns:
        df = df.sort_values("f1", ascending=False)
    return df


def save_metrics_json(metrics: Dict[str, Any], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)


def plot_feature_importance_rf(
    pipeline: Pipeline,
    top_k: int = 20,
    save_path: Optional[Path] = None,
) -> Optional[pd.DataFrame]:
    """
    Importance des features pour un Pipeline se terminant par RandomForestClassifier.
    """
    if "clf" not in pipeline.named_steps:
        return None
    clf = pipeline.named_steps["clf"]
    if not hasattr(clf, "feature_importances_"):
        return None
    prep = pipeline.named_steps.get("prep")
    if prep is None or not hasattr(prep, "get_feature_names_out"):
        return None
    try:
        names = prep.get_feature_names_out()
    except Exception:
        return None
    imp = clf.feature_importances_
    if len(names) != len(imp):
        return None
    df = pd.DataFrame({"feature": names, "importance": imp})
    df = df.sort_values("importance", ascending=False).head(top_k)

    fig, ax = plt.subplots(figsize=(8, max(4, top_k * 0.25)))
    sns.barplot(data=df, y="feature", x="importance", ax=ax, color="steelblue")
    ax.set_title("Random Forest — top feature importances")
    plt.tight_layout()
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return df


def error_analysis(
    urls: pd.Series,
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> Dict[str, pd.DataFrame]:
    """Sépare faux positifs et faux négatifs pour analyse qualitative."""
    fp_mask = (y_true == 0) & (y_pred == 1)
    fn_mask = (y_true == 1) & (y_pred == 0)
    fp = pd.DataFrame({"url": urls[fp_mask].values, "type": "false_positive"})
    fn = pd.DataFrame({"url": urls[fn_mask].values, "type": "false_negative"})
    return {"false_positives": fp, "false_negatives": fn}


def plot_feature_distributions(
    feature_matrix: np.ndarray,
    feature_names: List[str],
    y: np.ndarray,
    save_dir: Path,
) -> None:
    """Histogrammes par classe pour les premières features numériques."""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    X_df = pd.DataFrame(feature_matrix, columns=feature_names)
    X_df["label"] = y
    for col in feature_names[: min(6, len(feature_names))]:
        fig, ax = plt.subplots(figsize=(6, 3))
        for lab, sub in X_df.groupby("label"):
            sns.kdeplot(
                sub[col],
                label=f"class={lab}",
                ax=ax,
                warn_singular=False,
            )
        ax.set_title(f"Distribution — {col}")
        ax.legend()
        plt.tight_layout()
        fig.savefig(save_dir / f"dist_{col}.png", dpi=120)
        plt.close(fig)


def plot_correlation_heatmap(
    feature_matrix: np.ndarray,
    feature_names: List[str],
    save_path: Path,
) -> None:
    df = pd.DataFrame(feature_matrix, columns=feature_names)
    corr = df.corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=False, cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Corrélation entre features (handcrafted)")
    plt.tight_layout()
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
