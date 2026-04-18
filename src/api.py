"""
API HTTP minimale (Flask) pour scorer une URL ou un extrait d'email.

Lancer depuis la racine du projet :
    python -m src.api

Charge le dernier modèle sauvegardé (gradient_boosting ou random_forest selon disponibilité).
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
import yaml
from flask import Flask, jsonify, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.model import ModelTrainer

app = Flask(__name__)
log = logging.getLogger("api")

_PIPELINE = None
_MODEL_NAME = None


def _load_config():
    with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _pick_model_path(cfg) -> tuple:
    models_dir = ROOT / cfg["paths"]["models_dir"]
    preference = [
        "random_forest.joblib",
        "xgboost.joblib",
        "gradient_boosting.joblib",
        "logistic_regression.joblib",
    ]
    for name in preference:
        p = models_dir / name
        if p.is_file():
            return p, name.replace(".joblib", "")
    raise FileNotFoundError(
        f"Aucun modèle trouvé dans {models_dir}. Exécutez d'abord python src/pipeline.py"
    )


def get_pipeline():
    global _PIPELINE, _MODEL_NAME
    if _PIPELINE is None:
        cfg = _load_config()
        path, _MODEL_NAME = _pick_model_path(cfg)
        _PIPELINE = ModelTrainer.load_model(path)
        log.info("Modèle chargé : %s (%s)", _MODEL_NAME, path)
    return _PIPELINE, _MODEL_NAME


_URL_IN_TEXT = re.compile(
    r"https?://[^\s<>\"]+|www\.[^\s<>\"]+", re.IGNORECASE
)


def extract_urls_from_email(text: str) -> list:
    """Extrait des URLs grossières depuis le corps d'un email."""
    return _URL_IN_TEXT.findall(text or "")


@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Phishing Detection API is running"})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    """
    JSON : {"url": "https://..."} OU {"email_text": "..."} pour URLs détectées dans le texte.
    """
    data = request.get_json(force=True, silent=True) or {}
    urls = []
    if "url" in data and data["url"]:
        urls.append(str(data["url"]))
    if "email_text" in data and data["email_text"]:
        urls.extend(extract_urls_from_email(str(data["email_text"])))

    if not urls:
        return jsonify({"error": "Fournissez 'url' ou 'email_text' non vide."}), 400

    pipe, model_name = get_pipeline()
    df = pd.DataFrame({"url": urls})
    pred = pipe.predict(df)
    out = []
    try:
        proba = pipe.predict_proba(df)
    except Exception:
        proba = None
    for i, u in enumerate(urls):
        row = {
            "url": u,
            "label": int(pred[i]),
            "class": "phishing" if int(pred[i]) == 1 else "benign",
            "model": model_name,
        }
        if proba is not None:
            row["proba_phishing"] = float(proba[i, 1])
        out.append(row)
    return jsonify({"results": out})


def _preload_model_if_enabled() -> None:
    """Charge le modèle au démarrage (utile avec gunicorn : pas seulement en `python -m`)."""
    if os.environ.get("PRELOAD_MODEL", "1").lower() in ("0", "false", "no"):
        return
    try:
        get_pipeline()
    except Exception as exc:  # noqa: BLE001 — on logue et on retente au premier /predict
        log.warning("Préchargement du modèle ignoré au démarrage : %s", exc)


_preload_model_if_enabled()


def main():
    logging.basicConfig(level=logging.INFO)
    cfg = _load_config()
    api_cfg = cfg.get("api", {})
    # Hébergeurs (Render, Railway, Fly…) définissent PORT ; il faut écouter sur 0.0.0.0
    port = int(os.environ.get("PORT", api_cfg.get("port", 5000)))
    host = os.environ.get("HOST", api_cfg.get("host", "127.0.0.1"))
    if os.environ.get("PORT"):
        host = "0.0.0.0"
    debug = bool(api_cfg.get("debug", False)) and not os.environ.get("PORT")
    get_pipeline()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
