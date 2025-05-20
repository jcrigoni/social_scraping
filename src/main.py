import argparse
from datetime import datetime
import os
from urlebird_scraper import UrlebirdScraper
from logger import setup_logger

# Configure logging
logger = setup_logger('main')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape videos from urlebird.com with specific hashtags and date range"
    )
    
    parser.add_argument(
        "--hashtag", 
        type=str, 
        required=True,
        help="Hashtag to search for (with or without # symbol)"
    )
    
    parser.add_argument(
        "--start-date", 
        type=str, 
        help="Start date in YYYY-MM-DD format (inclusive)"
    )
    
    parser.add_argument(
        "--end-date", 
        type=str, 
        help="End date in YYYY-MM-DD format (inclusive)"
    )
    
    parser.add_argument(
        "--output", 
        type=str, 
        default="data/results.csv",
        help="Output CSV file path (default: data/results.csv)"
    )
    
    parser.add_argument(
        "--max-pages", 
        type=int, 
        default=5,
        help="Maximum number of pages to scrape (default: 5)"
    )
    
    parser.add_argument(
        "--delay", 
        type=float, 
        default=2.0,
        help="Delay between requests in seconds (default: 2.0)"
    )
    
    # Nouveaux arguments
    parser.add_argument(
        "--concurrent", 
        action="store_true",
        help="Use concurrent scraping (faster but more resource intensive)"
    )
    
    parser.add_argument(
        "--max-workers", 
        type=int, 
        default=3,
        help="Maximum number of concurrent workers (default: 3)"
    )
    
    parser.add_argument(
        "--incremental-save", 
        action="store_true",
        help="Save results incrementally during scraping"
    )
    
    parser.add_argument(
        "--proxy", 
        type=str,
        help="HTTP proxy to use (format: http://user:pass@host:port)"
    )
    
    parser.add_argument(
        "--save-stats", 
        action="store_true",
        help="Generate stats summary in a separate file"
    )
    
    return parser.parse_args()

def main():
    """Main function to run the scraper."""
    args = parse_args()
    
    # Parse dates if provided
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD.")
            return
    
    end_date = None
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD.")
            return
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    
    # Configure proxies if provided
    proxies = None
    if args.proxy:
        proxies = {
            'http': args.proxy,
            'https': args.proxy
        }
        logger.info(f"Using proxy: {args.proxy}")
    
    # Initialize scraper with new options
    scraper = UrlebirdScraper(
        delay_between_requests=args.delay,
        proxies=proxies
    )
    
    # Determine which search method to use
    if args.concurrent:
        logger.info(f"Using concurrent scraping with {args.max_workers} workers")
        videos = scraper.search_videos_concurrent(
            hashtag=args.hashtag,
            start_date=start_date,
            end_date=end_date,
            max_pages=args.max_pages,
            max_workers=args.max_workers
        )
    else:
        # Set up incremental save if requested
        incremental_save_path = args.output if args.incremental_save else None
        
        videos = scraper.search_videos(
            hashtag=args.hashtag,
            start_date=start_date,
            end_date=end_date,
            max_pages=args.max_pages,
            incremental_save_path=incremental_save_path
        )
    
    # Save results
    if videos:
        scraper.save_to_csv(videos, args.output)
        logger.info(f"Successfully saved {len(videos)} videos to {args.output}")
        
        # Generate stats if requested
        if args.save_stats:
            import pandas as pd
            df = pd.DataFrame(videos)
            
            stats_file = os.path.join(output_dir, "stats_summary.txt")
            with open(stats_file, 'w') as f:
                f.write(f"Scraping Results Summary for #{args.hashtag}\n")
                f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total videos found: {len(videos)}\n\n")
                
                if 'views' in df.columns:
                    f.write(f"Average views: {df['views'].mean():.1f}\n")
                    f.write(f"Max views: {df['views'].max()}\n")
                
                if 'likes' in df.columns:
                    f.write(f"Average likes: {df['likes'].mean():.1f}\n")
                    f.write(f"Max likes: {df['likes'].max()}\n")
                
                if 'author' in df.columns:
                    f.write(f"\nTop 10 authors by video count:\n")
                    author_counts = df['author'].value_counts().head(10)
                    for author, count in author_counts.items():
                        f.write(f"- {author}: {count} videos\n")
                
                if 'hashtags' in df.columns:
                    # Extract hashtags (they're stored as comma-separated strings)
                    all_hashtags = []
                    for tags in df['hashtags']:
                        if tags:
                            all_hashtags.extend(tags.split(','))
                    
                    if all_hashtags:
                        # Count occurrences
                        from collections import Counter
                        hashtag_counts = Counter(all_hashtags)
                        
                        f.write(f"\nTop 10 related hashtags:\n")
                        for tag, count in hashtag_counts.most_common(10):
                            if tag.lower() != args.hashtag.lower().replace('#', ''):
                                f.write(f"- #{tag}: {count} occurrences\n")
                
            logger.info(f"Generated stats summary at {stats_file}")
    else:
        logger.warning("No videos found matching the criteria")

if __name__ == "__main__":
    main()
