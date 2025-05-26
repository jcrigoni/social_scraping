"""
Enhanced scraper that uses headless browser for better data extraction.
Integrates BrowserManager with SocialScraper to extract videos data based on hashtag search.
"""

import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import datetime
from dateutil.relativedelta import relativedelta
from logger import setup_logger
from browser import BrowserManager
from config import SCRAPER_CONFIG

# Configure logging
logger = setup_logger('enhanced_scraper')

class EnhancedSocialScraper:
    """
    Enhanced scraper for tiktok that uses a headless browser to 
    load the full page content before scraping, allowing extraction of complete
    hashtag data.
    """
    
    BASE_URL = SCRAPER_CONFIG['BASE_URL']
    
    def __init__(self, delay_between_requests=2.0):
        """
        Initialize the enhanced scraper with browser support.
        
        Args:
            delay_between_requests: Time in seconds to wait between requests
        """
        self.delay = delay_between_requests
        self.browser_manager = BrowserManager()
    
    def _extract_video_id(self, url):
        """
        Extracts the video ID from a URL.
        
        Args:
            url: The video URL
            
        Returns:
            The extracted video ID or empty string if not found
        """
        # URL pattern is like: https://example.com/video/title-7497678636284120362/
        id_match = re.search(r'(\d+)(?:/)?$', url) # Capture digits and reject /'s, at the end of url
        if id_match:
            return id_match.group(1) # Extracts the content of the first capturing group from the regex match (\d+) = digits
        return "" # Returns empty string
    
    def _convert_relative_time(self, relative_time_text):
        """
        Converts a relative time expression (e.g., "3 days ago") to a datetime object.
        
        Args:
            relative_time_text: String with relative time expression
            
        Returns:
            Datetime object or None if parsing fails
        """
        if not relative_time_text:
            return None
            
        now = datetime.datetime.now()
        text = relative_time_text.lower().strip()
        
        try:
            # Extract the number and time unit using regex
            match = re.match(r'(\d+)\s+([a-z]+)', text)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                
                # Handle different time units
                if 'year' in unit:
                    return now - relativedelta(years=value)
                elif 'month' in unit:
                    return now - relativedelta(months=value)
                elif 'week' in unit:
                    return now - relativedelta(weeks=value)
                elif 'day' in unit:
                    return now - relativedelta(days=value)
                elif 'hour' in unit:
                    return now - relativedelta(hours=value)
                elif 'minute' in unit:
                    return now - relativedelta(minutes=value)
                elif 'second' in unit:
                    return now - relativedelta(seconds=value)
            
            # Handle special cases like "a day ago" or "an hour ago"
            if text.startswith('a ') or text.startswith('an '):
                unit = text.split(' ')[1]
                
                if 'year' in unit:
                    return now - relativedelta(years=1)
                elif 'month' in unit:
                    return now - relativedelta(months=1)
                elif 'week' in unit:
                    return now - relativedelta(weeks=1)
                elif 'day' in unit:
                    return now - relativedelta(days=1)
                elif 'hour' in unit:
                    return now - relativedelta(hours=1)
                elif 'minute' in unit:
                    return now - relativedelta(minutes=1)
                elif 'second' in unit:
                    return now - relativedelta(seconds=1)
                    
            logger.warning(f"Could not parse relative time: {relative_time_text}")
            return None
        except Exception as e:
            logger.error(f"Error parsing relative time '{relative_time_text}': {e}")
            return None
            
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
    
    async def _get_page_soup(self, any_url):
        """
        Retrieves page content using BrowserManager and converts to BeautifulSoup.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if the request fails
        """
        try:
            logger.info(f"Fetching page with browser: {any_url}")
            html_content = await self.browser_manager.get_page_content(any_url)
            
            if html_content:
                logger.info(f"Successfully loaded: {any_url}")
                # Save a copy for debugging
                self._save_debug_html(html_content, f"debug_page/debug_browser_{any_url.split('/')[-2]}.html")
                return BeautifulSoup(html_content, 'html.parser')
            else:
                logger.error(f"Failed to load page: {any_url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {any_url}: {str(e)}", exc_info=True)
            return None
            
    async def _extract_full_description(self, video_url):
        """
        Extracts the full description and hashtags from a video page.
        
        Args:
            video_url: URL of the video page
            
        Returns:
            Full description text or None if extraction fails
        """
        try:
            logger.info(f"Extracting full description from: {video_url}")
            soup = await self._get_page_soup(video_url)
            
            if not soup:
                return None
                
            # Try different approaches to find the full description
            # First try: check for description in .info2 div with h1
            info2_div = soup.select_one('.info2')
            if info2_div:
                h1_element = info2_div.select_one('h1')
                if h1_element:
                    full_text = h1_element.text.strip()
                    logger.info(f"Found full description in video page: '{full_text[:50]}...' (length: {len(full_text)})")
                    return full_text
                else:
                    logger.warning("info2 div found but no h1 element inside")
            else:
                logger.warning("No info2 div found on video page")
            
            # Try alternative selectors if info2 didn't work
            # Sometimes the description might be in other locations
            alternative_selectors = [
                '.video-description h1',
                '.video-info h1',
                '.content h1',
                'h1.description'
            ]
            
            for selector in alternative_selectors:
                element = soup.select_one(selector)
                if element:
                    full_text = element.text.strip()
                    logger.info(f"Found description using selector '{selector}': '{full_text[:50]}...'")
                    return full_text
            
            logger.error("Could not find description in any known location")
            return None
        except Exception as e:
            logger.error(f"Error extracting full description: {e}")
            return None
    
    async def enrich_video_descriptions(self, videos, batch_size=5, max_concurrent=3):
        """
        Enriches videos with full descriptions by visiting individual video pages.
        Only processes videos that have the 'needs_enrichment' flag set to True.
        
        Args:
            videos: List of video dictionaries to enrich
            batch_size: Number of videos to process in each batch
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            Number of successfully enriched videos
        """
        # Filter videos that need enrichment
        videos_to_enrich = [v for v in videos if v.get('needs_enrichment', False)]
        
        if not videos_to_enrich:
            logger.info("No videos need enrichment")
            return 0
            
        logger.info(f"Enriching {len(videos_to_enrich)} videos with full descriptions")
        
        enriched_count = 0
        
        # Process videos in batches
        for i in range(0, len(videos_to_enrich), batch_size):
            batch = videos_to_enrich[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} videos)")
            
            # Create tasks for concurrent processing
            tasks = []
            for video in batch:
                task = self._enrich_single_video(video)
                tasks.append(task)
            
            # Run tasks with limited concurrency
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def bounded_task(task):
                async with semaphore:
                    return await task
            
            bounded_tasks = [bounded_task(task) for task in tasks]
            results = await asyncio.gather(*bounded_tasks, return_exceptions=True)
            
            # Count successful enrichments
            for result in results:
                if result is True:
                    enriched_count += 1
                elif isinstance(result, Exception):
                    logger.error(f"Error during enrichment: {result}")
            
            # Add delay between batches to avoid rate limiting
            if i + batch_size < len(videos_to_enrich):
                await asyncio.sleep(self.delay)
        
        logger.info(f"Successfully enriched {enriched_count}/{len(videos_to_enrich)} videos")
        return enriched_count
    
    async def _enrich_single_video(self, video):
        """
        Enriches a single video with full description from its page.
        
        Args:
            video: Video dictionary to enrich (modified in place)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            video_url = video.get('url')
            if not video_url:
                logger.warning(f"No URL for video {video.get('video_id')}")
                return False
                
            logger.debug(f"Enriching video: {video_url}")
            
            # Get the full description from the video page
            full_text = await self._extract_full_description(video_url)
            
            if full_text:
                # Update the video info
                video['description_and_hashtags'] = full_text
                video['needs_enrichment'] = False
                
                # Extract hashtags from the full text
                hashtags = re.findall(r'#(\w+)', full_text)
                video['hashtags'] = hashtags
                video['hashtags_str'] = ','.join(hashtags) if hashtags else ''
                
                logger.info(f"Successfully enriched video {video.get('video_id')}:")
                logger.info(f"  - Full description: '{full_text[:50]}...' (length: {len(full_text)})")
                logger.info(f"  - Hashtags found: {hashtags}")
                return True
            else:
                logger.warning(f"Could not extract full description for video {video.get('video_id')}")
                video['needs_enrichment'] = False  # Mark as processed even if failed
                return False
                
        except Exception as e:
            logger.error(f"Error enriching video {video.get('video_id')}: {e}")
            video['needs_enrichment'] = False  # Mark as processed even if failed
            return False
    
    async def scrape_hashtag(self, hashtag, max_pages=1, enrich_descriptions=True):
        """
        Scrapes videos from a hashtag page using a headless browser.
        
        Args:
            hashtag: Hashtag to search for (without # symbol)
            max_pages: Maximum number of pages to scrape
            enrich_descriptions: Whether to enrich truncated descriptions (default: True)
            
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
        hash_url = f"{self.BASE_URL}/hash/{hashtag}/"
        
        while current_page <= max_pages:
            logger.info(f"Scraping page {current_page}/{max_pages}")
            
            # Request the page with browser
            soup = await self._get_page_soup(hash_url)
            if not soup:
                logger.error("Failed to get the page")
                break
            
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
            for idx, video_element in enumerate(video_elements):
                try:
                    # Save first video element for debugging
                    if idx == 0:
                        self._save_debug_html(str(video_element), 'debug_video_element.html')
                        logger.info("Saved first video element structure to debug_video_element.html")
                    
                    video_info = await self._extract_video_info(video_element)
                    if video_info:
                        results.append(video_info)
                        videos_extracted += 1
                except Exception as e:
                    logger.error(f"Error extracting video info: {e}")
            
            logger.info(f"Extracted {videos_extracted} videos from page {current_page}")
            with open('video3_elements_debug.html', 'w', encoding='utf-8') as f:
                f.write(str(results))
                logger.info("Saved video elements for debugging")

            # Save the current page HTML for debugging
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
        
        # Phase 2: Enrich videos with full descriptions if needed
        if enrich_descriptions and results:
            videos_needing_enrichment = sum(1 for v in results if v.get('needs_enrichment', False))
            if videos_needing_enrichment > 0:
                logger.info(f"{videos_needing_enrichment} videos need description enrichment")
                await self.enrich_video_descriptions(results)
            else:
                logger.info("All videos have complete descriptions, no enrichment needed")
        
        # Remove the needs_enrichment flag from results before returning
        for video in results:
            video.pop('needs_enrichment', None)
        
        return results
    
    async def _extract_video_info(self, video_element):
        """
        Extracts video information from a video card element.
        Only extracts data from the hashtag page without making additional requests.
        
        Args:
            video_element: BeautifulSoup element representing a video card
            
        Returns:
            Dictionary with video information or None if extraction fails
        """
        # Get current time for scraping timestamp
        now = datetime.datetime.now()
        
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
            'author': '',
            'author_url': '',
            'description_and_hashtags': '',
            'hashtags': [],
            'scrape_time': now.strftime('%Y-%m-%d %H:%M:%S'),
            'estimated_release_time': '',
            'needs_enrichment': False  # Flag to indicate if full description is needed
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
            
            # Extract description from info3 div - it's in a span inside the video link
            if not video_info['description_and_hashtags']:
                info_div = video_element.select_one('.info3')
                if info_div:
                    # Find the video link (not the author link)
                    for link in info_div.select('a'):
                        # Skip author links
                        if link.parent and link.parent.get('class') == ['author-name']:
                            continue
                        # Check if this link has a span with text
                        span_element = link.select_one('span')
                        if span_element:
                            truncated_text = span_element.text.strip()
                            video_info['description_and_hashtags'] = truncated_text
                            logger.info(f"Extracted description from info3 span: '{truncated_text[:50]}...' (length: {len(truncated_text)})")
                            
                            # Check if enrichment is needed (text ends with ellipsis or is short)
                            if truncated_text.endswith('...'):
                                video_info['needs_enrichment'] = True
                                logger.info(f"Video {video_info['video_id']} needs enrichment (truncated text)")
                            else:
                                # Extract hashtags from the full text
                                hashtags = re.findall(r'#(\w+)', truncated_text)
                                video_info['hashtags'] = hashtags
                                logger.info(f"Video {video_info['video_id']} has complete description with {len(hashtags)} hashtags")
                            break
            
            # Extract author info
            author_div = video_element.select_one('.author-name')
            if author_div and author_div.select_one('a'):
                author_link = author_div.select_one('a')
                video_info['author'] = author_link.text.strip()
                video_info['author_url'] = author_link['href']
                logger.debug(f"Extracted author: {video_info['author']}")
            
            # Extract the description from info2 div if we haven't found it yet
            if not video_info['description_and_hashtags']:
                logger.debug("No description found in info3, checking info2 div")
                info2_div = video_element.select_one('.info2')
                if info2_div:
                    h1_element = info2_div.select_one('h1')
                    logger.debug(f"Found info2 div with h1: {h1_element is not None}")
                    if h1_element:
                        truncated_text = h1_element.text.strip()
                        video_info['description_and_hashtags'] = truncated_text
                        logger.info(f"Extracted description from info2 h1: '{truncated_text[:50]}...' (length: {len(truncated_text)})")
                        
                        # Check if enrichment is needed
                        if truncated_text.endswith('...'):
                            video_info['needs_enrichment'] = True
                            logger.info(f"Video {video_info['video_id']} needs enrichment (truncated in info2)")
                        else:
                            # Extract hashtags from the full text
                            hashtags = re.findall(r'#(\w+)', truncated_text)
                            video_info['hashtags'] = hashtags
                            logger.info(f"Extracted {len(hashtags)} hashtags from info2: {hashtags}")
                else:
                    logger.warning("No info2 div found in video element")
            
            # Add additional attribute for hashtags as string for CSV export
            video_info['hashtags_str'] = ','.join(video_info['hashtags']) if video_info['hashtags'] else ''
            
            # Log final extraction results
            logger.info(f"Video extraction complete for {video_info['video_id']}:")
            logger.info(f"  - Description: {'Yes' if video_info['description_and_hashtags'] else 'No'} ({len(video_info['description_and_hashtags'])} chars)")
            logger.info(f"  - Hashtags: {len(video_info['hashtags'])} found")
            logger.info(f"  - Needs enrichment: {video_info.get('needs_enrichment', False)}")
            # Extract stats (timestamp, views, likes, comments)
            stats_div = video_element.select_one('.stats')
            if stats_div:
                # Extract each stat individually by its icon class
                # This ensures we get the right metadata even if the order changes
                
                # Timestamp (clock icon)
                timestamp_element = stats_div.select_one('.fa-clock')
                if timestamp_element and timestamp_element.parent:
                    timestamp_text = timestamp_element.parent.text.strip()
                    timestamp_raw = timestamp_text.replace('fa-clock', '').strip()
                    video_info['timestamp'] = timestamp_raw
                    
                    # Convert relative timestamp to estimated release time
                    release_time = self._convert_relative_time(timestamp_raw)
                    if release_time:
                        video_info['estimated_release_time'] = release_time.strftime('%Y-%m-%d %H:%M:%S')
                    logger.debug(f"Extracted timestamp: {video_info['timestamp']} -> {video_info['estimated_release_time']}")
                
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
    
    def _save_debug_html(self, html_content, filename):
        """
        Saves HTML to a file for debugging.
        
        Args:
            html_content: HTML content as string
            filename: Name of the output file
        """
        try:
            # Create debug directory if needed
            debug_dir = os.path.dirname(filename)
            if debug_dir and not os.path.exists(debug_dir):
                os.makedirs(debug_dir)
                
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(str(html_content))
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
        
        # Convert hashtags list to a comma-separated string
        if 'hashtags' in df.columns:
            df['hashtags_str'] = df['hashtags'].apply(lambda x: ','.join(x) if isinstance(x, list) else '')
        
        # Define column order with priority columns first
        priority_columns = [
            'url',                      # Video URL
            'video_id',                 # Extracted ID
            'scrape_time',              # Time of scraping
            'timestamp',                # Raw timestamp text (e.g., "3 days ago")
            'estimated_release_time',   # Estimated datetime of video release
            'views_raw',                # Raw views value
            'likes_raw',                # Raw likes value
            'comments_raw',             # Raw comments value
            'views',                    # Numeric views
            'likes',                    # Numeric likes
            'comments',                 # Numeric comments
            'author',                   # Author name
            'author_url',               # Author profile URL
            'description_and_hashtags', # Full comment text with hashtags
            'hashtags_str'              # Comma-separated hashtags
        ]
        
        # Reorder columns to match priority (if they exist)
        columns = [col for col in priority_columns if col in df.columns]
        
        # Add any remaining columns
        for col in df.columns:
            if col not in columns and col != 'hashtags':  # Exclude the original hashtags list
                columns.append(col)
                
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


async def main_async():
    """Async command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced TikTok Scraper with Browser Support')
    parser.add_argument('--hashtag', required=True, help='Hashtag to scrape (without # symbol)')
    parser.add_argument('--output', default='data/videos.csv', help='Output CSV file path')
    parser.add_argument('--max-pages', type=int, default=1, help='Maximum number of pages to scrape')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds')
    parser.add_argument('--no-enrich', action='store_true', help='Skip description enrichment phase')
    
    args = parser.parse_args()
    
    # Create and run the enhanced scraper
    scraper = EnhancedSocialScraper(delay_between_requests=args.delay)
    videos = await scraper.scrape_hashtag(
        args.hashtag, 
        max_pages=args.max_pages,
        enrich_descriptions=not args.no_enrich
    )
    
    if videos:
        scraper.save_to_csv(videos, args.output)
        print(f"Scraped {len(videos)} videos and saved to {args.output}")
    else:
        print("No videos found.")


def main():
    """Simple wrapper for async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()