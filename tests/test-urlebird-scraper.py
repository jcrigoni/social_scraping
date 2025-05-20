import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup
import requests_mock
import os
import sys

# Ajouter le répertoire parent au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.urlebird_scraper import UrlebirdScraper

class TestUrlebirdScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = UrlebirdScraper(delay_between_requests=0.1)  # Délai court pour les tests
        
        # Exemple HTML pour les tests
        self.example_html = """
        <html>
            <body>
                <div class="video-card">
                    <h3 class="video-card-title">
                        <a href="/video/12345">Test Video #dance #viral</a>
                    </h3>
                    <img class="video-card-thumbnail" src="https://example.com/thumb.jpg">
                    <a class="video-card-author" href="/user/testuser">testuser</a>
                    <span class="video-card-date">Apr 15, 2023</span>
                    <div class="video-card-stats">1.5K views</div>
                    <div class="video-card-stats">500 likes</div>
                    <div class="video-card-stats">100 comments</div>
                    <div class="video-card-stats">50 shares</div>
                </div>
            </body>
        </html>
        """
        
    def test_parse_date(self):
        # Test avec un format de date valide
        date_str = "Apr 15, 2023"
        expected = datetime(2023, 4, 15)
        self.assertEqual(self.scraper._parse_date(date_str), expected)
        
        # Test avec un format de date alternatif
        date_str2 = "2023-04-15"
        self.assertEqual(self.scraper._parse_date(date_str2), expected)
        
        # Test avec un format de date invalide
        invalid_date = "Invalid date"
        self.assertIsNone(self.scraper._parse_date(invalid_date))
    
    def test_is_in_date_range(self):
        test_date = datetime(2023, 5, 15)
        
        # Test sans limites de date
        self.assertTrue(self.scraper._is_in_date_range(test_date))
        
        # Test avec date de début seulement
        self.assertTrue(self.scraper._is_in_date_range(test_date, start_date=datetime(2023, 1, 1)))
        self.assertFalse(self.scraper._is_in_date_range(test_date, start_date=datetime(2023, 6, 1)))
        
        # Test avec date de fin seulement
        self.assertTrue(self.scraper._is_in_date_range(test_date, end_date=datetime(2023, 6, 1)))
        self.assertFalse(self.scraper._is_in_date_range(test_date, end_date=datetime(2023, 4, 1)))
        
        # Test avec les deux limites
        self.assertTrue(self.scraper._is_in_date_range(
            test_date, 
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        ))
        self.assertFalse(self.scraper._is_in_date_range(
            test_date, 
            start_date=datetime(2023, 6, 1),
            end_date=datetime(2023, 12, 31)
        ))
    
    def test_extract_number(self):
        # Test de différents formats numériques
        self.assertEqual(self.scraper._extract_number("1000 views"), 1000)
        self.assertEqual(self.scraper._extract_number("1.5K likes"), 1500)
        self.assertEqual(self.scraper._extract_number("2M views"), 2000000)
        self.assertEqual(self.scraper._extract_number("1,234"), 1234)
        self.assertEqual(self.scraper._extract_number(""), 0)
    
    def test_extract_hashtags(self):
        # Test d'extraction de hashtags
        text = "This is a #test with #multiple hashtags"
        expected = ["test", "multiple"]
        self.assertEqual(self.scraper._extract_hashtags(text), expected)
        
        # Test sans hashtags
        self.assertEqual(self.scraper._extract_hashtags("No hashtags here"), [])
        
        # Test avec texte vide
        self.assertEqual(self.scraper._extract_hashtags(""), [])
    
    def test_check_page_structure(self):
        # Test avec une structure valide
        soup = BeautifulSoup(self.example_html, 'lxml')
        self.assertTrue(self.scraper._check_page_structure(soup))
        
        # Test avec une structure invalide
        invalid_html = "<html><body><div>No video cards here</div></body></html>"
        invalid_soup = BeautifulSoup(invalid_html, 'lxml')
        self.assertFalse(self.scraper._check_page_structure(invalid_soup))
    
    def test_extract_video_info(self):
        soup = BeautifulSoup(self.example_html, 'lxml')
        video_element = soup.find('div', class_='video-card')
        
        video_info = self.scraper._extract_video_info(video_element)
        
        # Vérifier les informations extraites
        self.assertEqual(video_info['title'], 'Test Video #dance #viral')
        self.assertEqual(video_info['url'], 'https://urlebird.com/video/12345')
        self.assertEqual(video_info['thumbnail'], 'https://example.com/thumb.jpg')
        self.assertEqual(video_info['author'], 'testuser')
        self.assertEqual(video_info['author_url'], 'https://urlebird.com/user/testuser')
        self.assertEqual(video_info['date'], datetime(2023, 4, 15))
        self.assertEqual(video_info['views'], 1500)
        self.assertEqual(video_info['likes'], 500)
        self.assertEqual(video_info['comments'], 100)
        self.assertEqual(video_info['shares'], 50)
        self.assertEqual(video_info['hashtags'], ['dance', 'viral'])
    
    @requests_mock.Mocker()
    def test_make_request(self, m):
        test_url = "https://urlebird.com/search/"
        
        # Mocker la requête HTTP
        m.get(test_url, text=self.example_html)
        
        # Appeler la méthode
        soup = self.scraper._make_request(test_url)
        
        # Vérifier que BeautifulSoup a été appelé avec le HTML correct
        self.assertIsInstance(soup, BeautifulSoup)
        self.assertTrue(soup.find('div', class_='video-card'))
    
    @requests_mock.Mocker()
    def test_search_videos(self, m):
        # Mocker la requête de recherche
        m.get("https://urlebird.com/search/?q=dance&page=1", text=self.example_html)
        # Mocker une page vide pour la page 2 (pour tester l'arrêt)
        m.get("https://urlebird.com/search/?q=dance&page=2", text="<html><body></body></html>")
        
        # Appeler la méthode de recherche
        results = self.scraper.search_videos(
            hashtag="dance",
            max_pages=3
        )
        
        # Vérifier les résultats
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Test Video #dance #viral')
    
    @patch('src.urlebird_scraper.UrlebirdScraper._make_request')
    def test_search_videos_empty_result(self, mock_make_request):
        # Configurer le mock pour retourner une page sans vidéos
        mock_soup = BeautifulSoup("<html><body></body></html>", 'lxml')
        mock_make_request.return_value = mock_soup
        
        # Appeler la méthode
        results = self.scraper.search_videos(hashtag="nonexistenttag")
        
        # Vérifier qu'aucun résultat n'est retourné
        self.assertEqual(len(results), 0)
    
    def test_clean_text(self):
        # Test de nettoyage de texte
        self.assertEqual(self.scraper._clean_text("  Text  with  extra  spaces  "), "Text with extra spaces")
        self.assertEqual(self.scraper._clean_text(None), "")
        self.assertEqual(self.scraper._clean_text(""), "")

if __name__ == '__main__':
    unittest.main()
