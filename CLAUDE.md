# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based web scraper for extracting TikTok video data from urlebird.com (a TikTok content aggregator) based on hashtags. The scraper filters by date range and extracts metadata such as video title, author, views, likes, and hashtags.

The project is designed to address several challenges:
- Working with the specific URL structure of urlebird.com (/hash/[hashtag]/)
- Handling AJAX-based "Load More" functionality instead of traditional pagination
- Extracting structured data from a site with potentially changing HTML structure
- Implementing robust error handling and retry mechanisms

## Commands

### Setup and Installation

```bash
# Install dependencies with pip
pip install -r requirements.txt

# Or preferably use pipenv
pipenv install
pipenv shell
```

### Running the Scraper

```bash
# Basic usage
python src/main.py --hashtag dance

# With date filtering
python src/main.py --hashtag dance --start-date 2023-01-01 --end-date 2023-12-31

# Specify output file
python src/main.py --hashtag dance --output data/dance_videos.csv

# Increase number of pages
python src/main.py --hashtag dance --max-pages 10

# Enable concurrent scraping
python src/main.py --hashtag dance --concurrent --max-workers 4

# Use incremental save to avoid data loss
python src/main.py --hashtag dance --incremental-save

# Generate statistics
python src/main.py --hashtag dance --save-stats

# Use proxy to avoid being blocked
python src/main.py --hashtag dance --proxy http://user:pass@proxy.example.com:8080
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

The scraper is organized into two main components:

1. **Main Script** (`src/main.py`): 
   - Command-line interface that parses arguments
   - Sets up logging configuration
   - Handles file management and output directories
   - Creates and configures the UrlebirdScraper instance
   - Processes date ranges for filtering
   - Manages scraping execution and output saving
   - Optionally generates statistics on scraped data

2. **Scraper Implementation** (`src/urlebird_scraper.py`):
   - `UrlebirdScraper` class with the core scraping functionality
   - Makes HTTP requests with retry mechanisms and user-agent rotation
   - Parses HTML using multiple selector strategies for resilience
   - Handles AJAX-based "Load More" functionality
   - Extracts structured data from HTML and JSON
   - Implements date filtering and validation
   - Provides both sequential and concurrent scraping methods
   - Includes methods for saving results to CSV

### Key Technical Challenges

The scraper addresses several technical challenges:

1. **Dynamic HTML Structure**: Uses multiple CSS selectors for each element type to handle potential HTML structure changes.

2. **AJAX Content Loading**: Implements logic to find the "Load More" button, extract its parameters, and make AJAX requests to load additional content.

3. **JSON Data Extraction**: Analyzes embedded JSON data in script tags to extract video information when HTML parsing is insufficient.

4. **Error Handling**: Implements comprehensive error handling with retry mechanisms and backoff strategies.

5. **Date Parsing and Filtering**: Handles multiple date formats and provides filtering capabilities based on video publication dates.

## Development Notes

- The core functionality is mostly implemented, but improvements to the AJAX handling may be needed
- The concurrent scraping implementation may need refinement
- New selectors may need to be added as the site's HTML structure evolves
- Consider the site's robots.txt policies when making changes to request frequency or concurrency

## Best Practices

When making changes to this codebase:

1. Maintain the multi-selector approach for HTML parsing to ensure resilience
2. Preserve the delay between requests to avoid being blocked
3. Test changes thoroughly with different hashtags and date ranges
4. Update the debug logging to help with future troubleshooting
5. Consider adding more unit tests to improve reliability