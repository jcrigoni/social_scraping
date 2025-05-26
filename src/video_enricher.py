"""
Video enrichment script that reads basic video data from CSV and enriches with full descriptions.
This is the second stage of a two-stage scraping process.
"""

import asyncio
import pandas as pd
import re
import os
from logger import setup_logger
from browser import BrowserManager
from bs4 import BeautifulSoup

logger = setup_logger('video_enricher')

class VideoEnricher:
    """
    Enriches video data by visiting individual video pages to extract full descriptions and hashtags.
    """
    
    def __init__(self, delay_between_requests=2.0):
        """
        Initialize the video enricher.
        
        Args:
            delay_between_requests: Time in seconds to wait between requests
        """
        self.delay = delay_between_requests
        self.browser_manager = BrowserManager()
    
    async def _get_page_soup(self, url):
        """
        Retrieves page content using BrowserManager and converts to BeautifulSoup.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if the request fails
        """
        try:
            logger.info(f"Fetching video page: {url}")
            html_content = await self.browser_manager.get_page_content(url)
            
            if html_content:
                logger.debug(f"Successfully loaded: {url}")
                return BeautifulSoup(html_content, 'html.parser')
            else:
                logger.error(f"Failed to load page: {url}")
                return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
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
            logger.debug(f"Extracting full description from: {video_url}")
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
                    logger.debug(f"Found full description: '{full_text[:100]}...' (length: {len(full_text)})")
                    return full_text
                else:
                    logger.debug("info2 div found but no h1 element inside")
            else:
                logger.debug("No info2 div found on video page")
            
            # Try alternative selectors if info2 didn't work
            alternative_selectors = [
                '.video-description h1',
                '.video-info h1',
                '.content h1',
                'h1.description',
                '.info h1',
                '.description',
                '.video-text',
                '.caption'
            ]
            
            for selector in alternative_selectors:
                element = soup.select_one(selector)
                if element:
                    full_text = element.text.strip()
                    logger.debug(f"Found description using selector '{selector}': '{full_text[:100]}...'")
                    return full_text
            
            logger.warning("Could not find description in any known location")
            return None
        except Exception as e:
            logger.error(f"Error extracting full description: {e}")
            return None
    
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
                logger.info(f"  - Full description length: {len(full_text)}")
                logger.info(f"  - Hashtags found: {len(hashtags)}")
                return True
            else:
                logger.warning(f"Could not extract full description for video {video.get('video_id')}")
                video['needs_enrichment'] = False  # Mark as processed even if failed
                return False
                
        except Exception as e:
            logger.error(f"Error enriching video {video.get('video_id')}: {e}")
            video['needs_enrichment'] = False  # Mark as processed even if failed
            return False
    
    async def enrich_videos_from_csv(self, input_csv, output_csv, batch_size=5, max_concurrent=3):
        """
        Reads videos from CSV and enriches them with full descriptions.
        
        Args:
            input_csv: Path to input CSV file with basic video data
            output_csv: Path to output CSV file with enriched data
            batch_size: Number of videos to process in each batch
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            Number of successfully enriched videos
        """
        try:
            # Read the input CSV
            logger.info(f"Reading videos from: {input_csv}")
            df = pd.read_csv(input_csv)
            
            if df.empty:
                logger.warning("No videos found in input CSV")
                return 0
            
            # Convert DataFrame to list of dictionaries
            videos = df.to_dict('records')
            
            # Filter videos that need enrichment
            videos_to_enrich = [v for v in videos if v.get('needs_enrichment', False)]
            
            if not videos_to_enrich:
                logger.info("No videos need enrichment")
                # Still save the data (might have been processed already)
                self._save_to_csv(videos, output_csv)
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
            
            # Save the enriched data
            self._save_to_csv(videos, output_csv)
            
            return enriched_count
            
        except Exception as e:
            logger.error(f"Error reading or processing CSV: {e}")
            return 0
    
    def _save_to_csv(self, videos, output_file):
        """
        Saves the enriched video data to a CSV file.
        
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
        
        # Convert hashtags list to a comma-separated string if it's still a list
        if 'hashtags' in df.columns:
            df['hashtags_str'] = df['hashtags'].apply(
                lambda x: ','.join(x) if isinstance(x, list) else (x if isinstance(x, str) else '')
            )
        
        # Define column order with priority columns first
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
            'hashtags_str'
        ]
        
        # Reorder columns to match priority (if they exist)
        columns = [col for col in priority_columns if col in df.columns]
        
        # Add any remaining columns except the ones we don't want in final output
        excluded_columns = {'hashtags', 'needs_enrichment'}
        for col in df.columns:
            if col not in columns and col not in excluded_columns:
                columns.append(col)
                
        df = df[columns]
        
        # Save to CSV
        df.to_csv(output_file, index=False)
        logger.info(f"Saved {len(videos)} enriched videos to {output_file}")
        
        # Log some basic stats
        logger.info(f"- Total videos: {len(videos)}")
        if 'views' in df.columns:
            logger.info(f"- Average views: {df['views'].mean():.1f}")
        if 'likes' in df.columns:
            logger.info(f"- Average likes: {df['likes'].mean():.1f}")
        if 'description_and_hashtags' in df.columns:
            complete_descriptions = df['description_and_hashtags'].notna().sum()
            logger.info(f"- Videos with complete descriptions: {complete_descriptions}")


async def main_async():
    """Async command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Video Enricher - Stage 2 of TikTok scraping')
    parser.add_argument('--input', required=True, help='Input CSV file with basic video data')
    parser.add_argument('--output', default='data/enriched_videos.csv', help='Output CSV file path')
    parser.add_argument('--batch-size', type=int, default=5, help='Number of videos to process in each batch')
    parser.add_argument('--max-concurrent', type=int, default=3, help='Maximum number of concurrent requests')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between batches in seconds')
    
    args = parser.parse_args()
    
    # Create and run the video enricher
    enricher = VideoEnricher(delay_between_requests=args.delay)
    enriched_count = await enricher.enrich_videos_from_csv(
        args.input,
        args.output,
        batch_size=args.batch_size,
        max_concurrent=args.max_concurrent
    )
    
    if enriched_count > 0:
        print(f"Successfully enriched {enriched_count} videos and saved to {args.output}")
    else:
        print("No videos were enriched or no videos needed enrichment.")


def main():
    """Simple wrapper for async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()