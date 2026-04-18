# AI-Powered Phishing Detection & Generation System

Projet de **détection d’URLs de phishing** par apprentissage automatique, avec **génération synthétique** d’URLs malveillantes pour évaluer la **robustesse** des modèles. Le code est découpé en modules (features, modèles, évaluation, pipeline) et configurable via `config.yaml`.

> **Contexte pédagogique / cybersécurité** : ce travail illustre à la fois une usage **défensif** (classification binaire légitime / phishing) et un usage **offensif simulé** (génération d’exemples pour tests d’évasion), afin de comprendre les limites des détecteurs statistiques face à des attaques générées ou retouchées automatiquement.

---

## Architecture

| Élément | Rôle |
|--------|------|
| `data/phishing.csv` | Jeu d’URLs étiquetées (`url`, `label` : 0 bénin, 1 phishing) |
| `scripts/generate_sample_data.py` | Génère un CSV reproductible si vous n’avez pas de jeu externe |
| `src/features.py` | `FeatureExtractor` + transformateur sklearn (longueur, points, HTTPS, entropie, mots suspects, etc.) |
| `src/model.py` | Pipelines : **Régression logistique**, **Forêt aléatoire**, **HistGradientBoosting**, **XGBoost** (optionnel) + **TF-IDF caractères** |
| `src/evaluate.py` | Métriques, ROC, matrices de confusion, importances RF, analyses d’erreurs |
| `src/generator.py` | Génération d’URLs adversariales (typosquatting, sous-domaines, IP, etc.) |
| `src/pipeline.py` | Orchestration complète (entraînement, figures, métriques, test adversarial) |
| `src/api.py` | API Flask minimale (`/predict`) pour scorer une URL ou du texte contenant des URLs |
| `notebooks/exploration.ipynb` | EDA, features, comparaison, analyse qualitative |
| `config.yaml` | Hyperparamètres, chemins, logging, options TF-IDF |
| `outputs/` | `models/`, `metrics/`, `plots/` produits par le pipeline |

---

## Installation

```bash
cd /path/to/LP
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**XGBoost (optionnel)** : sur macOS, installez OpenMP (`brew install libomp`) puis `pip install -r requirements-optional.txt`. Sinon le pipeline utilise LR, RF et HistGradientBoosting uniquement.

### Données

Par défaut, générez un jeu synthétique **réaliste** (recommandé pour exécuter le projet sans téléchargement) :

```bash
python scripts/generate_sample_data.py --n 4000
```

Vous pouvez remplacer `data/phishing.csv` par votre propre fichier en conservant les colonnes `url` et `label`.

---

## Exécution du pipeline

Depuis la racine du projet :

```bash
python src/pipeline.py
```

Sorties principales :

- Modèles : `outputs/models/*.joblib`
- Métriques : `outputs/metrics/model_comparison.csv`, `metrics_summary.json`, `adversarial_attack.json`, `false_positives.csv`, `false_negatives.csv`
- Graphiques : `outputs/plots/` (ROC, confusion, corrélations, distributions, importances RF)

---

## API (bonus)

Après avoir entraîné les modèles :

```bash
python -m src.api
```

Exemple :

```bash
curl -s -X POST http://127.0.0.1:5000/predict \
  -H "Content-Type: application/json" \
  -d '{"url":"http://secure-paypa1-login.com"}'
```

---

## Résultats attendus (indicatif)

Sur le jeu **synthétique** fourni, les modèles atteignent en général des scores élevés (souvent **> 0.95** en F1 selon la graine et la taille). Les écarts entre modèles et le **taux de succès adversarial** (URLs générées classées à tort comme bénignes) sont enregistrés dans `outputs/metrics/`. En pratique, sur données réelles bruitées, les performances sont plus basses : d’où l’intérêt de l’EDA et de la validation continue.

---

## Analyse (résumé)

- **Faux positifs** : URLs légitimes longues, avec chemins `login` / `verify` (faux amis).
- **Faux négatifs** : phishing « minimal » qui imite des patterns légitimes (HTTPS, domaine propre, peu de mots-clés).
- **Robustesse** : la génération automatique (`generator.py`) permet de mesurer une **taux d’évasion** ; l’amélioration passe par plus de données réelles, des listes de domaines de confiance, du contexte réseau (DNS, TLS), et des modèles de séquence (transformers) sur le texte complet.

---

## Pistes d’amélioration

- Données : PhishTank / OpenPhish / jeux académiques, avec validation temporelle.
- Features : âge du domaine, certificats, redirections, contenu HTML téléchargé.
- Modèles : réseaux sur tokens de caractères, calibration des probabilités, apprentissage adversarial défensif.
- Déploiement : conteneurisation, monitoring de dérive, explicabilité (SHAP).

---

## Auteurs / contexte

Projet type **Cybersécurité & Big Data** — détection et génération de phishing par IA, avec rapport intégré (notebook + métriques exportées).

## Licence

Usage éducatif et de recherche. Ne pas utiliser la génération d’URLs à des fins malveillantes.
