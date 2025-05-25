# TikTok Scraper

A scraping tool to extract TikTok videos based on hashtags.

## Features

- Search videos by hashtag
- Filter results by date range
- Extract complete metadata (author, views, likes, comments, etc.)
- Extract full descriptions and hashtags (with enhanced scraper)
- Robust error handling and retry mechanisms
- Support for AJAX-based "Load More" functionality
- CSV output of results
- Dual implementation:
  - Simple scraper (HTTP) for quick extractions
  - Enhanced scraper (browser-based) for complete extractions

## Requirements

- Python 3.7+
- Libraries: requests, beautifulsoup4, lxml, pandas, python-dateutil
- For the enhanced scraper: playwright

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd social_scraping

# Install dependencies
pip install -r requirements.txt

# For the enhanced scraper, install playwright
pip install playwright
python -m playwright install chromium
```

## Usage

The project includes two scrapers to choose from depending on your needs:

### Simple Scraper (Fast)

```bash
# Basic usage
python src/simple_scraper.py --hashtag dance

# With date filtering
python src/simple_scraper.py --hashtag dance --start-date 2023-01-01 --end-date 2023-12-31

# Specify output file
python src/simple_scraper.py --hashtag dance --output data/dance_videos.csv

# Increase number of pages
python src/simple_scraper.py --hashtag dance --max-pages 10
```

### Enhanced Scraper (Complete)

The enhanced scraper uses a headless browser to retrieve full descriptions and all hashtags.

```bash
# Basic usage
python src/enhanced_scraper.py --hashtag dance

# With multiple pages and custom output
python src/enhanced_scraper.py --hashtag dance --max-pages 3 --output data/dance_results.csv

# Adjust delay between requests
python src/enhanced_scraper.py --hashtag dance --delay 3.0

# Disable description enrichment (faster but incomplete descriptions)
python src/enhanced_scraper.py --hashtag dance --no-enrich
```

### Available Options

#### Simple Scraper

- `--hashtag` : Hashtag to search for (required)
- `--start-date` : Start date in YYYY-MM-DD format
- `--end-date` : End date in YYYY-MM-DD format
- `--output` : Path to output CSV file (default: data/results.csv)
- `--max-pages` : Maximum number of pages to scrape (default: 5)
- `--delay` : Delay between requests in seconds (default: 2.0)

#### Enhanced Scraper

- `--hashtag` : Hashtag to search for (required)
- `--output` : Path to output CSV file (default: data/videos.csv)
- `--max-pages` : Maximum number of pages to scrape (default: 1)
- `--delay` : Delay between requests in seconds (default: 2.0)
- `--no-enrich` : Disable enrichment of truncated descriptions

### Code Example for Enhanced Scraper

```python
import asyncio
from src.enhanced_scraper import EnhancedSocialScraper

async def run_scraper():
    # Initialize the scraper
    scraper = EnhancedSocialScraper(delay_between_requests=2.0)
    
    # Search for videos
    videos = await scraper.scrape_hashtag(
        hashtag="dance",
        max_pages=3,
        enrich_descriptions=True
    )
    
    # Save the results
    scraper.save_to_csv(videos, "data/dance_videos.csv")

# Run the async function
asyncio.run(run_scraper())
```

## Data Structure

The enhanced scraper extracts and stores the following data for each video:

| Column                 | Description                                      |
|------------------------|--------------------------------------------------|
| url                    | Video URL on xxxxxx.com                        |
| video_id               | TikTok video ID                                  |
| scrape_time            | Timestamp of the extraction                      |
| timestamp              | Raw timestamp text (e.g., "3 days ago")          |
| estimated_release_time | Estimated datetime of video release              |
| views_raw              | Raw views value as displayed on the site         |
| likes_raw              | Raw likes value as displayed on the site         |
| comments_raw           | Raw comments value as displayed on the site      |
| views                  | Numeric views count                              |
| likes                  | Numeric likes count                              |
| comments               | Numeric comments count                           |
| author                 | Author name                                      |
| author_url             | Author profile URL                               |
| description_and_hashtags| Complete description text with hashtags         |
| hashtags_str           | Comma-separated list of hashtags                 |

## Code Structure

- `src/simple_scraper.py` : Simple HTTP-based implementation
- `src/enhanced_scraper.py` : Enhanced browser-based implementation
- `src/browser.py` : Browser manager for the enhanced implementation
- `src/logger.py` : Logging configuration for all components

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs` directory
2. Examine the debug HTML files saved to the `debug_page` directory
3. Try increasing the delay between requests if you're being rate limited
4. For the enhanced scraper, ensure Playwright is properly installed with the required browser engines

## Important Notes

1. This scraper is designed for xxxxxxx.com, which is an unofficial TikTok aggregator. The site structure may change.
2. The scraper uses the URL structure `/hash/[hashtag]/` and handles the "Load More" button to load more content.
3. Delays are included between requests to avoid being blocked.
4. The enhanced scraper visits individual video pages to extract full descriptions and all hashtags.

## Possible Improvements

- Improve detection and parsing of video elements
- Develop automated tests
- Add option to export to JSON
- Implement better date detection system
- Optimize AJAX loading to retrieve more videos
- Add proxy support for the enhanced scraper