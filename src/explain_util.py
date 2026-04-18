"""
Approximation d'explicabilité sur les features artisanales (sans SHAP / sans détail TF-IDF).
Les scores sont heuristiques et servent à l'UI — pas à l'audit formel du modèle.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.features import FeatureExtractor, get_handcrafted_feature_names


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _risk_subscores(row: Dict[str, float]) -> Dict[str, float]:
    """Sous-scores signés : positifs = augmente le risque structurel, négatifs = atténuateur."""
    L = row["url_length"]
    dots = row["num_dots"]
    at = row["has_at"]
    https = row["has_https"]
    digits = row["num_digits"]
    ip = row["has_ip"]
    subs = row["num_subdomains"]
    ent = row["entropy"]
    ldr = row["letter_digit_ratio"]
    kw = row["suspicious_keyword_hits"]

    parts: Dict[str, float] = {}

    parts["url_length"] = 10.0 * _clamp((L - 40.0) / 120.0)
    parts["num_dots"] = 10.0 * _clamp(dots / 12.0)
    parts["has_at"] = 12.0 if at >= 0.5 else 0.0
    parts["has_https"] = -7.0 if https >= 0.5 else 3.0
    parts["num_digits"] = 8.0 * _clamp(digits / 25.0)
    parts["has_ip"] = 18.0 if ip >= 0.5 else 0.0
    parts["num_subdomains"] = 8.0 * _clamp(subs / 5.0)
    parts["entropy"] = 8.0 * _clamp((ent - 3.2) / 2.5) if ent > 3.2 else 0.0
    parts["letter_digit_ratio"] = 4.0 * _clamp(abs(ldr - 2.0) / 4.0)
    parts["suspicious_keyword_hits"] = 14.0 * _clamp(kw / 4.0)

    return parts


_LABELS: Dict[str, Tuple[str, str]] = {
    "url_length": ("URL length", "Longer URLs are often used to hide malicious paths."),
    "num_dots": ("Number of dots", "Many subdomains/labels can indicate typosquatting."),
    "has_at": ("Contains '@'", "User-info style URLs are a common phishing trick."),
    "has_https": ("HTTPS", "HTTPS is common on legitimate sites; absence slightly increases structural risk."),
    "num_digits": ("Digits in URL", "High digit density can indicate encoded or random hosts."),
    "has_ip": ("Raw IP host", "Phishing often uses IPs instead of domain names."),
    "num_subdomains": ("Subdomains", "Long chains of subdomains are suspicious."),
    "entropy": ("Character entropy", "Very high entropy may indicate obfuscation."),
    "letter_digit_ratio": ("Letter / digit balance", "Unusual ratios can correlate with generated URLs."),
    "suspicious_keyword_hits": (
        "Suspicious keywords",
        "Words like login, verify, secure appear often in phishing pages.",
    ),
}


def explain_url(url: str, suspicious_keywords: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Retourne valeurs brutes, contributions approximatives (%) et un score structurel 0–100.
    """
    extractor = FeatureExtractor(suspicious_keywords=suspicious_keywords)
    vec = extractor.extract_row(url)
    names = get_handcrafted_feature_names()
    raw = {names[i]: float(vec[i]) for i in range(len(names))}

    subs = _risk_subscores(raw)
    positive_mass = sum(max(0.0, v) for v in subs.values()) + 1e-9
    signed_total = sum(subs.values())
    # Score 0–100 (heuristique)
    structural_risk = float(_clamp(55.0 + signed_total * 1.15, 0.0, 100.0))

    features_out: List[Dict[str, Any]] = []
    for name in names:
        s = subs[name]
        title, desc = _LABELS.get(name, (name, ""))
        if s >= 0:
            role = "risk"
            pct = 100.0 * s / positive_mass
        else:
            role = "mitigating"
            pct = 0.0

        features_out.append(
            {
                "id": name,
                "title": title,
                "description": desc,
                "value": raw[name],
                "signed_score": round(s, 2),
                "contribution_pct": round(pct, 1) if role == "risk" else None,
                "role": role,
            }
        )

    mitigating = [f for f in features_out if f["role"] == "mitigating"]
    risk_only = sorted(
        [f for f in features_out if f["role"] == "risk" and (f["contribution_pct"] or 0) > 0.1],
        key=lambda x: x["contribution_pct"] or 0,
        reverse=True,
    )

    return {
        "url": url,
        "structural_risk_score": round(structural_risk, 1),
        "features_ranked": risk_only[:8],
        "mitigating_factors": mitigating,
        "raw_features": raw,
    }
