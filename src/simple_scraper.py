import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time
import random
import os
from logger import setup_logger

# Configure logging
logger = setup_logger('simple_scraper')

class SocialScraper:
    """
    A simplified scraper for urlebird.com that extracts video URLs, IDs, and metadata.
    This version focuses purely on extracting the basic information needed without extra complexity.
    """
    
    BASE_URL = "https://urlebird.com"
    
    # Common user agents for browser simulation
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'
    ]
    
    def __init__(self, delay_between_requests=2.0):
        """
        Initialize the scraper with basic settings.
        
        Args:
            delay_between_requests: Time in seconds to wait between requests
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        self.delay = delay_between_requests
    
    def _get_random_user_agent(self):
        """Returns a random user agent."""
        return random.choice(self.USER_AGENTS)
    
    def _make_request(self, url, max_retries=3):
        """
        Makes an HTTP request with retry logic.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retry attempts
            
        Returns:
            BeautifulSoup object or None if the request fails
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Rotate user agent
                self.session.headers.update({'User-Agent': self._get_random_user_agent()})
                
                # Add delay
                time.sleep(self.delay)
                
                # Make the request
                response = self.session.get(url)
                response.raise_for_status()
                
                logger.info(f"Successfully requested: {url}")
                return BeautifulSoup(response.text, 'html.parser')
            
            except Exception as e:
                retry_count += 1
                logger.warning(f"Request attempt {retry_count} failed: {e}")
                if retry_count >= max_retries:
                    logger.error(f"All {max_retries} attempts failed.")
                    return None
    
    def _extract_video_id(self, url):
        """
        Extracts the video ID from a URL.
        
        Args:
            url: The video URL
            
        Returns:
            The extracted video ID or empty string if not found
        """
        # URL pattern is like: https://urlebird.com/video/title-7497678636284120362/
        id_match = re.search(r'(\d+)(?:/)?$', url)
        if id_match:
            return id_match.group(1)
        return ""
    
    def _extract_number(self, text):
        """
        Extracts a numeric value from text, handling K, M suffixes.
        
        Args:
            text: Text containing a number (e.g., "1.5M")
            
        Returns:
            Extracted numeric value as integer
        """
        if not text:
            return 0
            
        # Remove non-numeric characters except digits, dot, K, M
        text = re.sub(r'[^\d\.KkMm]', '', text.strip().lower())
        
        try:
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            elif text:
                # Handle comma-separated numbers like 1,200
                text = text.replace(',', '')
                return int(float(text))
            return 0
        except ValueError:
            logger.warning(f"Could not convert to number: {text}")
            return 0
    
    def scrape_hashtag(self, hashtag, max_pages=1):
        """
        Scrapes videos from a hashtag page.
        
        Args:
            hashtag: Hashtag to search for (without # symbol)
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of dictionaries with video information
        """
        # Remove # if present
        if hashtag.startswith('#'):
            hashtag = hashtag[1:]
        
        logger.info(f"Scraping hashtag: {hashtag}, max pages: {max_pages}")
        
        results = []
        current_page = 1
        
        # Build the URL
        url = f"{self.BASE_URL}/hash/{hashtag}/"
        
        while current_page <= max_pages:
            logger.info(f"Scraping page {current_page}/{max_pages}")
            
            # Request the page
            soup = self._make_request(url)
            if not soup:
                logger.error("Failed to get the page")
                break
            
            # Save a copy for debugging
            self._save_debug_html(soup, f"debug_page_{hashtag}.html")
            
            # Find the container with the video cards
            thumbs_container = soup.select_one('#thumbs')
            if not thumbs_container:
                logger.warning("Could not find #thumbs container")
                break
                
            # Find all video cards within the container
            # Make sure to exclude ad elements which have class 'display-flex-semi'
            video_elements = []
            for element in thumbs_container.select('div.thumb'):
                if 'display-flex-semi' not in element.get('class', []):
                    video_elements.append(element)
                    
            if not video_elements:
                logger.warning("No video elements found on the page")
                break
                
            logger.info(f"Found {len(video_elements)} valid video elements")
            
            # Extract data from each video card
            videos_extracted = 0
            for video_element in video_elements:
                try:
                    video_info = self._extract_video_info(video_element)
                    if video_info:
                        results.append(video_info)
                        videos_extracted += 1
                except Exception as e:
                    logger.error(f"Error extracting video info: {e}")
            
            logger.info(f"Extracted {videos_extracted} videos from page {current_page}")
            
            # Find if there's a "Load More" button
            load_more = soup.select_one('#hash_load_more')
            if not load_more:
                logger.info("No 'Load More' button found")
                break
                
            # For simplicity, we'll just stop after the first page by default
            if current_page >= max_pages:
                break
                
            current_page += 1
            
            # In a real implementation, we would handle the AJAX Load More here
            # This would involve extracting the data-* attributes from the button
            # and making additional AJAX requests to load more content
            
        logger.info(f"Scraped {len(results)} videos total")
        return results
    
    def _extract_video_info(self, video_element):
        """
        Extracts video information from a video card element.
        
        Args:
            video_element: BeautifulSoup element representing a video card
            
        Returns:
            Dictionary with video information or None if extraction fails
        """
        video_info = {
            'url': '',
            'video_id': '',
            'timestamp': '',
            'views_raw': '',
            'likes_raw': '',
            'comments_raw': '',
            'views': 0,
            'likes': 0, 
            'comments': 0,
            'title': '',
            'author': '',
            'author_url': ''
        }
        
        try:
            # Check if this is an ad or undesired element
            if video_element.get('class') and 'display-flex-semi' in video_element.get('class', []):
                logger.debug("Skipping advertisement element")
                return None
                
            # Extract video URL - first priority is the overlay link (most reliable)
            # This is usually the last <a> tag in the element with class="overlay-s"
            overlay_links = [a for a in video_element.select('a') 
                           if '/video/' in a.get('href', '') and ('overlay-s' in a.get('class', []) 
                                                             or a.select_one('.overlay-s'))]
            if overlay_links:
                video_url = overlay_links[0]['href']
                video_info['url'] = video_url
                video_info['video_id'] = self._extract_video_id(video_url)
                logger.debug(f"Extracted video URL from overlay: {video_url}")
            
            # If no overlay link found, check for video links in the info3 div
            if not video_info['url']:
                info_div = video_element.select_one('.info3')
                if info_div:
                    # Find all links in the info3 div that aren't author links
                    # The video link is usually the non-author link in the info3 div
                    video_links = [a for a in info_div.select('a') 
                                 if a.parent.get('class') != ['author-name'] and 
                                    '/video/' in a.get('href', '')]
                    
                    if video_links:
                        video_url = video_links[0]['href']
                        video_info['url'] = video_url
                        video_info['video_id'] = self._extract_video_id(video_url)
                        logger.debug(f"Extracted video URL from info3: {video_url}")
                        
                        # Extract title if there's a span inside the link
                        if video_links[0].select_one('span'):
                            video_info['title'] = video_links[0].select_one('span').text.strip()
            
            # Extract author info
            author_div = video_element.select_one('.author-name')
            if author_div and author_div.select_one('a'):
                author_link = author_div.select_one('a')
                video_info['author'] = author_link.text.strip()
                video_info['author_url'] = author_link['href']
                logger.debug(f"Extracted author: {video_info['author']}")
            
            # Extract stats (timestamp, views, likes, comments)
            stats_div = video_element.select_one('.stats')
            if stats_div:
                # Extract each stat individually by its icon class
                # This ensures we get the right metadata even if the order changes
                
                # Timestamp (clock icon)
                timestamp_element = stats_div.select_one('.fa-clock')
                if timestamp_element and timestamp_element.parent:
                    timestamp_text = timestamp_element.parent.text.strip()
                    video_info['timestamp'] = timestamp_text.replace('fa-clock', '').strip()
                    logger.debug(f"Extracted timestamp: {video_info['timestamp']}")
                
                # Views (play icon)
                views_element = stats_div.select_one('.fa-play')
                if views_element and views_element.parent:
                    views_text = views_element.parent.text.strip()
                    clean_views = views_text.replace('fa-play', '').strip()
                    video_info['views_raw'] = clean_views
                    video_info['views'] = self._extract_number(clean_views)
                    logger.debug(f"Extracted views: {clean_views} -> {video_info['views']}")
                
                # Likes (heart icon)
                likes_element = stats_div.select_one('.fa-heart')
                if likes_element and likes_element.parent:
                    likes_text = likes_element.parent.text.strip()
                    clean_likes = likes_text.replace('fa-heart', '').strip()
                    video_info['likes_raw'] = clean_likes
                    video_info['likes'] = self._extract_number(clean_likes)
                    logger.debug(f"Extracted likes: {clean_likes} -> {video_info['likes']}")
                
                # Comments (comment icon)
                comments_element = stats_div.select_one('.fa-comment')
                if comments_element and comments_element.parent:
                    comments_text = comments_element.parent.text.strip()
                    clean_comments = comments_text.replace('fa-comment', '').strip()
                    video_info['comments_raw'] = clean_comments
                    video_info['comments'] = self._extract_number(clean_comments)
                    logger.debug(f"Extracted comments: {clean_comments} -> {video_info['comments']}")
            
            # Basic validation
            if not video_info['url'] or not video_info['video_id']:
                logger.warning("Missing critical information (URL or video ID)")
                return None
                
            return video_info
            
        except Exception as e:
            logger.error(f"Error in extraction: {e}")
            return None
    
    def _save_debug_html(self, soup, filename):
        """
        Saves HTML to a file for debugging.
        
        Args:
            soup: BeautifulSoup object
            filename: Name of the output file
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.info(f"Saved debug HTML to {filename}")
        except Exception as e:
            logger.error(f"Error saving debug HTML: {e}")
    
    def save_to_csv(self, videos, output_file):
        """
        Saves the video data to a CSV file.
        
        Args:
            videos: List of video info dictionaries
            output_file: Path to the output CSV file
        """
        if not videos:
            logger.warning("No videos to save")
            return
        
        # Create output directory if needed
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")
        
        # Convert to DataFrame
        df = pd.DataFrame(videos)
        
        # Define column order with priority columns first
        priority_columns = [
            'url',           # Video URL
            'video_id',      # Extracted ID
            'timestamp',     # Raw timestamp text
            'views_raw',     # Raw views value
            'likes_raw',     # Raw likes value
            'comments_raw',  # Raw comments value
            'views',         # Numeric views
            'likes',         # Numeric likes
            'comments',      # Numeric comments
            'title',         # Video title
            'author',        # Author name
            'author_url'     # Author profile URL
        ]
        
        # Reorder columns to match priority (if they exist)
        columns = [col for col in priority_columns if col in df.columns]
        df = df[columns]
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(videos)} videos to {output_file}")
        
        # Log some basic stats
        logger.info(f"- Total videos: {len(videos)}")
        if 'views' in df.columns:
            logger.info(f"- Average views: {df['views'].mean():.1f}")
        if 'likes' in df.columns:
            logger.info(f"- Average likes: {df['likes'].mean():.1f}")
        if 'comments' in df.columns:
            logger.info(f"- Average comments: {df['comments'].mean():.1f}")


def main():
    """Simple command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple Urlebird Scraper')
    parser.add_argument('--hashtag', required=True, help='Hashtag to scrape (without # symbol)')
    parser.add_argument('--output', default='data/videos.csv', help='Output CSV file path')
    parser.add_argument('--max-pages', type=int, default=1, help='Maximum number of pages to scrape')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    # Create and run the scraper
    scraper = SocialScraper(delay_between_requests=args.delay)
    videos = scraper.scrape_hashtag(args.hashtag, max_pages=args.max_pages)
    
    if videos:
        scraper.save_to_csv(videos, args.output)
        print(f"Scraped {len(videos)} videos and saved to {args.output}")
    else:
        print("No videos found.")

if __name__ == "__main__":
    main()