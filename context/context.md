# Contexte du Projet de Scraping de Videos TikTok via urlebird.com

## Objectif
Développer un scraper Python robuste pour extraire des vidéos TikTok depuis le site urlebird.com en utilisant des hashtags spécifiques. L'objectif est de collecter des métadonnées sur les vidéos, telles que le titre, l'auteur, les dates, les vues, les likes, et les hashtags associés.

## Problématique Initiale
Le scraper existant (dans `src/urlebird_scraper.py`) présente plusieurs limitations:

1. **Gestion incorrecte des URLs** : Le code actuel utilise un système de paramètres URL (`params = {'q': hashtag, 'page': current_page}`) qui ne correspond pas à la structure réelle du site urlebird.com. En réalité, le site utilise des URLs de la forme `https://urlebird.com/hash/[hashtag]/`.

2. **Pagination inadaptée** : Le site n'utilise pas un système de pagination classique mais un bouton "Load More" qui charge davantage de contenu via des requêtes AJAX.

3. **Sélecteurs HTML potentiellement obsolètes** : Les sélecteurs actuels pourraient ne plus correspondre à la structure HTML actuelle du site.

4. **Extraction des données perfectible** : Le système d'extraction des données pourrait être amélioré pour récupérer plus d'informations ou le faire de manière plus robuste.

## Solution en Cours d'Implémentation

Nous travaillons sur une version améliorée qui:

1. **Corrige la structure des URLs** : Implémentation d'une construction d'URL correcte pour accéder aux pages de hashtags.

2. **Gère le chargement AJAX** : Implémentation d'un mécanisme pour extraire les données du bouton "Load More" et simuler des requêtes AJAX pour charger davantage de vidéos.

3. **Améliore la robustesse** : Utilisation de sélecteurs multiples, gestion des erreurs plus sophistiquée, et mécanismes de retry.

4. **Optimise l'extraction des données** : Amélioration des fonctions d'extraction pour récupérer plus de métadonnées et gérer les différents formats possibles.

## Prochaines Étapes

1. **Modifier la construction des URLs** pour utiliser le format correct (`https://urlebird.com/hash/[hashtag]/`)

2. **Implémenter l'extraction des paramètres du bouton "Load More"** pour pouvoir effectuer des requêtes AJAX subsequentes.

3. **Adapter le traitement des réponses JSON** pour extraire le HTML des nouvelles vidéos chargées via AJAX.

4. **Tester et affiner** le scraper pour s'assurer qu'il fonctionne correctement avec la structure actuelle du site.

## Notes Techniques

- Le site urlebird.com est un agrégateur de contenu TikTok, qui n'est pas l'API officielle de TikTok.
- La structure du site peut changer, donc le scraper doit être suffisamment robuste pour s'adapter ou échouer gracieusement.
- Nous incluons des délais entre les requêtes et une rotation des user-agents pour éviter d'être bloqué.
- Le scraper inclut des fonctionnalités pour le filtrage par date, le traitement concurrent, et la sauvegarde incrémentale.

## État actuel du code

- Le script principal (`main.py`) fournit une interface en ligne de commande pour le scraper.
- La classe `UrlebirdScraper` (dans `urlebird_scraper.py`) contient toute la logique de scraping.
- Nous sommes actuellement en train de modifier la méthode `search_videos` pour corriger la gestion des URLs et implémenter le support du chargement AJAX.
