"""
Entraînement, prédiction et persistance de modèles (LR, RF, GB, XGBoost).
Pipelines sklearn avec features artisanales + TF-IDF optionnel (caractères).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy import sparse as sp
from sklearn.base import clone
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, MaxAbsScaler, StandardScaler

from src.features import UrlHandcraftedTransformer

try:
    from xgboost import XGBClassifier  # noqa: F401

    _HAS_XGB = True
except Exception:
    # Import ou chargement de lib native (ex. libomp sur macOS) peut échouer
    XGBClassifier = None  # type: ignore
    _HAS_XGB = False


def _sparse_to_dense(X):
    """HistGradientBoosting exige une matrice dense ; TF-IDF est creux."""
    if sp.issparse(X):
        return X.toarray()
    return np.asarray(X)


def _build_preprocessors(config: Dict[str, Any]) -> Tuple[ColumnTransformer, ColumnTransformer]:
    """
    Retourne deux préprocesseurs :
    - ``scaled`` : handcrafted + StandardScaler (pour LR sur bloc dense + sparse TF-IDF via MaxAbsScaler global option — simplifié ci-dessous)
    """
    feat_cfg = config.get("features", {})
    suspicious = feat_cfg.get("suspicious_keywords")
    tfidf_cfg = feat_cfg.get("tfidf", {})
    use_tfidf = tfidf_cfg.get("enabled", True)

    hand_u = UrlHandcraftedTransformer(suspicious_keywords=suspicious)
    hand_s = clone(hand_u)

    if use_tfidf:
        vec_u = TfidfVectorizer(
            analyzer=tfidf_cfg.get("analyzer", "char_wb"),
            ngram_range=(
                int(tfidf_cfg.get("ngram_min", 3)),
                int(tfidf_cfg.get("ngram_max", 5)),
            ),
            max_features=int(tfidf_cfg.get("max_features", 2000)),
            min_df=2,
            sublinear_tf=True,
        )
        vec_s = clone(vec_u)
        unscaled = ColumnTransformer(
            transformers=[
                ("handcrafted", hand_u, "url"),
                ("tfidf", vec_u, "url"),
            ],
            remainder="drop",
            sparse_threshold=0.3,
        )
        scaled = ColumnTransformer(
            transformers=[
                (
                    "handcrafted",
                    Pipeline(
                        [
                            ("fe", hand_s),
                            ("scale", StandardScaler()),
                        ]
                    ),
                    "url",
                ),
                ("tfidf", vec_s, "url"),
            ],
            remainder="drop",
            sparse_threshold=0.3,
        )
    else:
        unscaled = ColumnTransformer(
            transformers=[("handcrafted", hand_u, "url")],
            remainder="drop",
        )
        scaled = ColumnTransformer(
            transformers=[
                (
                    "handcrafted",
                    Pipeline([("fe", hand_s), ("scale", StandardScaler())]),
                    "url",
                )
            ],
            remainder="drop",
        )

    return unscaled, scaled


def build_model_pipelines(config: Dict[str, Any]) -> Dict[str, Pipeline]:
    """Construit un dictionnaire nom -> Pipeline sklearn entièrement configuré."""
    _, scaled_prep = _build_preprocessors(config)
    unscaled_prep, _ = _build_preprocessors(config)

    models_cfg = config.get("models", {})
    seed = int(config.get("project", {}).get("random_seed", 42))

    out: Dict[str, Pipeline] = {}

    # Logistic Regression — scaling sur handcrafted + MaxAbs sur stack sparse/dense
    lr_cfg = models_cfg.get("logistic_regression", {})
    lr = LogisticRegression(
        max_iter=int(lr_cfg.get("max_iter", 2000)),
        class_weight=lr_cfg.get("class_weight", "balanced"),
        solver="saga",
        random_state=seed,
    )
    out["logistic_regression"] = Pipeline(
        [
            ("prep", scaled_prep),
            (
                "clf_block",
                Pipeline(
                    [
                        ("scale_all", MaxAbsScaler()),
                        ("clf", lr),
                    ]
                ),
            ),
        ]
    )

    rf_cfg = models_cfg.get("random_forest", {})
    out["random_forest"] = Pipeline(
        [
            ("prep", unscaled_prep),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=int(rf_cfg.get("n_estimators", 200)),
                    max_depth=rf_cfg.get("max_depth"),
                    class_weight=rf_cfg.get("class_weight", "balanced"),
                    random_state=int(rf_cfg.get("random_state", seed)),
                    n_jobs=int(rf_cfg.get("n_jobs", 1)),
                ),
            ),
        ]
    )

    gb_cfg = models_cfg.get("gradient_boosting", {})
    out["gradient_boosting"] = Pipeline(
        [
            ("prep", unscaled_prep),
            (
                "dense",
                FunctionTransformer(_sparse_to_dense, accept_sparse=True),
            ),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_iter=int(gb_cfg.get("n_estimators", 150)),
                    max_depth=int(gb_cfg.get("max_depth", 5)),
                    learning_rate=float(gb_cfg.get("learning_rate", 0.1)),
                    random_state=int(gb_cfg.get("random_state", seed)),
                    class_weight="balanced",
                ),
            ),
        ]
    )

    if _HAS_XGB:
        xgb_cfg = models_cfg.get("xgboost", {})
        out["xgboost"] = Pipeline(
            [
                ("prep", unscaled_prep),
                (
                    "clf",
                    XGBClassifier(
                        n_estimators=int(xgb_cfg.get("n_estimators", 200)),
                        max_depth=int(xgb_cfg.get("max_depth", 6)),
                        learning_rate=float(xgb_cfg.get("learning_rate", 0.1)),
                        subsample=float(xgb_cfg.get("subsample", 0.9)),
                        colsample_bytree=float(xgb_cfg.get("colsample_bytree", 0.9)),
                        eval_metric=xgb_cfg.get("eval_metric", "logloss"),
                        random_state=int(xgb_cfg.get("random_state", seed)),
                        n_jobs=int(xgb_cfg.get("n_jobs", 1)),
                    ),
                ),
            ],
        )

    return out


class ModelTrainer:
    """Entraîne, prédit, sauvegarde et charge des pipelines sklearn."""

    def __init__(self, model: Pipeline, name: str = "model"):
        self.model = model
        self.name = name

    def train(self, X: pd.DataFrame, y: np.ndarray) -> "ModelTrainer":
        self.model.fit(X, y)
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return self.model.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        if hasattr(self.model, "predict_proba"):
            return self.model.predict_proba(X)
        raise AttributeError("Le modèle n'expose pas predict_proba.")

    def save_model(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)
        meta = {"name": self.name, "sklearn_pipeline": True}
        with open(path.with_suffix(path.suffix + ".meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    @staticmethod
    def load_model(path: Path) -> Pipeline:
        return joblib.load(path)
