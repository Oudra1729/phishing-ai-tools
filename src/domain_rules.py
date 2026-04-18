"""
Post-traitement par domaine (sans ré-entraînement) : liste de confiance, typosquatting léger.
Utilise le domaine enregistrable (eTLD+1) via tldextract.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Tuple

import tldextract

log = logging.getLogger("domain_rules")

_TLD_CACHE = Path(__file__).resolve().parent.parent / ".cache" / "tldextract"
_TLD_CACHE.mkdir(parents=True, exist_ok=True)
# Pas de réseau au démarrage : liste publique embarquée (snapshot).
_TLD_EXTRACT = tldextract.TLDExtract(cache_dir=str(_TLD_CACHE), suffix_list_urls=())

# Domaines enregistrables considérés comme légitimes (eTLD+1, minuscules)
TRUSTED_DOMAINS = frozenset(
    {
        "paypal.com",
        "google.com",
        "github.com",
        "microsoft.com",
        "apple.com",
    }
)

# Marques souvent usurpées : si le domaine n’est pas dans TRUSTED mais contient la marque → léger boost
BRAND_NAMES = (
    "paypal",
    "google",
    "github",
    "microsoft",
    "apple",
    "amazon",
    "netflix",
    "stripe",
    "chase",
    "wellsfargo",
    "coinbase",
)

# Seuil : sur domaine de confiance, ne pas marquer phishing si proba brute < ce seuil
TRUSTED_PHISHING_MIN_PROBA = 0.9

# Plafond de proba après downgrade sur domaine de confiance (évite faux positifs « login »)
TRUSTED_DOWNGRADE_CAP = 0.12

TYPO_BOOST_PER_HIT = 0.12
TYPO_BOOST_MAX = 0.28


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u
    if not u.startswith(("http://", "https://")):
        u = "http://" + u
    return u


def registered_domain(url: str) -> str:
    """Retourne le domaine enregistrable (ex. www.paypal.com/login → paypal.com)."""
    u = normalize_url(url)
    if not u:
        return ""
    ext = _TLD_EXTRACT(u)
    if not ext.domain:
        return ""
    if ext.suffix:
        return f"{ext.domain}.{ext.suffix}".lower()
    return ext.domain.lower()


def _typosquat_boost(reg_domain: str, proba_raw: float) -> Tuple[float, str]:
    """Augmente légèrement la proba si le domaine ressemble à une marque sans être le domaine officiel."""
    if reg_domain in TRUSTED_DOMAINS:
        return proba_raw, ""
    d = reg_domain.lower()
    hits = 0
    for brand in BRAND_NAMES:
        if brand in d:
            if d == f"{brand}.com" or d.endswith(f".{brand}.com"):
                continue
            hits += 1
    if hits == 0:
        return proba_raw, ""
    boost = min(TYPO_BOOST_MAX, hits * TYPO_BOOST_PER_HIT)
    return min(1.0, proba_raw + boost), "typosquat_brand_boost"


def apply_domain_rules(
    url: str,
    proba_phishing_raw: float,
    model_label: int,
) -> Dict[str, Any]:
    """
    Applique liste blanche + typosquatting. Retourne proba / label ajustés et métadonnées.
    """
    reg = registered_domain(url)
    raw = float(proba_phishing_raw)
    raw_label = int(model_label)

    log.debug(
        "domain_rules: url=%r registrable=%r raw_proba=%.4f raw_label=%s",
        url,
        reg,
        raw,
        raw_label,
    )

    adjustment = "none"
    proba = raw
    label = raw_label

    if reg in TRUSTED_DOMAINS:
        if raw < TRUSTED_PHISHING_MIN_PROBA:
            proba = min(raw * 0.2, TRUSTED_DOWNGRADE_CAP)
            label = 0
            adjustment = "trusted_downgrade"
            log.info(
                "trusted_downgrade: domain=%s raw_proba=%.4f -> adjusted_proba=%.4f",
                reg,
                raw,
                proba,
            )
        else:
            proba = raw
            label = 1 if raw >= 0.5 else 0
            adjustment = "trusted_high_confidence"
            log.info(
                "trusted_high_confidence: domain=%s raw_proba=%.4f label=%s",
                reg,
                raw,
                label,
            )
    else:
        proba, typo_note = _typosquat_boost(reg, raw)
        if typo_note:
            adjustment = typo_note
            label = 1 if proba >= 0.5 else 0
            log.info(
                "typosquat: domain=%s raw_proba=%.4f -> proba=%.4f (%s)",
                reg,
                raw,
                proba,
                typo_note,
            )
        else:
            label = 1 if proba >= 0.5 else 0

    cls = "phishing" if label == 1 else "safe"
    return {
        "domain": reg,
        "proba": float(proba),
        "proba_raw": float(raw),
        "label": int(label),
        "class": cls,
        "adjustment": adjustment,
    }
