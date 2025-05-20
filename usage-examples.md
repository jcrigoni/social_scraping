# Exemples d'utilisation du scraper urlebird amélioré

## Usage basique

```bash
# Activer l'environnement virtuel
pipenv shell

# Recherche simple avec un hashtag
python src/main.py --hashtag dance

# Recherche avec une plage de dates
python src/main.py --hashtag dance --start-date 2023-01-01 --end-date 2023-06-30

# Spécifier le fichier de sortie
python src/main.py --hashtag dance --output data/dance_videos.csv
```

## Fonctionnalités avancées

```bash
# Utiliser le mode concurrent pour des performances améliorées
python src/main.py --hashtag dance --concurrent --max-workers 4

# Augmenter le nombre de pages à scraper
python src/main.py --hashtag dance --max-pages 20

# Ajuster le délai entre les requêtes pour éviter d'être bloqué
python src/main.py --hashtag dance --delay 3.5

# Activer la sauvegarde incrémentale pour éviter de perdre des données
python src/main.py --hashtag dance --max-pages 30 --incremental-save

# Générer des statistiques sur les vidéos trouvées
python src/main.py --hashtag dance --save-stats

# Utiliser un proxy pour éviter d'être bloqué
python src/main.py --hashtag dance --proxy http://user:pass@proxy.example.com:8080
```

## Exemples d'analyse de tendances

```bash
# Comparer deux hashtags populaires (exécuter séparément)
python src/main.py --hashtag dance --output data/dance_videos.csv --save-stats
python src/main.py --hashtag fitness --output data/fitness_videos.csv --save-stats

# Scraper plusieurs hashtags liés au même sujet
for HASHTAG in dance choreography ballet hiphop; do
    python src/main.py --hashtag $HASHTAG --output data/${HASHTAG}_videos.csv --save-stats
done

# Collecter des données sur une longue période en divisant par tranches de temps
python src/main.py --hashtag viral --start-date 2023-01-01 --end-date 2023-03-31 --output data/viral_Q1.csv
python src/main.py --hashtag viral --start-date 2023-04-01 --end-date 2023-06-30 --output data/viral_Q2.csv
```

## Analyse des données après le scraping

Une fois que vous avez collecté les données, vous pouvez les analyser avec pandas :

```python
import pandas as pd
import matplotlib.pyplot as plt

# Charger les données
df = pd.read_csv('data/dance_videos.csv')

# Convertir la date en datetime
df['date'] = pd.to_datetime(df['date'])

# Analyser les vues par date
views_by_date = df.groupby(df['date'].dt.date)['views'].mean().reset_index()

# Visualiser les tendances
plt.figure(figsize=(12, 6))
plt.plot(views_by_date['date'], views_by_date['views'])
plt.title('Moyenne des vues par jour pour les vidéos avec #dance')
plt.xlabel('Date')
plt.ylabel('Vues moyennes')
plt.grid(True)
plt.tight_layout()
plt.savefig('data/dance_views_trend.png')

# Trouver les auteurs les plus populaires
top_authors = df.groupby('author').agg({
    'views': 'sum',
    'likes': 'sum',
    'url': 'count'  # Compter le nombre de vidéos
}).rename(columns={'url': 'video_count'}).sort_values('views', ascending=False).head(10)

print("Top 10 des auteurs par nombre total de vues :")
print(top_authors)
```
