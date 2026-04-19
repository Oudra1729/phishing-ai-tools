"""
API Flask : prédiction ML, post-traitement domaine, explication, UI React.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import pandas as pd
import yaml
from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.domain_rules import apply_domain_rules
from src.explain_util import explain_url
from src.generator import generate_phishing_urls
from src.model import ModelTrainer

FRONTEND_DIST = ROOT / "frontend" / "dist"
FRONTEND_ASSETS = FRONTEND_DIST / "assets"

app = Flask(
    __name__,
    template_folder=str(ROOT / "templates"),
    static_folder=str(ROOT / "static"),
    static_url_path="/static-legacy",
)
_cors = os.environ.get("CORS_ORIGINS")
_origins: str | list[str] = (
    [o.strip() for o in _cors.split(",") if o.strip()] if _cors else "*"
)
CORS(app, resources={r"/*": {"origins": _origins}})
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
    return _URL_IN_TEXT.findall(text or "")


def _predict_urls_with_rules(pipe, model_name: str, urls: list[str]) -> list[dict]:
    """Infère puis applique les règles domaine (liste blanche, typosquatting)."""
    if not urls:
        return []
    df = pd.DataFrame({"url": urls})
    pred = pipe.predict(df)
    try:
        proba_mat = pipe.predict_proba(df)
        probas = proba_mat[:, 1]
    except Exception:
        probas = None

    out: list[dict] = []
    for i, u in enumerate(urls):
        raw_l = int(pred[i])
        if probas is not None:
            raw_p = float(probas[i])
        else:
            raw_p = 1.0 if raw_l == 1 else 0.0
        rules = apply_domain_rules(u, raw_p, raw_l)
        log.info(
            "predict_raw: url=%r domain=%s raw_proba=%.4f raw_label=%s",
            u,
            rules["domain"],
            raw_p,
            raw_l,
        )
        log.info(
            "predict_adj: url=%r adjusted_proba=%.4f label=%s adjustment=%s",
            u,
            rules["proba"],
            rules["label"],
            rules["adjustment"],
        )
        proba_final = rules["proba"]
        item = {
            "url": u,
            "domain": rules["domain"],
            "label": rules["label"],
            "class": rules["class"],
            "proba": proba_final,
            "proba_raw": rules["proba_raw"],
            "proba_phishing": proba_final,
            "model": model_name,
            "adjustment": rules["adjustment"],
        }
        out.append(item)
    return out


def _public_class(label: int) -> str:
    return "safe" if label == 0 else "phishing"


def _legacy_class(label: int) -> str:
    return "benign" if label == 0 else "phishing"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/predict", methods=["POST"])
def predict():
    """
    JSON : { "url"?: "...", "email_text"?: "..." }
    Évalue séparément l'URL principale et les URLs extraites du texte.
    """
    data = request.get_json(force=True, silent=True) or {}
    main_url = (data.get("url") or "").strip()
    email_text = data.get("email_text")
    email_text_str = str(email_text).strip() if email_text else ""

    email_urls: list[str] = []
    if email_text_str:
        email_urls = extract_urls_from_email(email_text_str)

    if not main_url and not email_urls:
        return jsonify({"error": "Fournissez 'url' ou 'email_text' non vide."}), 400

    pipe, model_name = get_pipeline()

    main_rows: list[dict] = []
    if main_url:
        main_rows = _predict_urls_with_rules(pipe, model_name, [main_url])

    email_blocks: list[dict] = []
    if email_urls:
        email_blocks = _predict_urls_with_rules(pipe, model_name, email_urls)

    ordered = main_rows + email_blocks
    legacy_results: list[dict] = []
    for r in ordered:
        lr = dict(r)
        lr["class"] = _legacy_class(r["label"])
        legacy_results.append(lr)

    main_public = None
    if main_rows:
        m = main_rows[0]
        main_public = {**m, "class": _public_class(m["label"])}

    email_public = [{**e, "class": _public_class(e["label"])} for e in email_blocks]

    return jsonify(
        {
            "main_url": main_public,
            "email_urls": email_public,
            "results": legacy_results,
            "model": model_name,
        }
    )


@app.route("/explain", methods=["POST"])
def explain():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Fournissez une clé 'url' non vide."}), 400
    cfg = _load_config()
    kw = cfg.get("features", {}).get("suspicious_keywords")
    payload = explain_url(url, suspicious_keywords=kw)
    return jsonify(payload)


@app.route("/examples", methods=["GET"])
def examples():
    urls = generate_phishing_urls(n=10, seed=42)
    return jsonify({"urls": urls})


@app.route("/assets/<path:filename>")
def vite_assets(filename):
    if not FRONTEND_ASSETS.is_dir():
        return jsonify({"error": "Frontend build not found"}), 404
    target = FRONTEND_ASSETS / filename
    if not target.is_file() or not str(target.resolve()).startswith(str(FRONTEND_ASSETS.resolve())):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(str(FRONTEND_ASSETS), filename)


def _send_dist_root_file(name: str):
    """Fichiers copiés à la racine du build Vite (dossier public/)."""
    safe = {"logo.png", "favicon.png"}
    if name not in safe:
        abort(404)
    path = FRONTEND_DIST / name
    if not path.is_file() or not str(path.resolve()).startswith(str(FRONTEND_DIST.resolve())):
        abort(404)
    return send_from_directory(str(FRONTEND_DIST), name)


@app.route("/logo.png", methods=["GET"])
def serve_logo_png():
    return _send_dist_root_file("logo.png")


@app.route("/favicon.png", methods=["GET"])
def serve_favicon_png():
    return _send_dist_root_file("favicon.png")


@app.route("/", methods=["GET"])
def index():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return send_from_directory(str(FRONTEND_DIST), "index.html")
    log.warning(
        "React SPA missing (%s). Serving legacy Jinja UI — run: cd frontend && npm ci && npm run build "
        "(or deploy with Docker: build creates frontend/dist).",
        index_file,
    )
    return render_template("index.html")


def _preload_model_if_enabled() -> None:
    if os.environ.get("PRELOAD_MODEL", "1").lower() in ("0", "false", "no"):
        return
    try:
        get_pipeline()
    except Exception as exc:  # noqa: BLE001
        log.warning("Préchargement du modèle ignoré au démarrage : %s", exc)


_preload_model_if_enabled()


def main():
    logging.basicConfig(level=logging.INFO)
    cfg = _load_config()
    api_cfg = cfg.get("api", {})
    port = int(os.environ.get("PORT", api_cfg.get("port", 5000)))
    host = os.environ.get("HOST", api_cfg.get("host", "127.0.0.1"))
    if os.environ.get("PORT"):
        host = "0.0.0.0"
    debug = bool(api_cfg.get("debug", False)) and not os.environ.get("PORT")
    get_pipeline()
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
