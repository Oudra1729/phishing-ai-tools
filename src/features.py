"""
Extraction de caractéristiques structurelles et lexicales à partir d'URLs.
Compatible scikit-learn (BaseEstimator / TransformerMixin).
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Optional, Union
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

# IPv4 dans le host ou le chemin
_IPV4_RE = re.compile(
    r"(?<![0-9])(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?![0-9])"
)


def _shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    n = len(text)
    ent = 0.0
    for c in counts.values():
        p = c / n
        ent -= p * math.log2(p)
    return ent


def _count_subdomains(hostname: str) -> int:
    """Approximation : nombre de labels avant le domaine registré (eTLD+1 simplifié)."""
    if not hostname:
        return 0
    host = hostname.lower().strip(".")
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return max(0, len(parts) - 1)
    # www.example.com -> 1 sous-domaine (www)
    return max(0, len(parts) - 2)


class FeatureExtractor:
    """
    Extraction manuelle de features à partir d'une liste / Series d'URLs.

    Features obligatoires :
        - longueur URL
        - nombre de points
        - présence de '@'
        - présence HTTPS
        - nombre de chiffres
        - présence d'une adresse IP
        - nombre de sous-domaines

    Bonus :
        - entropie de la chaîne URL
        - ratio lettres / chiffres
        - nombre de mots suspects (liste configurable)
    """

    FEATURE_NAMES: List[str] = [
        "url_length",
        "num_dots",
        "has_at",
        "has_https",
        "num_digits",
        "has_ip",
        "num_subdomains",
        "entropy",
        "letter_digit_ratio",
        "suspicious_keyword_hits",
    ]

    def __init__(
        self,
        suspicious_keywords: Optional[Iterable[str]] = None,
    ) -> None:
        self.suspicious_keywords = tuple(
            suspicious_keywords
            or (
                "login",
                "verify",
                "secure",
                "account",
                "update",
                "confirm",
                "signin",
                "banking",
                "paypal",
                "password",
            )
        )

    def extract_row(self, url: str) -> List[float]:
        if not isinstance(url, str):
            url = str(url)
        u = url.strip()
        parsed = urlparse(u if "://" in u else "http://" + u)
        host = (parsed.netloc or parsed.path.split("/")[0] or "").lower()
        path_query = f"{parsed.path or ''}{parsed.query or ''}"

        url_length = float(len(u))
        num_dots = float(u.count("."))
        has_at = 1.0 if "@" in u else 0.0
        has_https = 1.0 if u.lower().startswith("https://") else 0.0

        digit_count = sum(1 for c in u if c.isdigit())
        num_digits = float(digit_count)

        has_ip = 1.0 if _IPV4_RE.search(u) else 0.0

        num_subdomains = float(_count_subdomains(host))

        ent = _shannon_entropy(u)
        letters = sum(1 for c in u if c.isalpha())
        letter_digit_ratio = float(letters / (digit_count + 1e-6))

        lower_u = u.lower()
        kw_hits = sum(1 for kw in self.suspicious_keywords if kw in lower_u)
        suspicious_keyword_hits = float(kw_hits)

        return [
            url_length,
            num_dots,
            has_at,
            has_https,
            num_digits,
            has_ip,
            num_subdomains,
            ent,
            letter_digit_ratio,
            suspicious_keyword_hits,
        ]

    def transform(self, urls: Union[pd.Series, np.ndarray, List[str]]) -> np.ndarray:
        if isinstance(urls, pd.Series):
            iterable = urls.astype(str).tolist()
        else:
            iterable = [str(x) for x in urls]
        return np.array([self.extract_row(u) for u in iterable], dtype=np.float64)

    def fit(self, X, y=None) -> "FeatureExtractor":
        """API sklearn — pas d'apprentissage pour ces features."""
        return self


class UrlHandcraftedTransformer(BaseEstimator, TransformerMixin):
    """
    Transformateur sklearn : DataFrame avec colonne ``url`` -> matrice dense de features.
    """

    def __init__(self, suspicious_keywords: Optional[Iterable[str]] = None) -> None:
        self.suspicious_keywords = suspicious_keywords

    def fit(self, X, y=None):
        self.extractor_ = FeatureExtractor(
            suspicious_keywords=self.suspicious_keywords
        )
        return self

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            if "url" not in X.columns:
                raise ValueError("Le DataFrame doit contenir une colonne 'url'.")
            urls = X["url"]
        else:
            urls = pd.Series(np.asarray(X).ravel())
        return self.extractor_.transform(urls)

    def get_feature_names_out(self, input_features=None):
        return np.asarray(FeatureExtractor.FEATURE_NAMES, dtype=object)


def get_handcrafted_feature_names() -> List[str]:
    return list(FeatureExtractor.FEATURE_NAMES)
