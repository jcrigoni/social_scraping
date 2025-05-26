# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based web scraper for extracting TikTok video data from xxxxxx.com (a TikTok content aggregator) based on hashtags. The scraper filters by date range and extracts metadata such as video title, author, views, likes, and hashtags.

The project now includes multiple scraper implementations:
1. A simple HTTP-based scraper (simple_scraper.py)
2. An enhanced browser-based scraper (enhanced_scraper.py) that can extract full descriptions and hashtags
3. A two-stage scraping approach:
   - Hash page scraper (hash_scraper.py) - Stage 1: Extracts basic video data from hashtag pages
   - Video enricher (video_enricher.py) - Stage 2: Enriches videos with full descriptions by visiting individual pages

The project is designed to address several challenges:
- Working with the specific URL structure of urlebird.com (/hash/[hashtag]/)
- Handling AJAX-based "Load More" functionality instead of traditional pagination
- Extracting structured data from a site with potentially changing HTML structure
- Implementing robust error handling and retry mechanisms
- Retrieving complete descriptions and hashtags that are truncated in the HTML

## Commands

### Setup and Installation

```bash
# Install dependencies with pip
pip install -r requirements.txt

# Or preferably use pipenv
pipenv install
pipenv shell

# For the enhanced scraper, install playwright
pip install playwright
python -m playwright install chromium
```

### Running the Simple Scraper

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

### Running the Enhanced Scraper

```bash
# Basic usage
python src/enhanced_scraper.py --hashtag dance

# With multiple pages and custom output
python src/enhanced_scraper.py --hashtag dance --max-pages 3 --output data/dance_results.csv

# Adjust delay between requests
python src/enhanced_scraper.py --hashtag dance --delay 3.0

# Skip description enrichment phase (faster but incomplete descriptions)
python src/enhanced_scraper.py --hashtag dance --no-enrich
```

### Running the Two-Stage Scraper (Recommended)

The two-stage approach is more efficient and allows better control over the scraping process:

#### Stage 1: Hash Page Scraping
```bash
# Basic usage - scrapes hashtag page and saves basic video data
python src/hash_scraper.py --hashtag dance

# With custom output and multiple Load More operations
python src/hash_scraper.py --hashtag dance --output data/dance_basic.csv --max-loads 10

# Adjust delay between Load More operations
python src/hash_scraper.py --hashtag dance --delay 3.0
```

#### Stage 2: Video Enrichment
```bash
# Enrich videos with full descriptions from individual video pages
python src/video_enricher.py --input data/dance_basic.csv --output data/dance_complete.csv

# Adjust processing parameters
python src/video_enricher.py --input data/dance_basic.csv --output data/dance_complete.csv --batch-size 10 --max-concurrent 5

# Control delay between batches
python src/video_enricher.py --input data/dance_basic.csv --output data/dance_complete.csv --delay 3.0
```

### Using pipenv scripts

```bash
# Using the predefined pipenv script
pipenv run scrape --hashtag dance
```

### Development

```bash
# Run linting with flake8
pipenv run flake8 src/

# Format code with black
pipenv run black src/

# Run tests (when implemented)
pipenv run pytest
```

## Code Architecture

The scraper is now organized into multiple components:

1. **Simple Scraper** (`src/simple_scraper.py`): 
   - Basic HTTP-based scraper
   - Makes simple HTTP requests with user-agent rotation
   - Extracts basic metadata from the list view
   - Lighter and faster, but cannot get full descriptions

2. **Enhanced Scraper** (`src/enhanced_scraper.py`):
   - Uses headless browser automation with Playwright
   - Extracts complete descriptions and hashtags by visiting individual video pages
   - Handles truncated descriptions with ellipsis ('...')
   - Provides richer data but slower performance

3. **Two-Stage Scraping System** (Recommended):
   - **Hash Page Scraper** (`src/hash_scraper.py`): 
     - Stage 1: Extracts basic video metadata from hashtag pages
     - Properly handles "Load More" button functionality with AJAX
     - Uses Playwright to click Load More buttons and load additional content
     - Saves intermediate data with 'needs_enrichment' flag
     - Faster initial data collection
   
   - **Video Enricher** (`src/video_enricher.py`):
     - Stage 2: Reads intermediate CSV and enriches videos with full descriptions
     - Only processes videos that need enrichment (marked with 'needs_enrichment' flag)
     - Visits individual video pages to extract complete descriptions and hashtags
     - Supports batch processing and concurrent requests with rate limiting
     - Produces final enriched dataset

4. **Browser Manager** (`src/browser.py`):
   - Manages browser instantiation and page navigation
   - Handles cookies, timeouts, and retries
   - Provides rate limiting to avoid being blocked

5. **Logger** (`src/logger.py`):
   - Configures logging for all components
   - Saves debug information to log files

### Key Technical Challenges

The scraper addresses several technical challenges:

1. **Dynamic HTML Structure**: Uses multiple CSS selectors for each element type to handle potential HTML structure changes.

2. **Truncated Descriptions**: The enhanced scraper can detect truncated descriptions (ending with '...') and visit the video page to extract the full text.

3. **AJAX Content Loading**: Implements logic to find and click the "Load More" button using Playwright, properly waiting for AJAX requests to complete and new content to load.

4. **Error Handling**: Implements comprehensive error handling with retry mechanisms and backoff strategies.

5. **Date Parsing and Filtering**: Handles multiple date formats and provides filtering capabilities based on video publication dates.

## Data Structure

The enhanced scraper extracts and stores the following data for each video:

| Column                  | Description                                        |
|-------------------------|----------------------------------------------------|
| url                     | Video URL on xxxxxxx.com                           |
| video_id                | TikTok video ID                                     |
| scrape_time             | Timestamp when the scraping was performed           |
| timestamp               | Raw timestamp text (e.g., "3 days ago")             |
| estimated_release_time  | Estimated datetime of video release                 |
| views_raw               | Raw views value as displayed on the site            |
| likes_raw               | Raw likes value as displayed on the site            |
| comments_raw            | Raw comments value as displayed on the site         |
| views                   | Numeric views count                                 |
| likes                   | Numeric likes count                                 |
| comments                | Numeric comments count                              |
| author                  | Author name                                         |
| author_url              | Author profile URL                                  |
| description_and_hashtags| Complete comment text with hashtags                |
| hashtags_str            | Comma-separated list of hashtags                    |

## Development Notes

- The enhanced scraper uses an async workflow with Playwright for browser automation
- Debug HTML files are saved to help with troubleshooting in the debug_page directory
- The description enrichment process can be disabled for faster scraping if full descriptions aren't needed
- Rate limiting is implemented in both scrapers to avoid being blocked

## Best Practices

When making changes to this codebase:

1. Maintain the multi-selector approach for HTML parsing to ensure resilience
2. Preserve the delay between requests to avoid being blocked
3. Test changes thoroughly with different hashtags and date ranges
4. Update the debug logging to help with future troubleshooting
5. Consider adding more unit tests to improve reliability
6. Use the two-stage scraping approach for the best balance of speed and completeness:
   - Use hash scraper for fast initial data collection
   - Use video enricher for complete descriptions only when needed
7. Use the simple scraper for very fast basic data collection
8. Use the enhanced scraper when you need everything in one go (slower but complete)

## Troubleshooting

If you encounter issues:

1. Check the log files in the `logs` directory
2. Examine the debug HTML files saved to the `debug_page` directory
3. Try increasing the delay between requests if you're being rate limited
4. For the enhanced scraper, ensure Playwright is properly installed with the required browser engines