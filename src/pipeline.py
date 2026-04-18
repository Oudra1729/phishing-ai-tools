#!/usr/bin/env python3
"""
Pipeline complet : chargement, features, entraînement multi-modèles, évaluation,
tests adversariaux, sauvegarde des artefacts (métriques, figures, modèles).

Exécution depuis la racine du projet :
    python src/pipeline.py
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

# Racine du projet sur le path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.evaluate import (
    classification_metrics,
    compare_models_table,
    error_analysis,
    plot_confusion_matrix,
    plot_correlation_heatmap,
    plot_feature_distributions,
    plot_feature_importance_rf,
    plot_roc_curve,
    save_metrics_json,
)
from src.features import FeatureExtractor, get_handcrafted_feature_names
from src.generator import generate_mixed_test_urls, generate_phishing_urls
from src.model import ModelTrainer, build_model_pipelines


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def load_config(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dirs(cfg: Dict[str, Any]) -> None:
    for key in ("models_dir", "metrics_dir", "plots_dir"):
        Path(cfg["paths"][key]).mkdir(parents=True, exist_ok=True)


def load_dataset(cfg: Dict[str, Any]) -> pd.DataFrame:
    paths = cfg["paths"]
    data_cfg = cfg["data"]
    csv_path = ROOT / paths["data_csv"]
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Dataset introuvable : {csv_path}. Lancez : python scripts/generate_sample_data.py"
        )
    df = pd.read_csv(csv_path)
    url_col = data_cfg["url_column"]
    lab_col = data_cfg["label_column"]
    df = df[[url_col, lab_col]].dropna()
    df[url_col] = df[url_col].astype(str)
    df[lab_col] = df[lab_col].astype(int)
    return df


def adversarial_evaluation(
    pipeline,
    phishing_urls: List[str],
) -> Dict[str, float]:
    """
    Taux d'« attaque réussie » : proportion d'URLs phishing prédites comme bénignes (0).
    """
    X = pd.DataFrame({"url": phishing_urls})
    pred = pipeline.predict(X)
    pred = np.asarray(pred).astype(int)
    n = len(phishing_urls)
    evaded = int(np.sum(pred == 0))
    return {
        "n_generated_phishing": float(n),
        "predicted_as_benign": float(evaded),
        "attack_success_rate": float(evaded / n) if n else 0.0,
        "detected_as_phishing": float(np.sum(pred == 1)),
    }


def run_pipeline(config_path: Path) -> None:
    log = logging.getLogger("pipeline")
    cfg = load_config(config_path)
    ensure_dirs(cfg)

    seed = int(cfg["project"].get("random_seed", 42))
    data_cfg = cfg["data"]
    url_col = data_cfg["url_column"]
    lab_col = data_cfg["label_column"]

    df = load_dataset(cfg)
    log.info("Dataset chargé : %d lignes", len(df))

    X = df[[url_col]].rename(columns={url_col: "url"})
    y = df[lab_col].values

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=float(data_cfg.get("test_size", 0.2)),
        random_state=seed,
        stratify=y if data_cfg.get("stratify", True) else None,
    )

    models = build_model_pipelines(cfg)
    comparison_rows: List[Dict[str, Any]] = []
    paths = cfg["paths"]
    plots_dir = ROOT / paths["plots_dir"]
    metrics_dir = ROOT / paths["metrics_dir"]
    models_dir = ROOT / paths["models_dir"]

    # Visualisations exploratoires sur features artisanales (train)
    extractor = FeatureExtractor(
        suspicious_keywords=cfg.get("features", {}).get("suspicious_keywords")
    )
    X_hand_train = extractor.transform(X_train["url"])
    fnames = get_handcrafted_feature_names()
    plot_feature_distributions(
        X_hand_train,
        fnames,
        y_train,
        plots_dir / "feature_distributions",
    )
    plot_correlation_heatmap(
        X_hand_train,
        fnames,
        plots_dir / "correlation_handcrafted.png",
    )

    trained: Dict[str, ModelTrainer] = {}

    for name, pipe in models.items():
        log.info("Entraînement : %s", name)
        trainer = ModelTrainer(pipe, name=name)
        trainer.train(X_train, y_train)
        trained[name] = trainer

        y_pred = trainer.predict(X_test)
        try:
            proba = trainer.predict_proba(X_test)[:, 1]
        except Exception:
            proba = None

        m = classification_metrics(y_test, y_pred, proba)
        m["model"] = name
        comparison_rows.append(m)

        plot_confusion_matrix(
            y_test,
            y_pred,
            title=f"Confusion matrix — {name}",
            save_path=plots_dir / f"confusion_{name}.png",
        )
        if proba is not None and len(np.unique(y_test)) > 1:
            plot_roc_curve(
                y_test,
                proba,
                title=f"ROC — {name}",
                save_path=plots_dir / f"roc_{name}.png",
            )

        save_path = models_dir / f"{name}.joblib"
        trainer.save_model(save_path)
        log.info("Modèle sauvegardé : %s", save_path)

        if name == "random_forest":
            plot_feature_importance_rf(
                trainer.model,
                top_k=25,
                save_path=plots_dir / "feature_importance_random_forest.png",
            )

    table = compare_models_table(comparison_rows)
    table_path = metrics_dir / "model_comparison.csv"
    table.to_csv(table_path, index=False)
    log.info("Tableau comparatif : %s", table_path)
    save_metrics_json(
        {"comparison": comparison_rows},
        metrics_dir / "metrics_summary.json",
    )

    # Meilleur modèle (F1)
    best_name = str(table.iloc[0]["model"])
    best_trainer = trained[best_name]
    log.info("Meilleur modèle (F1) : %s", best_name)

    y_hat = best_trainer.predict(X_test)
    err = error_analysis(X_test["url"], y_test, y_hat)
    err["false_positives"].to_csv(metrics_dir / "false_positives.csv", index=False)
    err["false_negatives"].to_csv(metrics_dir / "false_negatives.csv", index=False)

    # Test adversarial
    gen_urls = generate_phishing_urls(n=30, seed=seed + 1)
    adv = adversarial_evaluation(best_trainer.model, gen_urls)
    adv["best_model"] = best_name
    with open(metrics_dir / "adversarial_attack.json", "w", encoding="utf-8") as f:
        json.dump(adv, f, indent=2)
    log.info(
        "Test adversarial (URLs générées) — taux de succès attaque : %.2f%%",
        100.0 * adv["attack_success_rate"],
    )

    # Section « test réel » — 5 normales + 5 phishing inventées
    mixed = generate_mixed_test_urls(n_normal=5, n_phish=5, seed=seed + 2)
    mixed_df = pd.DataFrame(mixed, columns=["url", "true_label"])
    mixed_df["pred"] = best_trainer.predict(pd.DataFrame({"url": mixed_df["url"]}))
    mixed_df.to_csv(metrics_dir / "manual_url_tests.csv", index=False)

    save_metrics_json(
        {
            "best_model": best_name,
            "adversarial": adv,
            "manual_tests_preview": mixed_df.to_dict(orient="records"),
        },
        metrics_dir / "report_summary.json",
    )
    log.info("Pipeline terminé.")


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Pipeline phishing ML")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.yaml",
        help="Chemin vers config.yaml",
    )
    args = parser.parse_args(argv)

    cfg0 = load_config(args.config)
    setup_logging(cfg0.get("logging", {}).get("level", "INFO"))
    run_pipeline(args.config)


if __name__ == "__main__":
    main()
