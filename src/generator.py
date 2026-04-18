"""
Génération d'URLs de phishing synthétiques pour tests adversariaux et robustesse.
Stratégies : domaines réalistes, typosquatting, sous-domaines trompeurs, mots-clés sociaux.
"""
from __future__ import annotations

import random
import string
from typing import List, Optional


_BRANDS = [
    "paypal",
    "amazon",
    "microsoft",
    "apple",
    "netflix",
    "stripe",
    "chase",
    "wellsfargo",
    "coinbase",
    "binance",
]

_TLDS = ["com", "net", "xyz", "top", "icu", "click", "online", "site", "info"]

_SECURE_WORDS = ["secure", "login", "verify", "account", "auth", "update", "confirm"]


def _token(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def typo_squat(brand: str) -> str:
    """Remplace un caractère par un homoglyphe courant."""
    if len(brand) < 4:
        return brand + random.choice("10o")
    i = random.randint(1, len(brand) - 2)
    repl = random.choice(["1", "0", "l", "rn"])
    return brand[:i] + repl + brand[i + 1 :]


def random_subdomains() -> str:
    subs = random.sample(
        ["www", "secure", "login", "m", "account", "verify", "mobile"],
        k=random.randint(2, 4),
    )
    return ".".join(subs)


def generate_phishing_urls(
    n: int = 25,
    seed: Optional[int] = None,
) -> List[str]:
    """
    Génère au moins ``n`` URLs de phishing variées (HTTP/HTTPS, IP, @, typos, etc.).
    """
    if seed is not None:
        random.seed(seed)
    urls: List[str] = []

    while len(urls) < n:
        brand = random.choice(_BRANDS)
        tld = random.choice(_TLDS)
        r = random.random()

        if r < 0.2:
            # Typosquat + mots suspects dans le domaine
            dom = f"{typo_squat(brand)}-{_token(4)}-secure.{tld}"
            path = f"/login/verify?next={_token(8)}"
            scheme = random.choice(["http://", "https://"])
            urls.append(f"{scheme}{dom}{path}")

        elif r < 0.4:
            # Sous-domaines multiples
            sub = random_subdomains()
            dom = f"{sub}.{typo_squat(brand)}.{tld}"
            urls.append(f"http://{dom}/signin/secure")

        elif r < 0.55:
            # @ dans l'URL
            dom = f"{brand}-verify.{tld}"
            user = random.choice(["noreply", "secure", "service"])
            urls.append(f"http://{user}@{dom}/account/update")

        elif r < 0.7:
            # IP + chemin suspect
            ip = f"{random.randint(10, 220)}.{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(2, 250)}"
            urls.append(f"http://{ip}/paypal/login.html")

        else:
            frag = "-".join(random.sample(_SECURE_WORDS, k=2))
            dom = f"{frag}-{_token(5)}.{tld}"
            urls.append(f"https://{dom}/{random.choice(_SECURE_WORDS)}?s={_token(10)}")

    return urls[:n]


def generate_mixed_test_urls(
    n_normal: int = 5,
    n_phish: int = 5,
    seed: Optional[int] = None,
) -> List[tuple]:
    """Retourne une liste de (url, label attendu) pour tests manuels."""
    if seed is not None:
        random.seed(seed)
    normal = [
        ("https://www.wikipedia.org/wiki/Main_Page", 0),
        ("https://github.com/scikit-learn/scikit-learn", 0),
        ("https://docs.python.org/3/", 0),
        ("https://stackoverflow.com/questions/tagged/python", 0),
        ("https://www.mozilla.org/en-US/firefox/new/", 0),
    ]
    phish = [(u, 1) for u in generate_phishing_urls(n=n_phish, seed=seed)]
    out = list(normal[:n_normal]) + phish
    random.shuffle(out)
    return out
