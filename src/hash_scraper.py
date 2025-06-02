"""
Hash page scraper that extracts basic video data from hashtag pages.
This is the first stage of a two-stage scraping process.
"""

import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import datetime
import json
from dateutil.relativedelta import relativedelta
from logger import setup_logger
from browser import BrowserManager
from config import SCRAPER_CONFIG

logger = setup_logger('hash_scraper')

class HashPageScraper:
    """
    Scraper for hashtag pages that extracts basic video metadata.
    Uses Load More button functionality with AJAX requests.
    """
    
    BASE_URL = SCRAPER_CONFIG['BASE_URL']
    
    def __init__(self, delay_between_requests=2.0):
        """
        Initialize the hash page scraper.
        
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
        id_match = re.search(r'(\d+)(?:/)?$', url)
        if id_match:
            return id_match.group(1)
        return ""
    
    def _convert_relative_time(self, relative_time_text):
        """
        Converts a relative time expression to a datetime object.
        
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
            match = re.match(r'(\d+)\s+([a-z]+)', text)
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                
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
            text: Text containing a number
            
        Returns:
            Extracted numeric value as integer
        """
        if not text:
            return 0
            
        text = re.sub(r'[^\d\.KkMm]', '', text.strip().lower())
        
        try:
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            elif text:
                text = text.replace(',', '')
                return int(float(text))
            return 0
        except ValueError:
            logger.warning(f"Could not convert to number: {text}")
            return 0
    
    async def _get_page_soup(self, url):
        """
        Retrieves page content using BrowserManager and converts to BeautifulSoup.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if the request fails
        """
        try:
            logger.info(f"Fetching page with browser: {url}")
            html_content = await self.browser_manager.get_page_content(url)
            
            if html_content:
                logger.info(f"Successfully loaded: {url}")
                self._save_debug_html(html_content, f"debug_page/debug_hash_{url.split('/')[-2]}.html")
                return BeautifulSoup(html_content, 'html.parser')
            else:
                logger.error(f"Failed to load page: {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}", exc_info=True)
            return None
    
    async def _find_load_more_button(self, soup):
        """
        Finds the Load More button and extracts its parameters for AJAX requests.
        
        Args:
            soup: BeautifulSoup object to analyze
            
        Returns:
            Dictionary with button attributes or None if not found
        """
        button_selectors = [
            '#hash_load_more',
            '#paging a.btn', 
            'a.load-more-btn',
            'a.js-load-more',
            'button.load-more',
            '.load-more-container a',
            '.pagination a.next',
            '.more-videos-btn',
            '.show-more-btn',
            '#load-more',
            '.load-more',
            'button[data-load-more]',
            '[data-action="load-more"]'
        ]
        
        for selector in button_selectors:
            load_more = soup.select_one(selector)
            if load_more:
                data_attrs = {}
                for attr_name, attr_value in load_more.attrs.items():
                    if attr_name.startswith('data-') or attr_name in ['href', 'onclick']:
                        data_attrs[attr_name] = attr_value
                
                logger.info(f"Found Load More button with selector '{selector}': {data_attrs}")
                return data_attrs
        
        logger.info("No Load More button found")
        return None

    async def _load_more_content(self, page, load_more_data):
        """
        Clicks the Load More button to load additional content via AJAX.
        
        Args:
            page: Playwright page object
            load_more_data: Dictionary with button parameters
            
        Returns:
            BeautifulSoup object with updated page content or None if failed
        """
        try:
            # Check for any overlays that might be blocking clicks
            overlay_selectors = [
                '#qc-cmp2-container',
                '.qc-cmp2-container',
                '.qc-cmp-cleanslate',
                '[class*="cookie"]',
                '[class*="consent"]'
            ]
            
            for overlay_selector in overlay_selectors:
                try:
                    overlay = await page.query_selector(overlay_selector)
                    if overlay and await overlay.is_visible():
                        logger.warning(f"Found blocking overlay: {overlay_selector}, trying to dismiss...")
                        # Try to handle the cookie popup again
                        await self.browser_manager._handle_cookies_popup(page)
                        break
                except:
                    continue
            
            # Find the Load More button on the page
            button_selectors = [
                '#hash_load_more',
                '#paging a.btn', 
                'a.load-more-btn',
                'a.js-load-more',
                'button.load-more',
                '.load-more-container a',
                '.pagination a.next',
                '.more-videos-btn',
                '.show-more-btn',
                '#load-more',
                '.load-more',
                'button[data-load-more]',
                '[data-action="load-more"]'
            ]
            
            load_more_element = None
            for selector in button_selectors:
                try:
                    load_more_element = await page.wait_for_selector(selector, timeout=5000)
                    if load_more_element and await load_more_element.is_visible():
                        logger.info(f"Found Load More button with selector: {selector}")
                        break
                except:
                    continue
            
            if not load_more_element:
                logger.warning("No Load More button found on page")
                return None
            
            # Wait for any existing network activity to complete
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except:
                logger.warning("Page not fully idle, proceeding anyway")
            
            # Add random human-like delays and actions before clicking
            await asyncio.sleep(2 + (asyncio.get_event_loop().time() % 1))  # Random 2-3 second delay
            
            # Simulate human behavior: scroll, move mouse, etc.
            await page.mouse.move(100, 200)
            await asyncio.sleep(0.5)
            
            # Scroll the button into view to make sure it's clickable
            await load_more_element.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            # Move mouse near the button
            box = await load_more_element.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                await asyncio.sleep(0.5)
            
            # Count current video elements before clicking
            current_videos = await page.query_selector_all('div.thumb:not(.display-flex-semi)')
            current_count = len(current_videos)
            logger.info(f"Current video count before Load More: {current_count}")
            
            # Set up a promise to wait for new content to appear
            # We'll wait for the video count to increase
            async def wait_for_new_content():
                for i in range(30):  # Wait up to 30 seconds
                    await asyncio.sleep(1)
                    
                    # Check if #thumbs container still exists
                    thumbs_container = await page.query_selector('#thumbs')
                    if not thumbs_container:
                        logger.error(f"#thumbs container disappeared after {i+1} seconds!")
                        # Save current page HTML for debugging
                        current_html = await page.content()
                        self._save_debug_html(current_html, f"debug_page/debug_missing_thumbs_{i+1}s.html")
                        return False
                    
                    new_videos = await page.query_selector_all('div.thumb:not(.display-flex-semi)')
                    new_count = len(new_videos)
                    
                    if i % 5 == 0:  # Log every 5 seconds
                        logger.debug(f"Waiting for content... {i+1}s - Videos: {new_count} (need >{current_count})")
                    
                    if new_count > current_count:
                        logger.info(f"New video count after Load More: {new_count} (added {new_count - current_count})")
                        return True
                return False
            
            # Click the Load More button
            logger.info("Clicking Load More button...")
            try:
                await load_more_element.click(timeout=5000)
                logger.info("Load More button clicked successfully")
            except Exception as click_error:
                logger.warning(f"Normal click failed: {click_error}, trying force click...")
                try:
                    await load_more_element.click(force=True, timeout=5000)
                    logger.info("Force click succeeded")
                except Exception as force_error:
                    logger.error(f"Force click also failed: {force_error}")
                    return None
            
            # Wait for new content to appear
            logger.info("Waiting for new content to load...")
            content_loaded = await wait_for_new_content()
            
            if not content_loaded:
                logger.warning("No new content appeared after clicking Load More")
                # Try alternative approach using the data attributes for AJAX request
                logger.info("Attempting alternative AJAX approach using data attributes...")
                success = await self._try_ajax_load_more(page, load_more_data)
                if success:
                    # Wait a bit more for content to load
                    await asyncio.sleep(3)
                    content_loaded = await wait_for_new_content()
            
            if content_loaded:
                logger.info("New content detected, Load More was successful")
            else:
                logger.error("Load More failed - no new content detected")
                # Save page state for debugging
                debug_html = await page.content()
                self._save_debug_html(debug_html, "debug_page/debug_failed_load_more.html")
            
            # Final check: verify #thumbs container still exists
            final_thumbs = await page.query_selector('#thumbs')
            if not final_thumbs:
                logger.error("CRITICAL: #thumbs container missing after Load More attempt!")
                debug_html = await page.content()
                self._save_debug_html(debug_html, "debug_page/debug_critical_missing_thumbs.html")
                return None
            
            # Get the updated page content
            html_content = await page.content()
            
            if html_content:
                soup = BeautifulSoup(html_content, 'html.parser')
                # Verify the soup contains the thumbs container
                if soup.select_one('#thumbs'):
                    logger.info("Successfully loaded content and verified #thumbs container exists")
                    return soup
                else:
                    logger.error("HTML retrieved but #thumbs container missing in parsed content")
                    return None
            else:
                logger.warning("Failed to get updated content after clicking Load More")
                return None
                
        except Exception as e:
            logger.error(f"Error clicking Load More button: {e}")
            return None

    async def _try_ajax_load_more(self, page, data_attrs):
        """
        Attempts to trigger the Load More functionality using JavaScript and the data attributes.
        
        Args:
            page: Playwright page object
            data_attrs: Dictionary with Load More button data attributes
            
        Returns:
            True if the AJAX request was triggered successfully, False otherwise
        """
        try:
            # Extract the necessary data from the button attributes
            hash_value = data_attrs.get('data-hash', '')
            data_id = data_attrs.get('data-id', '')
            page_num = data_attrs.get('data-page', '2')
            cursor = data_attrs.get('data-cursor', '20')
            data_x = data_attrs.get('data-x', '')
            
            logger.info(f"Trying AJAX with hash={hash_value}, page={page_num}, cursor={cursor}")
            
            # Construct the AJAX URL based on typical patterns
            ajax_url = f"{self.BASE_URL}/hash_load_more"
            
            # Use page.evaluate to make the AJAX request from within the page context
            js_code = f"""
            async () => {{
                try {{
                    console.log('Starting AJAX Load More request...');
                    const formData = new FormData();
                    formData.append('hash', '{hash_value}');
                    formData.append('id', '{data_id}');
                    formData.append('page', '{page_num}');
                    formData.append('cursor', '{cursor}');
                    formData.append('x', '{data_x}');
                    
                    console.log('FormData prepared:', {{
                        hash: '{hash_value}',
                        id: '{data_id}',
                        page: '{page_num}',
                        cursor: '{cursor}',
                        x: '{data_x}'
                    }});
                    
                    const response = await fetch('{ajax_url}', {{
                        method: 'POST',
                        body: formData,
                        headers: {{
                            'X-Requested-With': 'XMLHttpRequest'
                        }}
                    }});
                    
                    console.log('Response status:', response.status);
                    console.log('Response ok:', response.ok);
                    
                    if (response.ok) {{
                        const result = await response.text();
                        console.log('Response length:', result.length);
                        console.log('Response preview:', result.substring(0, 200));
                        
                        // Try to append the result to the thumbs container
                        const thumbsContainer = document.getElementById('thumbs');
                        if (thumbsContainer && result && result.length > 50) {{
                            console.log('Appending content to thumbs container...');
                            thumbsContainer.insertAdjacentHTML('beforeend', result);
                            return true;
                        }} else {{
                            console.error('Cannot append content:', {{
                                thumbsContainer: !!thumbsContainer,
                                resultLength: result ? result.length : 0
                            }});
                            return false;
                        }}
                    }} else {{
                        console.error('Response not ok:', response.status, response.statusText);
                        return false;
                    }}
                }} catch (error) {{
                    console.error('AJAX request failed:', error);
                    return false;
                }}
            }}
            """
            
            result = await page.evaluate(js_code)
            
            if result:
                logger.info("AJAX Load More request successful")
                return True
            else:
                logger.warning("AJAX Load More request failed or returned no content")
                return False
                
        except Exception as e:
            logger.error(f"Error in AJAX Load More fallback: {e}")
            return False

    async def _extract_video_info(self, video_element):
        """
        Extracts basic video information from a video card element.
        
        Args:
            video_element: BeautifulSoup element representing a video card
            
        Returns:
            Dictionary with video information or None if extraction fails
        """
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
            'needs_enrichment': False
        }
        
        try:
            # Check if this is an ad element
            if video_element.get('class') and 'display-flex-semi' in video_element.get('class', []):
                logger.debug("Skipping advertisement element")
                return None
                
            # Extract video URL from overlay links
            overlay_links = [a for a in video_element.select('a') 
                           if '/video/' in a.get('href', '') and ('overlay-s' in a.get('class', []) 
                                                             or a.select_one('.overlay-s'))]
            if overlay_links:
                video_url = overlay_links[0]['href']
                video_info['url'] = video_url
                video_info['video_id'] = self._extract_video_id(video_url)
                logger.debug(f"Extracted video URL from overlay: {video_url}")
            
            # Fallback: check for video links in info3 div
            if not video_info['url']:
                info_div = video_element.select_one('.info3')
                if info_div:
                    video_links = [a for a in info_div.select('a') 
                                 if a.parent.get('class') != ['author-name'] and 
                                    '/video/' in a.get('href', '')]
                    
                    if video_links:
                        video_url = video_links[0]['href']
                        video_info['url'] = video_url
                        video_info['video_id'] = self._extract_video_id(video_url)
                        logger.debug(f"Extracted video URL from info3: {video_url}")
            
            # Extract description from info3 div
            if not video_info['description_and_hashtags']:
                info_div = video_element.select_one('.info3')
                if info_div:
                    for link in info_div.select('a'):
                        if link.parent and link.parent.get('class') == ['author-name']:
                            continue
                        span_element = link.select_one('span')
                        if span_element:
                            truncated_text = span_element.text.strip()
                            video_info['description_and_hashtags'] = truncated_text
                            logger.debug(f"Extracted description: '{truncated_text[:50]}...'")
                            
                            # Check if enrichment is needed
                            if truncated_text.endswith('...'):
                                video_info['needs_enrichment'] = True
                                logger.debug(f"Video {video_info['video_id']} needs enrichment")
                            else:
                                hashtags = re.findall(r'#(\w+)', truncated_text)
                                video_info['hashtags'] = hashtags
                            break
            
            # Extract author info
            author_div = video_element.select_one('.author-name')
            if author_div and author_div.select_one('a'):
                author_link = author_div.select_one('a')
                video_info['author'] = author_link.text.strip()
                video_info['author_url'] = author_link['href']
                logger.debug(f"Extracted author: {video_info['author']}")
            
            # Extract description from info2 div if not found yet
            if not video_info['description_and_hashtags']:
                info2_div = video_element.select_one('.info2')
                if info2_div:
                    h1_element = info2_div.select_one('h1')
                    if h1_element:
                        truncated_text = h1_element.text.strip()
                        video_info['description_and_hashtags'] = truncated_text
                        logger.debug(f"Extracted description from info2: '{truncated_text[:50]}...'")
                        
                        if truncated_text.endswith('...'):
                            video_info['needs_enrichment'] = True
                        else:
                            hashtags = re.findall(r'#(\w+)', truncated_text)
                            video_info['hashtags'] = hashtags
            
            # Add hashtags as string for CSV export
            video_info['hashtags_str'] = ','.join(video_info['hashtags']) if video_info['hashtags'] else ''
            
            # Extract stats (timestamp, views, likes, comments)
            stats_div = video_element.select_one('.stats')
            if stats_div:
                # Timestamp (clock icon)
                timestamp_element = stats_div.select_one('.fa-clock')
                if timestamp_element and timestamp_element.parent:
                    timestamp_text = timestamp_element.parent.text.strip()
                    timestamp_raw = timestamp_text.replace('fa-clock', '').strip()
                    video_info['timestamp'] = timestamp_raw
                    
                    release_time = self._convert_relative_time(timestamp_raw)
                    if release_time:
                        video_info['estimated_release_time'] = release_time.strftime('%Y-%m-%d %H:%M:%S')
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

    async def scrape_hashtag_page(self, hashtag, max_loads=5):
        """
        Scrapes videos from a hashtag page using Load More functionality.
        
        Args:
            hashtag: Hashtag to search for (without # symbol)
            max_loads: Maximum number of Load More operations to perform
            
        Returns:
            List of dictionaries with basic video information
        """
        if hashtag.startswith('#'):
            hashtag = hashtag[1:]
        
        logger.info(f"Scraping hashtag page: {hashtag}, max loads: {max_loads}")
        
        results = []
        
        # Build the URL
        hash_url = f"{self.BASE_URL}/hash/{hashtag}/"
        
        try:
            # Use browser manager to get a page object for better Load More handling
            async with await self.browser_manager.get_browser() as browser:
                context = await browser.new_context(
                    user_agent=SCRAPER_CONFIG['USER_AGENT'],
                    viewport={'width': 1920, 'height': 1080},
                    extra_http_headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1'
                    }
                )
                page = await context.new_page()
                
                # Add script to hide automation indicators
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                    
                    window.chrome = {
                        runtime: {},
                    };
                """)
                
                # Navigate to the hashtag page
                logger.info(f"Navigating to: {hash_url}")
                await page.goto(hash_url, wait_until='networkidle')
                
                # Handle cookie popups
                await self.browser_manager._handle_cookies_popup(page)
                
                # Set up console logging to capture browser messages
                page.on("console", lambda msg: logger.info(f"Browser console: {msg.text}"))
                page.on("pageerror", lambda err: logger.error(f"Browser error: {err}"))
                
                # Get initial page content
                html_content = await page.content()
                current_soup = BeautifulSoup(html_content, 'html.parser')
                
                # Save initial page for debugging
                self._save_debug_html(html_content, f"debug_page/debug_hash_initial_{hashtag}.html")
                
                load_count = 0
                
                while load_count <= max_loads:
                    logger.info(f"Processing load {load_count + 1}/{max_loads + 1}")
                    
                    # Find the container with video cards
                    thumbs_container = current_soup.select_one('#thumbs')
                    if not thumbs_container:
                        logger.error(f"Could not find #thumbs container on load {load_count + 1}")
                        
                        # Wait a moment and try to get fresh page content
                        logger.info("Waiting 3 seconds and trying to get fresh page content...")
                        await asyncio.sleep(3)
                        fresh_html = await page.content()
                        fresh_soup = BeautifulSoup(fresh_html, 'html.parser')
                        fresh_thumbs = fresh_soup.select_one('#thumbs')
                        
                        if fresh_thumbs:
                            logger.info("Found #thumbs container after refresh, continuing...")
                            current_soup = fresh_soup
                            thumbs_container = fresh_thumbs
                        else:
                            # Save current page state for debugging
                            self._save_debug_html(fresh_html, f"debug_page/debug_no_thumbs_load_{load_count + 1}.html")
                            
                            # Try to find alternative containers
                            alternative_containers = fresh_soup.select('div[id*="thumb"], div[class*="thumb"], div[class*="video"], main, .content')
                            if alternative_containers:
                                logger.info(f"Found {len(alternative_containers)} alternative containers, trying to continue...")
                                # Log the structure for debugging
                                container_info = [(elem.name, elem.get('id'), elem.get('class')) for elem in alternative_containers[:5]]
                                logger.info(f"Alternative containers: {container_info}")
                            else:
                                logger.error("No alternative containers found either, stopping scraping")
                            
                            break
                        
                    # Find all video cards, excluding ads
                    video_elements = []
                    for element in thumbs_container.select('div.thumb'):
                        if 'display-flex-semi' not in element.get('class', []):
                            video_elements.append(element)
                            
                    if not video_elements:
                        logger.warning("No video elements found")
                        break
                        
                    logger.info(f"Found {len(video_elements)} video elements")
                    
                    # Extract data from each video card
                    videos_extracted = 0
                    for idx, video_element in enumerate(video_elements):
                        try:
                            # Save first video element for debugging
                            if idx == 0 and load_count == 0:
                                self._save_debug_html(str(video_element), 'debug_video_element.html')
                            
                            video_info = await self._extract_video_info(video_element)
                            if video_info:
                                # Check if we already have this video (avoid duplicates)
                                existing_ids = {v.get('video_id') for v in results}
                                if video_info['video_id'] not in existing_ids:
                                    results.append(video_info)
                                    videos_extracted += 1
                        except Exception as e:
                            logger.error(f"Error extracting video info: {e}")
                    
                    logger.info(f"Extracted {videos_extracted} new videos from load {load_count + 1}")
                    
                    # Check if we should continue loading more
                    if load_count >= max_loads:
                        logger.info(f"Reached maximum loads ({max_loads}), stopping")
                        break
                        
                    # Find and click Load More button
                    load_more_data = await self._find_load_more_button(current_soup)
                    if not load_more_data:
                        logger.info("No Load More button found, stopping")
                        break
                    
                    # Load more content by clicking the button
                    logger.info(f"Attempting Load More operation {load_count + 1}...")
                    new_soup = await self._load_more_content(page, load_more_data)
                    if not new_soup:
                        logger.warning(f"Failed to load more content on attempt {load_count + 1}")
                        logger.info("This is likely due to anti-bot protection (403 Forbidden)")
                        logger.info("Continuing with videos already collected...")
                        break
                        
                    current_soup = new_soup
                    load_count += 1
                    
                    # Add delay between loads to be more respectful
                    delay_time = self.delay + (load_count * 0.5)  # Increase delay with each load
                    logger.info(f"Waiting {delay_time:.1f} seconds before next operation...")
                    await asyncio.sleep(delay_time)
                
                await page.close()
                await context.close()
        
        except Exception as e:
            logger.error(f"Error during hashtag scraping: {e}")
        
        logger.info(f"Scraped {len(results)} total videos from hashtag page")
        return results
    
    def _save_debug_html(self, html_content, filename):
        """
        Saves HTML to a file for debugging.
        
        Args:
            html_content: HTML content as string
            filename: Name of the output file
        """
        try:
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
        Saves the basic video data to a CSV file.
        
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
        
        # Define column order
        priority_columns = [
            'url',
            'video_id',
            'scrape_time',
            'timestamp',
            'estimated_release_time',
            'views_raw',
            'likes_raw',
            'comments_raw',
            'views',
            'likes',
            'comments',
            'author',
            'author_url',
            'description_and_hashtags',
            'hashtags_str',
            'needs_enrichment'
        ]
        
        # Reorder columns
        columns = [col for col in priority_columns if col in df.columns]
        for col in df.columns:
            if col not in columns and col != 'hashtags':
                columns.append(col)
                
        df = df[columns]
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(videos)} videos to {output_file}")
        
        # Log stats
        logger.info(f"- Total videos: {len(videos)}")
        needs_enrichment = sum(1 for v in videos if v.get('needs_enrichment', False))
        logger.info(f"- Videos needing enrichment: {needs_enrichment}")
        if 'views' in df.columns:
            logger.info(f"- Average views: {df['views'].mean():.1f}")


async def main_async():
    """Async command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hash Page Scraper - Stage 1 of TikTok scraping')
    parser.add_argument('--hashtag', required=True, help='Hashtag to scrape (without # symbol)')
    parser.add_argument('--output', default='data/hash_videos.csv', help='Output CSV file path')
    parser.add_argument('--max-loads', type=int, default=5, help='Maximum number of Load More operations')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between requests in seconds')
    
    args = parser.parse_args()
    
    # Create and run the hash scraper
    scraper = HashPageScraper(delay_between_requests=args.delay)
    videos = await scraper.scrape_hashtag_page(
        args.hashtag, 
        max_loads=args.max_loads
    )
    
    if videos:
        scraper.save_to_csv(videos, args.output)
        print(f"Scraped {len(videos)} videos and saved to {args.output}")
        needs_enrichment = sum(1 for v in videos if v.get('needs_enrichment', False))
        print(f"{needs_enrichment} videos need enrichment (stage 2)")
    else:
        print("No videos found.")


def main():
    """Simple wrapper for async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()