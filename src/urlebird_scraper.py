import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import time
import re
import random
import json
import urllib.robotparser
from typing import List, Dict, Optional, Tuple, Union
from dateutil import parser as date_parser
import os
import concurrent.futures
from logger import setup_logger

# Configuration du logging
logger = setup_logger('urlebird_scraper')

class UrlebirdScraper:
    """
    Scraper pour urlebird.com pour collecter des métadonnées et liens de vidéos TikTok.
    Note importante: urlebird.com n'héberge PAS de vidéos, c'est un agrégateur qui fournit
    des liens vers les vidéos originales sur TikTok et des métadonnées associées.
    
    Version améliorée avec gestion des erreurs robuste, multi-sélecteurs, et support du chargement AJAX.
    
    Cette version tient compte de la structure réelle du site urlebird.com:
    - Utilisation des URLs au format /hash/[hashtag]/ plutôt que des paramètres
    - Gestion du bouton "Load More" pour charger plus d'informations via AJAX
    - Extraction des paramètres nécessaires pour les requêtes AJAX
    """
    
    BASE_URL = "https://urlebird.com"
    SEARCH_URL = f"{BASE_URL}/hash/"
    
    # Liste de User-Agents pour la rotation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'
    ]
    
    # Sélecteurs CSS multiples pour différents éléments
    SELECTORS = {
        'video_card': [
            # Sélecteurs originaux
            'div.video-card',
            '.video-item',
            '.tiktok-video-item',
            '.video-container',
            # Nouveaux sélecteurs à essayer
            '.video-feed-item',
            '.feed-item',
            '.tiktok-feed-item',
            '.video-post',
            '.tiktok-post',
            '.video-entry',
            '.video-box',
            'article.video',
            'div[data-video-id]',
            '.content-item',
            '.post-item',
            # Sélecteurs très génériques en dernier recours
            '.card',
            '.item'
        ],
        'title': [
            # Sélecteurs originaux
            'h3.video-card-title a',
            '.video-title a',
            '.title a',
            'h2.video-name a',
            # Nouveaux sélecteurs à essayer
            '.video-caption',
            '.caption',
            '.description',
            '.video-description',
            'p.title',
            '.post-title',
            '.video-text',
            'h2 a',
            'h3 a',
            'h4 a',
            'a.title',
            '.content-title'
        ],
        'thumbnail': [
            # Sélecteurs originaux
            'img.video-card-thumbnail',
            'img.thumbnail',
            '.video-img img',
            '.video-thumbnail img',
            # Nouveaux sélecteurs à essayer
            '.post-thumbnail img',
            '.media-thumbnail img',
            '.preview-image',
            '.video-preview img',
            'div.thumbnail img',
            '.image-container img',
            '.media img',
            'video',
            'video[poster]',
            '.cover-image',
            'img.cover',
            '.image img'
        ],
        'author': [
            # Sélecteurs originaux
            'a.video-card-author',
            '.video-author a',
            '.author-name a',
            '.creator-name',
            # Nouveaux sélecteurs à essayer
            '.username',
            '.user-name',
            '.creator a',
            '.profile-link',
            '.user-link',
            '.account-name',
            '.poster-name',
            '.user-info a',
            '.account a',
            '.author-link',
            '.tiktok-author'
        ],
        'date': [
            # Sélecteurs originaux
            'span.video-card-date',
            '.video-date',
            '.publish-date',
            '.date-info',
            # Nouveaux sélecteurs à essayer
            '.timestamp',
            '.time',
            '.post-date',
            '.published-on',
            '.creation-time',
            '.posted-on',
            '.upload-date',
            '.meta-date',
            'time',
            '[datetime]',
            '.date',
            '.post-time'
        ],
        'stats': [
            # Sélecteurs originaux
            'div.video-card-stats',
            '.video-stats',
            '.engagement-stats',
            '.metrics',
            # Nouveaux sélecteurs à essayer
            '.stats',
            '.counters',
            '.engagement',
            '.numbers',
            '.interaction-stats',
            '.post-stats',
            '.stats-counter',
            '.likes-comments',
            '.video-metrics',
            '.media-stats',
            '.stats-wrapper',
            '.interactions'
        ]
    }
    
    def __init__(self, 
                delay_between_requests: float = 2.0, 
                proxies: Optional[Dict] = None, 
                verify_ssl: bool = True,
                timeout: int = 10):
        """
        Initialise le scraper.
        
        Args:
            delay_between_requests: Temps en secondes d'attente entre les requêtes
            proxies: Dictionnaire optionnel de proxies {'http': 'http://...', 'https': 'https://...'}
            verify_ssl: Si les certificats SSL doivent être vérifiés
            timeout: Timeout en secondes pour les requêtes HTTP
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.delay = delay_between_requests
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        
        # Configuration des proxies si fournis
        if proxies:
            self.session.proxies.update(proxies)
        
    
    def _get_random_user_agent(self) -> str:
        """Retourne un user-agent aléatoire de la liste."""
        return random.choice(self.USER_AGENTS)
    
    
    def _make_request(self, url: str, params: Optional[Dict] = None, max_retries: int = 3, use_json: bool = False) -> Optional[Union[BeautifulSoup, Dict]]:
        """
        Effectue une requête HTTP avec retry automatique et retourne l'objet BeautifulSoup parsé.
        
        Args:
            url: L'URL à requêter
            params: Paramètres de requête optionnels
            max_retries: Nombre maximum de tentatives
            
        Returns:
            Objet BeautifulSoup du HTML parsé ou None en cas d'échec
        """
        
        retry_count = 0
        backoff_factor = 2  # Facteur exponentiel de backoff
        
        while retry_count < max_retries:
            try:
                # Mise à jour de l'user-agent pour chaque requête
                self.session.headers.update({'User-Agent': self._get_random_user_agent()})
                
                # Ajout d'un délai aléatoire pour éviter la limitation de débit
                delay = self.delay + random.uniform(0, 1)
                if retry_count > 0:
                    delay += (backoff_factor ** retry_count)  # Délai exponentiel
                
                time.sleep(delay)
                
                response = self.session.get(
                    url, 
                    params=params, 
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                response.raise_for_status()
                
                logger.info(f"URL requêtée: {response.url}")
                
                # Retourner JSON si demandé, sinon BeautifulSoup
                if use_json:
                    return response.json()
                else:
                    # Utiliser lxml au lieu de html.parser pour un parsing plus robuste
                    return BeautifulSoup(response.text, 'lxml')
            
            except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"Tentative {retry_count}/{max_retries} échouée: {e}. Nouvel essai...")
                else:
                    logger.error(f"Requête échouée après {max_retries} tentatives: {e}")
                    return None
            
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la requête: {e}")
                return None
    
    def _find_load_more_button(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        Trouve le bouton 'Load More' et extrait ses attributs data-* pour les requêtes AJAX.
        
        Args:
            soup: Objet BeautifulSoup à analyser
            
        Returns:
            Dictionnaire des attributs data-* ou None si non trouvé
        """
        # Chercher le bouton Load More avec différents sélecteurs possibles
        button_selectors = [
            # Sélecteurs originaux
            '#hash_load_more',
            '#paging a.btn', 
            'a.load-more-btn',
            'a.js-load-more',
            'button.load-more',
            'a:contains("Load More")',
            'button:contains("Load More")',
            '.load-more-container a',
            # Nouveaux sélecteurs à essayer
            '.pagination a.next',
            '.more-videos-btn',
            '.show-more-btn',
            '.pagination-next',
            '#load-more',
            '#loadMore',
            '.load-more',
            '.loadMore',
            'button[data-load-more]',
            '[data-action="load-more"]',
            'a.more',
            '.paging-load-more',
            'button.more',
            '.view-more',
            '.load-content',
            'a[data-next-page]',
            '.next-page-btn',
            '#next-page',
            '.more-button',
            '.pagination .next',
            'button:contains("Show More")',
            'a:contains("Show More")',
            'button:contains("More")',
            'a:contains("More")'
        ]
        
        for selector in button_selectors:
            load_more = soup.select_one(selector)
            if load_more:
                # Extraire tous les attributs data-*
                data_attrs = {}
                for attr_name, attr_value in load_more.attrs.items():
                    if attr_name.startswith('data-'):
                        data_attrs[attr_name] = attr_value
                
                # Extraire aussi l'URL si c'est un lien
                if load_more.name == 'a' and 'href' in load_more.attrs:
                    data_attrs['href'] = load_more['href']
                
                logger.info(f"Bouton 'Load More' trouvé avec attributs: {data_attrs}")
                return data_attrs
        
        logger.info("Bouton 'Load More' non trouvé")
        return None
        
    def _debug_save_html(self, soup: BeautifulSoup, filename: str = "debug_page.html"):
        """
        Enregistre le HTML pour débogage.
        
        Args:
            soup: Objet BeautifulSoup à enregistrer
            filename: Nom du fichier de sortie
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.info(f"HTML enregistré pour débogage dans {filename}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du HTML de débogage: {e}")
    
    '''def _check_page_structure(self, soup: BeautifulSoup) -> bool:
        """
        Vérifie si la structure de la page correspond à ce qui est attendu.
        
        Args:
            soup: Objet BeautifulSoup à vérifier
            
        Returns:
            True si la structure est valide, False sinon
        """
        # Chercher au moins une carte d'information vidéo avec les différents sélecteurs possibles
        # Note: urlebird ne stocke pas de vidéos, uniquement des liens et métadonnées
        for selector in self.SELECTORS['video_card']:
            elements = soup.select(selector)
            if elements:
                logger.info(f"Structure de page valide, trouvé {len(elements)} cartes d'information avec le sélecteur: {selector}")
                return True
        
        # Si aucun sélecteur ne correspond, enregistrer le HTML pour analyse
        self._debug_save_html(soup, "debug_page.html")
        
        # Analyser la structure pour aider au débogage
        logger.warning("Structure de page non reconnue: aucun élément vidéo trouvé")
        
        # Log quelques informations sur la structure de la page pour aider au débogage
        page_title = soup.title.text if soup.title else "Pas de titre"
        logger.info(f"Titre de la page: {page_title}")
        
        # Vérifier si on est redirigé vers une page d'erreur
        if "not found" in page_title.lower() or "error" in page_title.lower() or "404" in page_title:
            logger.warning("La page semble être une page d'erreur ou 404")
        
        # Log quelques éléments représentatifs pour aider à trouver les nouveaux sélecteurs
        common_containers = ['div.container', 'div.content', 'main', 'div.main-content', 'div.videos', 'div.feed']
        for container in common_containers:
            elements = soup.select(container)
            if elements:
                logger.info(f"Trouvé {len(elements)} éléments avec le sélecteur: {container}")
        
        # Analyser la structure de base pour trouver des indices
        logger.info("Analyse de la structure de base du HTML:")
        try:
            # Essayez de trouver tous les div avec des classes
            divs_with_class = soup.select('div[class]')
            class_count = {}
            for div in divs_with_class[:30]:  # Limiter à 30 premiers pour éviter de surcharger les logs
                classes = div.get('class', [])
                for cls in classes:
                    if cls not in class_count:
                        class_count[cls] = 0
                    class_count[cls] += 1
            
            # Log les classes les plus fréquentes qui pourraient être des conteneurs de vidéos
            top_classes = sorted(class_count.items(), key=lambda x: x[1], reverse=True)[:10]
            logger.info(f"Classes les plus fréquentes dans les divs: {top_classes}")
            
            # Examiner les balises qui pourraient contenir des vidéos
            for tag in ['article', 'div', 'section', 'li']:
                elements = soup.find_all(tag, limit=20)
                if elements:
                    logger.info(f"Trouvé {len(elements)} balises {tag}, premières classes: {[e.get('class', '') for e in elements[:5]]}")
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la structure HTML: {e}")
        
        return False'''
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse des chaînes de date de urlebird en objets datetime.
        Gère plusieurs formats possibles.
        
        Args:
            date_str: Chaîne de date de urlebird
            
        Returns:
            Objet datetime ou None si l'analyse échoue
        """
        if not date_str:
            return None
            
        date_str = date_str.strip()
        
        try:
            # Essayer d'abord le format attendu
            return datetime.strptime(date_str, "%b %d, %Y")
        except ValueError:
            try:
                # Si ça échoue, utiliser dateutil.parser qui est plus flexible
                return date_parser.parse(date_str)
            except Exception:
                logger.warning(f"Impossible d'analyser la date: {date_str}")
                return None
    
    def _is_in_date_range(
        self, 
        video_date: Optional[datetime], 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> bool:
        """
        Vérifie si la date de la vidéo est dans la plage spécifiée.
        
        Args:
            video_date: Date de publication de la vidéo
            start_date: Date de début optionnelle pour le filtrage
            end_date: Date de fin optionnelle pour le filtrage
            
        Returns:
            True si la vidéo est dans la plage, False sinon
        """
        if video_date is None:
            return False
            
        if start_date and video_date < start_date:
            return False
            
        if end_date and video_date > end_date:
            return False
            
        return True
    
    def _find_element_with_selectors(self, parent, selectors: List[str]) -> Optional[BeautifulSoup]:
        """
        Cherche un élément en utilisant plusieurs sélecteurs CSS.
        
        Args:
            parent: Élément parent BeautifulSoup
            selectors: Liste de sélecteurs CSS à essayer
            
        Returns:
            Premier élément correspondant ou None si aucun trouvé
        """
        for selector in selectors:
            element = parent.select_one(selector)
            if element:
                return element
        return None
    
    def _clean_text(self, text: Optional[str]) -> str:
        """Nettoie le texte en supprimant les espaces superflus et caractères non désirés."""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def _extract_number(self, text: str) -> int:
        """
        Extrait un nombre d'une chaîne de texte, en gérant les formats comme "1.2K" ou "5M".
        
        Args:
            text: Texte contenant un nombre
            
        Returns:
            Nombre entier extrait
        """
        if not text:
            return 0
            
        text = text.strip().lower()
        
        try:
            # Supprimer les textes courants
            for suffix in ['views', 'likes', 'comments', 'shares']:
                text = text.replace(suffix, '')
            
            # Supprimer les caractères non numériques sauf .KkMm
            text = re.sub(r'[^\d\.KkMm]', '', text)
            
            # Convertir K/M en valeurs numériques
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            else:
                return int(float(text))
        except ValueError:
            logger.warning(f"Impossible de convertir en nombre: {text}")
            return 0
    
    def _extract_from_json_scripts(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Essaie d'extraire les métadonnées de vidéo des scripts JSON dans la page.
        
        De nombreux sites modernes injectent les données initiales via des objets JSON dans des balises script.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            soup: Objet BeautifulSoup de la page
            
        Returns:
            Liste des métadonnées et liens de vidéos extraites des scripts JSON
        """
        videos = []
        script_selectors = [
            'script[type="application/json"]',
            'script[type="text/javascript"]',
            'script:not([type])',
            'script[id*="__NEXT_DATA__"]',
            'script[id*="__INITIAL_STATE__"]',
            'script[id*="__INITIAL_DATA__"]',
            'script[id*="__APOLLO_STATE__"]'
        ]
        
        for selector in script_selectors:
            scripts = soup.select(selector)
            logger.info(f"Trouvé {len(scripts)} scripts avec le sélecteur: {selector}")
            
            for script in scripts:
                try:
                    # Extraire le contenu du script
                    content = script.string
                    if not content:
                        continue
                    
                    # Essayer de trouver un objet JSON
                    content = content.strip()
                    if content.startswith('window.'):
                        # Cas spécial pour les déclarations window.X = {...}
                        match = re.search(r'window\.[\w\d_]+ = (\{.*\});', content, re.DOTALL)
                        if match:
                            content = match.group(1)
                    
                    # Essayer de parser en tant que JSON
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                    
                    # Chercher des données qui ressemblent à des vidéos TikTok
                    # Explorer récursivement l'objet
                    found_videos = self._extract_videos_from_json_object(data)
                    if found_videos:
                        logger.info(f"Trouvé {len(found_videos)} vidéos dans un script JSON")
                        videos.extend(found_videos)
                
                except Exception as e:
                    logger.warning(f"Erreur lors de l'extraction des données JSON d'un script: {e}")
        
        return videos
    
    def _extract_videos_from_json_object(self, obj, path="") -> List[Dict]:
        """
        Explore récursivement un objet JSON pour trouver des métadonnées de vidéos TikTok.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            obj: Objet JSON à explorer
            path: Chemin actuel dans l'objet (pour le débogage)
            
        Returns:
            Liste des métadonnées et liens de vidéos extraites
        """
        videos = []
        
        if isinstance(obj, dict):
            # Vérifier si cet objet ressemble à une vidéo TikTok
            if self._looks_like_tiktok_video(obj):
                video_info = self._convert_json_to_video_info(obj)
                videos.append(video_info)
            
            # Explorer récursivement chaque clé
            for key, value in obj.items():
                new_path = f"{path}.{key}" if path else key
                found_videos = self._extract_videos_from_json_object(value, new_path)
                videos.extend(found_videos)
                
        elif isinstance(obj, list):
            # Explorer chaque élément de la liste
            for i, item in enumerate(obj):
                new_path = f"{path}[{i}]"
                found_videos = self._extract_videos_from_json_object(item, new_path)
                videos.extend(found_videos)
        
        return videos
    
    def _looks_like_tiktok_video(self, obj: Dict) -> bool:
        """
        Vérifie si un objet JSON ressemble à des informations sur une vidéo TikTok.
        Note: Nous recherchons des métadonnées et des liens, pas les vidéos elles-mêmes.
        
        Args:
            obj: Objet JSON à vérifier
            
        Returns:
            True si l'objet ressemble à des infos de vidéo TikTok, False sinon
        """
        # Chercher des combinaisons de champs qui indiqueraient une vidéo TikTok
        video_indicators = [
            # Au moins 3 de ces champs doivent être présents
            ['id', 'author', 'desc', 'video'],
            ['id', 'author', 'title', 'cover'],
            ['video_id', 'username', 'caption', 'thumbnail'],
            ['videoId', 'authorName', 'text', 'cover'],
            ['id', 'user', 'caption', 'url'],
            ['itemId', 'author', 'text', 'video'],
            ['id', 'creator', 'text', 'media'],
            ['video_url', 'author_name', 'description', 'thumbnail_url'],
            ['play_url', 'nickname', 'desc', 'cover_url'],
            ['id', 'username', 'caption', 'thumbnail']
        ]
        
        # Vérifier les indicateurs statistiques courants
        stat_fields = ['likes', 'comments', 'shares', 'views', 'plays', 'diggs', 'hearts']
        has_stats = any(field in obj for field in stat_fields)
        
        # Vérifier les indicateurs temporels
        time_fields = ['createTime', 'create_time', 'created_at', 'timestamp', 'published_at', 'upload_time', 'date']
        has_time = any(field in obj for field in time_fields)
        
        # Vérifier les combinaisons d'indicateurs
        for indicator_set in video_indicators:
            matches = sum(1 for field in indicator_set if any(f == field or f.lower() == field.lower() for f in obj))
            if matches >= 3:  # Si au moins 3 champs correspondent
                if has_stats or has_time:  # Et qu'il y a des stats ou une date
                    return True
        
        return False
    
    def _convert_json_to_video_info(self, obj: Dict) -> Dict:
        """
        Convertit un objet JSON représentant des informations de vidéo TikTok au format standard.
        Note: Il s'agit de métadonnées et de liens, pas des fichiers vidéo eux-mêmes.
        
        Args:
            obj: Objet JSON représentant des informations de vidéo TikTok
            
        Returns:
            Dictionnaire formaté selon notre structure standard
        """
        # Mapper les champs communs aux différents formats possibles
        video_info = {
            'title': '',
            'url': '',
            'thumbnail': '',
            'author': '',
            'author_url': '',
            'date': None,
            'date_raw': '',
            'views': 0,
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'hashtags': []
        }
        
        # Essayer différents noms de champs courants pour chaque propriété
        field_mappings = {
            'title': ['desc', 'description', 'caption', 'text', 'title', 'content'],
            'url': ['url', 'video_url', 'play_url', 'share_url', 'webVideoUrl', 'web_video_url', 'link', 'video_link'],
            'thumbnail': ['cover', 'thumbnail', 'cover_url', 'thumbnail_url', 'poster', 'image_url', 'image', 'preview_image'],
            'author': ['author_name', 'author', 'username', 'nickname', 'creator', 'user_name', 'userName', 'authorName'],
            'author_url': ['author_url', 'profile_url', 'user_profile', 'author_link'],
            'date_raw': ['createTime', 'create_time', 'created_at', 'timestamp', 'published_at', 'upload_time', 'date', 'publish_time', 'upload_date'],
            'views': ['views', 'play_count', 'playCount', 'view_count', 'viewCount', 'plays'],
            'likes': ['likes', 'like_count', 'likeCount', 'digg_count', 'diggCount', 'hearts', 'heart_count', 'heartCount'],
            'comments': ['comments', 'comment_count', 'commentCount', 'comment_num'],
            'shares': ['shares', 'share_count', 'shareCount', 'repost_count', 'forwards']
        }
        
        # Parcourir les mappages et extraire les valeurs
        for target_field, source_fields in field_mappings.items():
            for source_field in source_fields:
                # Vérifier les variantes de casse
                for field in [source_field, source_field.lower(), source_field.upper()]:
                    if field in obj:
                        value = obj[field]
                        
                        # Cas spéciaux pour certains champs
                        if target_field in ['views', 'likes', 'comments', 'shares']:
                            # Convertir en nombre si nécessaire
                            if isinstance(value, str):
                                value = self._extract_number(value)
                            if not isinstance(value, (int, float)):
                                try:
                                    value = int(value)
                                except (ValueError, TypeError):
                                    value = 0
                        
                        # Enregistrer la valeur dans le dictionnaire résultat
                        video_info[target_field] = value
                        break
                        
                # Si on a trouvé une valeur, passer au champ suivant
                if video_info[target_field]:
                    break
        
        # Traitement spécial pour certains champs
        # Extraire les hashtags du titre
        if video_info['title']:
            video_info['hashtags'] = self._extract_hashtags(video_info['title'])
        
        # Essayer de parser la date
        if video_info['date_raw']:
            video_info['date'] = self._parse_date(str(video_info['date_raw']))
        
        # Vérifier si l'URL est complète
        if video_info['url'] and not video_info['url'].startswith('http'):
            video_info['url'] = self.BASE_URL + video_info['url']
        
        # Vérifier si l'URL de l'auteur est complète
        if video_info['author_url'] and not video_info['author_url'].startswith('http'):
            video_info['author_url'] = self.BASE_URL + video_info['author_url']
        
        return video_info
    
    def _extract_hashtags(self, text: str) -> List[str]:
        """
        Extrait les hashtags d'un texte.
        
        Args:
            text: Texte contenant des hashtags
            
        Returns:
            Liste de hashtags sans le symbole #
        """
        if not text:
            return []
            
        # Utiliser une regex plus précise pour les hashtags
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags
    
    def _extract_video_info(self, video_element) -> Dict:
        """
        Extrait les métadonnées et liens d'une carte d'information vidéo.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            video_element: Élément BeautifulSoup représentant une carte d'information vidéo
            
        Returns:
            Dictionnaire avec les métadonnées et liens de la vidéo TikTok
        """
        video_info = {
            'title': '',
            'url': '',
            'thumbnail': '',
            'author': '',
            'author_url': '',
            'date': None,
            'date_raw': '',  # Stocker la date brute pour débogage
            'views': 0,
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'hashtags': []
        }
        
        try:
            # Extraction du titre et de l'URL de la vidéo avec des sélecteurs multiples
            title_element = self._find_element_with_selectors(video_element, self.SELECTORS['title'])
            if title_element:
                video_info['title'] = self._clean_text(title_element.text)
                # S'assurer que l'URL est absolue
                href = title_element.get('href', '')
                if href:
                    video_info['url'] = href if href.startswith('http') else self.BASE_URL + href
            
            # Extraction de la vignette avec des sélecteurs multiples
            thumbnail_element = self._find_element_with_selectors(video_element, self.SELECTORS['thumbnail'])
            if thumbnail_element:
                # Essayer différents attributs pour l'URL de la vignette
                for attr in ['src', 'data-src', 'data-original']:
                    if attr in thumbnail_element.attrs and thumbnail_element[attr]:
                        video_info['thumbnail'] = thumbnail_element[attr]
                        break
            
            # Extraction des informations de l'auteur
            author_element = self._find_element_with_selectors(video_element, self.SELECTORS['author'])
            if author_element:
                video_info['author'] = self._clean_text(author_element.text)
                href = author_element.get('href', '')
                if href:
                    video_info['author_url'] = href if href.startswith('http') else self.BASE_URL + href
            
            # Extraction de la date
            date_element = self._find_element_with_selectors(video_element, self.SELECTORS['date'])
            if date_element:
                date_str = self._clean_text(date_element.text)
                video_info['date_raw'] = date_str  # Stocker pour débogage
                video_info['date'] = self._parse_date(date_str)
            
            # Extraction des statistiques vidéo (vues, likes, etc.)
            stats_elements = video_element.select(','.join(self.SELECTORS['stats']))
            for stat in stats_elements:
                stat_text = stat.text.strip().lower()
                
                if 'views' in stat_text or 'vue' in stat_text:
                    video_info['views'] = self._extract_number(stat_text)
                elif 'likes' in stat_text or 'j\'aime' in stat_text:
                    video_info['likes'] = self._extract_number(stat_text)
                elif 'comments' in stat_text or 'commentaire' in stat_text:
                    video_info['comments'] = self._extract_number(stat_text)
                elif 'shares' in stat_text or 'partage' in stat_text:
                    video_info['shares'] = self._extract_number(stat_text)
            
            # Extraction des hashtags du titre
            if video_info['title']:
                video_info['hashtags'] = self._extract_hashtags(video_info['title'])
                
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des informations de la vidéo: {e}")
        
        # Validation basique
        if not video_info['url'] or not video_info['title']:
            logger.warning("Informations de vidéo incomplètes extraites")
        
        return video_info
    
    def _load_more_videos(self, load_more_data: Dict, hashtag: str) -> Optional[List[Dict]]:
        """
        Effectue une requête AJAX pour charger plus de métadonnées et liens de vidéos.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            load_more_data: Attributs data-* du bouton Load More
            hashtag: Le hashtag recherché
            
        Returns:
            Liste des métadonnées et liens de vidéos ou None en cas d'échec
        """
        # Exemple d'implémentation - à adapter selon la structure réelle des requêtes AJAX
        # Note: cette implémentation est hypothétique et devra être ajustée en fonction de l'analyse du site
        
        # URL pour les requêtes AJAX (à déterminer en analysant le site)
        ajax_url = f"{self.BASE_URL}/api/v1/hash/{hashtag}/videos"
        
        # Préparer les paramètres pour la requête AJAX
        ajax_params = {}
        
        # Copier tous les attributs data-* comme paramètres
        for key, value in load_more_data.items():
            if key.startswith('data-'):
                # Convertir data-page-num en page_num par exemple
                param_key = key.replace('data-', '').replace('-', '_')
                ajax_params[param_key] = value
        
        # Si un href est présent, on peut l'utiliser directement au lieu de construire l'URL
        if 'href' in load_more_data:
            ajax_url = self.BASE_URL + load_more_data['href'] if not load_more_data['href'].startswith('http') else load_more_data['href']
            ajax_params = None  # Les paramètres sont déjà dans l'URL
        
        logger.info(f"Chargement de vidéos supplémentaires via AJAX: {ajax_url}")
        
        # Effectuer la requête AJAX
        response = self._make_request(ajax_url, params=ajax_params, use_json=True)
        if not response:
            return None
        
        # Analyser la réponse (dépend de la structure de la réponse AJAX)
        # Ce code est hypothétique et devra être adapté à la structure réelle
        try:
            # Si la réponse contient directement du HTML
            if 'html' in response:
                html_content = response['html']
                soup = BeautifulSoup(html_content, 'lxml')
                
                # Extraire les vidéos du HTML fourni
                videos = []
                for selector in self.SELECTORS['video_card']:
                    video_elements = soup.select(selector)
                    if video_elements:
                        for video_element in video_elements:
                            video_info = self._extract_video_info(video_element)
                            videos.append(video_info)
                        logger.info(f"Extrait {len(videos)} vidéos supplémentaires via AJAX")
                        return videos
            
            # Si la réponse contient des données JSON directement
            elif 'videos' in response:
                # Adaptez cette partie à la structure réelle des données
                videos = []
                for video_data in response['videos']:
                    # Convertir les données JSON en format compatible avec notre structure
                    video_info = {
                        'title': video_data.get('title', ''),
                        'url': video_data.get('url', ''),
                        'thumbnail': video_data.get('cover', ''),
                        'author': video_data.get('author', {}).get('name', ''),
                        'author_url': video_data.get('author', {}).get('url', ''),
                        'date': self._parse_date(video_data.get('create_time', '')),
                        'date_raw': video_data.get('create_time', ''),
                        'views': video_data.get('play_count', 0),
                        'likes': video_data.get('digg_count', 0),
                        'comments': video_data.get('comment_count', 0),
                        'shares': video_data.get('share_count', 0),
                        'hashtags': video_data.get('hashtags', [])
                    }
                    videos.append(video_info)
                logger.info(f"Extrait {len(videos)} vidéos supplémentaires via AJAX (format JSON)")
                return videos
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de la réponse AJAX: {e}")
        
        return None
    
    def search_videos(
        self, 
        hashtag: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_pages: int = 5,
        incremental_save_path: Optional[str] = None,
        save_every: int = 2
    ) -> List[Dict]:
        """
        Recherche des métadonnées et liens de vidéos TikTok avec un hashtag spécifique.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            hashtag: Hashtag à rechercher (avec ou sans le symbole #)
            start_date: Date de début pour le filtrage des vidéos (incluse)
            end_date: Date de fin pour le filtrage des vidéos (incluse)
            max_pages: Nombre maximum de pages à scraper
            incremental_save_path: Chemin pour sauvegarder les résultats de manière incrémentale
            save_every: Sauvegarder après ce nombre de pages
            
        Returns:
            Liste de dictionnaires contenant les métadonnées et liens des vidéos TikTok
        """
        results = []
        current_page = 1
        
        # Supprimer # si inclus dans le hashtag
        if hashtag.startswith('#'):
            hashtag = hashtag[1:]
            
        logger.info(f"Recherche de vidéos avec le hashtag: {hashtag}")
        if start_date:
            logger.info(f"Date de début: {start_date.strftime('%Y-%m-%d')}")
        if end_date:
            logger.info(f"Date de fin: {end_date.strftime('%Y-%m-%d')}")
        
        while current_page <= max_pages:
            logger.info(f"Scraping de la page {current_page}/{max_pages}")
            
            # Construire l'URL directement avec le hashtag
            url = f"{self.SEARCH_URL}{hashtag}/"
            
            logger.info(f"URL construite: {url}")
            
            # Ne plus utiliser de paramètres d'URL car le site utilise des chemins directs
            soup = self._make_request(url)
            if not soup:
                logger.warning(f"Impossible de récupérer la page {current_page}")
                break
            
            # Enregistrer le HTML pour le débogage
            self._debug_save_html(soup, f"debug_page_{hashtag}.html")
            
            '''# Vérifier si la structure de la page est valide
            if not self._check_page_structure(soup):
                logger.warning("La structure de la page a changé, arrêt du scraping")
                break'''
            
            # Trouver tous les éléments d'information vidéo (cartes) sur la page
            # Note: urlebird ne stocke pas de vidéos, uniquement des liens et métadonnées
            video_cards = []
            for selector in self.SELECTORS['video_card']:
                elements = soup.select(selector)
                if elements:
                    video_cards = elements
                    logger.info(f"Cartes d'information vidéo trouvées avec le sélecteur: {selector} - {len(elements)} résultats")
                    break
            
            if not video_cards:
                logger.info("Plus d'éléments d'information vidéo trouvés")
                break
                
            logger.info(f"Trouvé {len(video_cards)} cartes d'information vidéo sur la page {current_page}")
            
            # Traiter chaque carte d'information vidéo
            videos_on_page = 0
            for video_element in video_cards:
                video_info = self._extract_video_info(video_element)
                
                # Vérifier si la vidéo est dans la plage de dates
                if self._is_in_date_range(video_info['date'], start_date, end_date):
                    results.append(video_info)
                    videos_on_page += 1
            
            logger.info(f"{videos_on_page} vidéos sur la page {current_page} sont dans la plage de dates spécifiée")
            
            # Trouver le bouton "Load More" pour charger plus de vidéos via AJAX
            load_more_data = self._find_load_more_button(soup)
            has_next_page = bool(load_more_data)
            
            # Si on a trouvé un bouton Load More, essayer de charger plus de vidéos
            if has_next_page and current_page < max_pages:
                # On ne tente de charger plus de vidéos que si on n'a pas atteint max_pages
                additional_videos = self._load_more_videos(load_more_data, hashtag)
                if additional_videos:
                    # Filtrer les vidéos supplémentaires par date
                    for video_info in additional_videos:
                        if self._is_in_date_range(video_info['date'], start_date, end_date):
                            results.append(video_info)
                    
                    logger.info(f"Ajouté {len(additional_videos)} vidéos supplémentaires via AJAX")
            
            # Sauvegarde incrémentale
            if incremental_save_path and current_page % save_every == 0 and results:
                temp_path = f"{incremental_save_path}.temp"
                self.save_to_csv(results, temp_path)
                logger.info(f"Sauvegarde incrémentale: {len(results)} vidéos à {temp_path}")
            
            if not has_next_page:
                logger.info("C'est la dernière page, arrêt du scraping")
                break
            
            current_page += 1
        
        logger.info(f"Total des vidéos trouvées dans la plage de dates: {len(results)}")
        return results
    
    def search_videos_concurrent(
        self,
        hashtag: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_pages: int = 5,
        max_workers: int = 3
    ) -> List[Dict]:
        """
        Version concurrente de search_videos avec des requêtes parallèles limitées.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        Attention: Utilisez cette méthode avec prudence pour éviter de surcharger le serveur.
        
        Args:
            hashtag: Hashtag à rechercher (avec ou sans le symbole #)
            start_date: Date de début pour le filtrage des vidéos
            end_date: Date de fin pour le filtrage des vidéos
            max_pages: Nombre maximum de pages à scraper
            max_workers: Nombre maximum de workers concurrents
            
        Returns:
            Liste de dictionnaires contenant les métadonnées et liens des vidéos TikTok
        """
        results = []
        
        # Supprimer # si inclus dans le hashtag
        if hashtag.startswith('#'):
            hashtag = hashtag[1:]
        
        logger.info(f"Recherche concurrente de vidéos avec le hashtag: {hashtag} (max_workers={max_workers})")
        
        def fetch_page(page_num):
            """Fonction pour récupérer et traiter une seule page."""
            logger.info(f"Worker traitant la page {page_num}/{max_pages}")
            
            page_results = []
            # Construire l'URL directement avec le hashtag pour le traitement concurrent
            url = f"{self.SEARCH_URL}{hashtag}/"
            
            # Ne plus utiliser de paramètres d'URL car le site utilise des chemins directs
            soup = self._make_request(url)
            '''if not soup or not self._check_page_structure(soup):'''
            return page_results
            
            # Trouver toutes les cartes d'information vidéo
            video_cards = []
            for selector in self.SELECTORS['video_card']:
                elements = soup.select(selector)
                if elements:
                    video_cards = elements
                    break
            
            # Traiter chaque carte d'information vidéo
            for video_element in video_cards:
                video_info = self._extract_video_info(video_element)
                
                # Vérifier si la vidéo est dans la plage de dates
                if self._is_in_date_range(video_info['date'], start_date, end_date):
                    page_results.append(video_info)
            
            logger.info(f"Page {page_num}: trouvé {len(page_results)} éléments d'information dans la plage de dates")
            return page_results
        
        # Note: Comme le site utilise Load More plutôt que des pages distinctes,
        # l'implémentation concurrente n'est pas idéale. On effectue une seule requête initiale.
        # On pourrait potentiellement paralléliser les requêtes AJAX "Load More" ultérieures.
        
        # Pour l'instant, on utilise simplement la méthode non concurrente
        return self.search_videos(
            hashtag=hashtag,
            start_date=start_date,
            end_date=end_date,
            max_pages=max_pages
        )
        
        logger.info(f"Total des vidéos trouvées avec le scraping concurrent: {len(results)}")
        return results
    
    def save_to_csv(self, videos: List[Dict], output_file: str):
        """
        Sauvegarde les métadonnées et liens des vidéos dans un fichier CSV.
        Note: urlebird.com n'héberge pas de vidéos, seulement des liens et des métadonnées.
        
        Args:
            videos: Liste de dictionnaires contenant les métadonnées et liens des vidéos TikTok
            output_file: Chemin vers le fichier CSV de sortie
        """
        if not videos:
            logger.warning("Pas de vidéos à sauvegarder")
            return
        
        # Créer le répertoire de sortie s'il n'existe pas
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Répertoire de sortie créé: {output_dir}")
        
        # Convertir en DataFrame
        df = pd.DataFrame(videos)
        
        # Convertir date en format chaîne
        if 'date' in df.columns:
            df['date'] = df['date'].apply(
                lambda x: x.strftime('%Y-%m-%d') if x else None
            )
        
        # Supprimer la colonne date_raw utilisée pour le débogage
        if 'date_raw' in df.columns:
            df = df.drop(columns=['date_raw'])
        
        # Convertir la liste de hashtags en chaîne séparée par des virgules
        if 'hashtags' in df.columns:
            df['hashtags'] = df['hashtags'].apply(lambda x: ','.join(x) if x else '')
        
        # Sauvegarder en CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Sauvegardé {len(videos)} vidéos dans {output_file}")
        
        # Générer quelques statistiques de base
        logger.info("Statistiques de base:")
        logger.info(f"- Nombre total de vidéos: {len(videos)}")
        if 'views' in df.columns:
            logger.info(f"- Moyenne des vues: {df['views'].mean():.1f}")
        if 'likes' in df.columns:
            logger.info(f"- Moyenne des likes: {df['likes'].mean():.1f}")
        if 'author' in df.columns:
            logger.info(f"- Nombre d'auteurs uniques: {df['author'].nunique()}")