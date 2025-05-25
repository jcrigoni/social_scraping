"""
Browser utilities for web scraper.
Handles browser initialization, page navigation, and interaction.
"""

import asyncio
from logger import setup_logger
from datetime import datetime
from playwright.async_api import async_playwright
from config import SCRAPER_CONFIG

logger = setup_logger('browser')

class BrowserManager:
    """Manages browser interactions for web scraping"""
    
    def __init__(self):
        """Initialize the browser manager"""
        self.last_request_time = {}
    
    async def _check_rate_limit(self, domain):
        """
        Implements rate limiting per domain
        
        Args:
            domain: The domain to check rate limits for
        """
        now = datetime.now().timestamp()
        if domain in self.last_request_time:
            time_passed = now - self.last_request_time[domain]
            if time_passed < SCRAPER_CONFIG['DELAY_BETWEEN_REQUESTS']:
                await asyncio.sleep(
                    SCRAPER_CONFIG['DELAY_BETWEEN_REQUESTS'] - time_passed
                )
        self.last_request_time[domain] = now

    async def _handle_page_load(self, page, url):
        """
        Handles page loading with retries
        
        Args:
            page: Playwright page object
            url: URL to load
            
        Returns:
            True if the page loaded successfully, False otherwise
        """
        for attempt in range(SCRAPER_CONFIG['MAX_RETRIES']):
            try:
                logger.info(f"Attempting to load {url} (attempt {attempt + 1})")
                await page.goto(
                    url, 
                    timeout=SCRAPER_CONFIG['PAGE_LOAD_TIMEOUT']
                )
                return True
            except Exception as e:
                logger.error(
                    f"Failed to load {url} on attempt {attempt + 1}: {str(e)}"
                )
                if attempt < SCRAPER_CONFIG['MAX_RETRIES'] - 1:
                    await asyncio.sleep(SCRAPER_CONFIG['RETRY_DELAY'])
                else:
                    return False

    async def _handle_cookies_popup(self, page):
        """
        Handles common cookie consent popups
        
        Args:
            page: Playwright page object
        """
        try:
            # Add common cookie consent button selectors
            common_selectors = [
                'button[id*="accept"]',
                'button[class*="accept"]',
                'button[id*="cookie"]',
                # Add more selectors as needed
            ]
            
            for selector in common_selectors:
                try:
                    await page.click(selector, timeout=5000)
                    logger.debug("Handled cookie popup")
                    break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Cookie popup handling failed: {str(e)}")
    
    async def get_page_content(self, url):
        """
        Retrieves page content from the specified URL
        
        Args:
            url: URL to fetch content from
            
        Returns:
            HTML content of the page
        """
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=SCRAPER_CONFIG['HEADLESS']
                )
                context = await browser.new_context(
                    user_agent=SCRAPER_CONFIG['USER_AGENT']
                )
                page = await context.new_page()
                
                # Rate limiting
                domain = url.split('/')[2]
                await self._check_rate_limit(domain)
                
                # Load page
                logger.info(f"Starting fetch of {url}")
                if not await self._handle_page_load(page, url):
                    raise Exception("Failed to load page after all retries")
                
                # Handle cookie popups
                await self._handle_cookies_popup(page)
                
                # Get HTML content
                content = await page.content()
                
                await browser.close()
                return content
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}", exc_info=True)
            raise