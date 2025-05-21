#!/usr/bin/env python
import os
import sys
from bs4 import BeautifulSoup
from simple_scraper import SimpleScraper
import pandas as pd

def test_extraction_from_debug_file(debug_file, output_file):
    """
    Test the extraction functionality using a saved debug HTML file.
    
    Args:
        debug_file: Path to the debug HTML file
        output_file: Path to save the extracted data
    """
    print(f"Testing extraction from {debug_file}")
    
    # Load the HTML file
    with open(debug_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the container with video cards
    thumbs_container = soup.select_one('#thumbs')
    if not thumbs_container:
        print(f"ERROR: Could not find #thumbs container in {debug_file}")
        return
    
    # Find all video cards (excluding ads)
    video_elements = []
    for element in thumbs_container.select('div.thumb'):
        if 'display-flex-semi' not in element.get('class', []):
            video_elements.append(element)
    
    print(f"Found {len(video_elements)} video elements")
    
    # Create a scraper instance
    scraper = SimpleScraper()
    
    # Extract data from each video card
    results = []
    for i, video_element in enumerate(video_elements):
        try:
            video_info = scraper._extract_video_info(video_element)
            if video_info:
                results.append(video_info)
                print(f"[{i+1}] Extracted: {video_info['url']} - {video_info['timestamp']} - {video_info['views_raw']} views")
            else:
                print(f"[{i+1}] Failed to extract data")
        except Exception as e:
            print(f"[{i+1}] Error: {e}")
    
    print(f"Successfully extracted {len(results)} videos")
    
    # Save to CSV
    if results:
        scraper.save_to_csv(results, output_file)
        print(f"Saved results to {output_file}")
        
        # Display a summary of the extracted data
        df = pd.DataFrame(results)
        print("\nExtraction Summary:")
        print(f"- Videos with timestamp: {df['timestamp'].notna().sum()}/{len(df)}")
        print(f"- Videos with views: {df['views_raw'].notna().sum()}/{len(df)}")
        print(f"- Videos with likes: {df['likes_raw'].notna().sum()}/{len(df)}")
        print(f"- Videos with comments: {df['comments_raw'].notna().sum()}/{len(df)}")
        
        # Check for videos without proper URL format
        invalid_urls = df[~df['url'].str.contains('/video/', na=True)]
        if not invalid_urls.empty:
            print(f"\nWARNING: Found {len(invalid_urls)} videos without proper URL format:")
            for i, row in invalid_urls.iterrows():
                print(f"- {row.get('url', 'N/A')}")

if __name__ == "__main__":
    # Check for the debug file argument
    if len(sys.argv) < 2:
        debug_files = [f for f in os.listdir('.') if f.startswith('debug_page_') and f.endswith('.html')]
        if not debug_files:
            print("No debug files found. Please create one first with the scraper.")
            sys.exit(1)
        debug_file = debug_files[0]
        print(f"Using default debug file: {debug_file}")
    else:
        debug_file = sys.argv[1]
    
    # Default output file based on debug file name
    hashtag = debug_file.replace('debug_page_', '').replace('.html', '')
    output_file = f"data/{hashtag}_videos.csv"
    
    # Run the test
    test_extraction_from_debug_file(debug_file, output_file)