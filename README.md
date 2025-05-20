# Urlebird Scraper

Un outil de scraping pour extraire des vidéos TikTok depuis urlebird.com en fonction des hashtags.

## Fonctionnalités

- Recherche de vidéos par hashtag
- Filtrage des résultats par dates
- Extraction complète des métadonnées (titre, auteur, date, statistiques, etc.)
- Gestion robuste des erreurs et mécanisme de retry
- Support du chargement AJAX avec le bouton "Load More"
- Sauvegarde CSV des résultats
- Sauvegarde incrémentale (option)
- Génération de statistiques (option)
- Support des proxies

## Prérequis

- Python 3.7+
- Bibliothèques: requests, beautifulsoup4, lxml, pandas, python-dateutil

## Installation

```bash
# Cloner le dépôt
git clone <url-du-repo>
cd social_scraping

# Installer les dépendances
pip install -r requirements.txt
```

## Utilisation

### Ligne de commande

```bash
python src/main.py --hashtag "parisfood" --max-pages 3 --output "data/parisfood_videos.csv"
```

### Options disponibles

- `--hashtag` : Hashtag à rechercher (obligatoire)
- `--start-date` : Date de début au format YYYY-MM-DD
- `--end-date` : Date de fin au format YYYY-MM-DD
- `--output` : Chemin du fichier CSV de sortie (défaut: data/results.csv)
- `--max-pages` : Nombre maximum de pages à scraper (défaut: 5)
- `--delay` : Délai entre les requêtes en secondes (défaut: 2.0)
- `--incremental-save` : Sauvegarder les résultats de manière incrémentale
- `--proxy` : Proxy HTTP à utiliser (format: http://user:pass@host:port)
- `--save-stats` : Générer un résumé statistique dans un fichier séparé

### Exemple de code

```python
from datetime import datetime
from src.urlebird_scraper import UrlebirdScraper

# Initialiser le scraper
scraper = UrlebirdScraper(delay_between_requests=1.5)

# Rechercher des vidéos
videos = scraper.search_videos(
    hashtag="parisfood",
    start_date=datetime(2023, 1, 1),
    end_date=datetime(2023, 12, 31),
    max_pages=3
)

# Sauvegarder les résultats
scraper.save_to_csv(videos, "data/parisfood_videos.csv")
```

## Structure du code

- `src/main.py` : Point d'entrée, interface en ligne de commande
- `src/urlebird_scraper.py` : Implémentation principale du scraper

## Notes importantes

1. Ce scraper est conçu pour le site urlebird.com qui est un agrégateur non officiel de TikTok. La structure du site peut changer.
2. Le scraper utilise la nouvelle structure d'URL (`/hash/[hashtag]/`) et gère le bouton "Load More" pour charger plus de contenu.
3. Des délais sont inclus entre les requêtes pour éviter d'être bloqué.
4. La rotation des user-agents aide à éviter la détection du scraping.

## To-Do / Améliorations possibles

- Améliorer la détection et l'analyse des éléments vidéo
- Développer des tests automatisés
- Ajouter une option pour exporter en JSON
- Implémenter un meilleur système de détection des dates
- Optimiser le chargement AJAX pour récupérer plus de vidéos
