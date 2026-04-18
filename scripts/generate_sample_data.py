#!/usr/bin/env python3
"""
Génère un fichier data/phishing.csv avec des URLs synthétiques mais réalistes
pour rendre le projet exécutable sans dépendre d'un téléchargement externe.
Colonnes: url, label (0=légitime, 1=phishing).
"""
from __future__ import annotations

import argparse
import random
import string
from pathlib import Path

# Domaines et chemins plausibles (légitimes)
BENIGN_DOMAINS = [
    "wikipedia.org",
    "github.com",
    "stackoverflow.com",
    "python.org",
    "mozilla.org",
    "gnu.org",
    "kernel.org",
    "apache.org",
    "nginx.org",
    "debian.org",
    "archlinux.org",
    "rust-lang.org",
    "nodejs.org",
    "npmjs.com",
    "pypi.org",
    "readthedocs.io",
    "medium.com",
    "bbc.co.uk",
    "reuters.com",
    "nature.com",
    "arxiv.org",
    "springer.com",
    "ieee.org",
    "mit.edu",
    "stanford.edu",
    "google.com",
    "microsoft.com",
    "apple.com",
    "amazon.com",
    "cloudflare.com",
]

BENIGN_PATHS = [
    "",
    "/docs",
    "/blog/post",
    "/wiki/Main_Page",
    "/download",
    "/releases/tag/v1.0",
    "/issues/42",
    "/pull/100",
    "/search?q=test",
    "/user/login",  # légitime sur vrai site
    "/about",
    "/contact",
]

# Patterns typiques phishing (synthétiques)
PHISH_BRANDS = [
    "paypal",
    "amazon",
    "microsoft",
    "apple",
    "netflix",
    "bankofamerica",
    "chase",
    "wellsfargo",
    "google",
    "facebook",
]

PHISH_TLDS = ["com", "net", "xyz", "top", "icu", "click", "online", "site"]

SUSPICIOUS_FRAGMENTS = [
    "secure-login",
    "verify-account",
    "update-payment",
    "confirm-identity",
    "signin-secure",
    "auth-verify",
    "banking-secure",
    "paypal-login",
]


def random_subdomain() -> str:
    parts = [
        "www",
        "m",
        "secure",
        "login",
        "account",
        "verify",
        "update",
        "auth",
        "signin",
        "mobile",
    ]
    n = random.randint(1, 3)
    return ".".join(random.sample(parts, min(n, len(parts))))


def typo_brand(brand: str) -> str:
    """Typosquatting simple."""
    if len(brand) < 4:
        return brand + random.choice("10o")
    i = random.randint(1, len(brand) - 2)
    c = brand[i]
    rep = random.choice(["1", "0", "l", "rn"])
    return brand[:i] + rep + brand[i + 1 :]


def fake_ip_path() -> str:
    return f"http://{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}/login"


def generate_benign_url() -> str:
    scheme = random.choice(["https://", "https://", "http://"])
    domain = random.choice(BENIGN_DOMAINS)
    path = random.choice(BENIGN_PATHS)
    if random.random() < 0.3 and "?" not in path:
        path += f"?ref={random.randint(1, 999)}"
    return f"{scheme}{domain}{path}"


def generate_phishing_url() -> str:
    r = random.random()
    brand = random.choice(PHISH_BRANDS)
    tld = random.choice(PHISH_TLDS)

    if r < 0.25:
        # Typosquat + mots suspects
        dom = f"{typo_brand(brand)}-{random.choice(['secure', 'login', 'verify'])}.{tld}"
        path = f"/{random.choice(SUSPICIOUS_FRAGMENTS)}"
    elif r < 0.45:
        # Sous-domaines nombreux
        sub = random_subdomain()
        dom = f"{sub}.{typo_brand(brand)}.{tld}"
        path = random.choice(["/signin", "/verify", "/account/update"])
    elif r < 0.65:
        # @ dans l'URL (user@host)
        dom = f"{brand}-verify.{tld}"
        user = random.choice(["user", "secure", "noreply"])
        return f"http://{user}@{dom}/login.html"
    elif r < 0.8:
        # IP
        return fake_ip_path()
    else:
        dom = f"{random.choice(SUSPICIOUS_FRAGMENTS).replace('-', '')}.{brand[:4]}{random.randint(10, 99)}.{tld}"
        path = f"/{random.choice(['login', 'verify', 'secure'])}?session={random_token(8)}"

    scheme = random.choice(["http://", "http://", "https://"])
    return f"{scheme}{dom}{path}"


def random_token(n: int) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=4000, help="Nombre total d'exemples")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "phishing.csv",
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    n_phish = args.n // 2
    n_benign = args.n - n_phish

    rows = []
    for _ in range(n_benign):
        rows.append((generate_benign_url(), 0))
    for _ in range(n_phish):
        rows.append((generate_phishing_url(), 1))

    random.shuffle(rows)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("url,label\n")
        for url, lab in rows:
            escaped = url.replace('"', '""')
            f.write(f'"{escaped}",{lab}\n')

    print(f"Écrit {len(rows)} lignes dans {args.out}")


if __name__ == "__main__":
    main()
