"""
Streamlit interface for TikTok hashtag scraping.
Simple UI that wraps around the hash_scraper.py functionality.
"""

import streamlit as st
import asyncio
import pandas as pd
import io
import os
import sys
from datetime import datetime

# Add src directory to path to import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.hash_scraper import HashPageScraper

def build_tiktok_url(author, video_id):
    """
    Build the real TikTok URL from author and video_id.
    
    Args:
        author: Author username
        video_id: Video ID
        
    Returns:
        TikTok URL string
    """
    if author and video_id:
        # Clean author name (remove @ if present)
        clean_author = author.replace('@', '') if author else ''
        return f"https://www.tiktok.com/@{clean_author}/video/{video_id}"
    return ""

def process_videos_for_export(videos):
    """
    Process scraped videos into the format needed for Excel export.
    
    Args:
        videos: List of video dictionaries from scraper
        
    Returns:
        DataFrame with columns ready for Excel export
    """
    if not videos:
        return pd.DataFrame()
    
    # Create the export data
    export_data = []
    for video in videos:
        # Build the real TikTok URL
        tiktok_url = build_tiktok_url(video.get('author', ''), video.get('video_id', ''))
        
        export_row = {
            'tiktok_url': tiktok_url,
            'estimated_release_time': video.get('estimated_release_time', ''),
            'views': video.get('views', 0),
            'likes': video.get('likes', 0),
            'comments': video.get('comments', 0),
            'description_and_hashtags': video.get('description_and_hashtags', ''),
            'author': video.get('author', '')
        }
        export_data.append(export_row)
    
    return pd.DataFrame(export_data)

async def run_scraper(hashtag, max_loads):
    """
    Run the hash scraper asynchronously.
    
    Args:
        hashtag: Hashtag to scrape
        max_loads: Maximum number of Load More operations
        
    Returns:
        List of scraped videos
    """
    scraper = HashPageScraper(delay_between_requests=2.0)
    videos = await scraper.scrape_hashtag_page(hashtag, max_loads)
    return videos

def create_excel_download(df):
    """
    Create an Excel file in memory for download.
    
    Args:
        df: DataFrame to convert to Excel
        
    Returns:
        BytesIO buffer containing Excel file
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='TikTok_Videos')
        
        # Get the xlsxwriter workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['TikTok_Videos']
        
        # Add some formatting
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D7E4BC',
            'border': 1
        })
        
        # Write the column headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
        
        # Auto-adjust column widths
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            worksheet.set_column(i, i, min(column_len, 50))
    
    output.seek(0)
    return output

def main():
    """Main Streamlit application."""
    
    # Page configuration
    st.set_page_config(
        page_title="TikTok Hashtag Scraper",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title and description
    st.title("🎵 TikTok Hashtag Scraper")
    st.markdown("---")
    st.markdown("""
    **Simple tool to scrape TikTok videos by hashtag**
    
    This tool extracts basic video information from hashtag pages and provides:
    - Real TikTok URLs
    - Video metadata (views, likes, comments)
    - Author information
    - Descriptions and hashtags
    - Estimated release times
    """)
    
    # Sidebar for inputs
    st.sidebar.header("⚙️ Scraping Configuration")
    
    # Hashtag input
    hashtag = st.sidebar.text_input(
        "Hashtag to scrape",
        placeholder="e.g., dance, cooking, funny",
        help="Enter hashtag without # symbol"
    )
    
    # Max loads slider
    max_loads = st.sidebar.slider(
        "Maximum Load More operations",
        min_value=1,
        max_value=5,
        value=3,
        help="Number of times to click 'Load More' to get additional videos"
    )
    
    # Information about limits
    st.sidebar.info(
        f"""
        **Current Settings:**
        - Hashtag: {hashtag or 'Not set'}
        - Max loads: {max_loads}
        - Expected videos: ~{max_loads * 20} videos
        """
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Note:** Scraping may take 1-3 minutes depending on the number of Load More operations.")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Start scraping button
        if st.button("🚀 Start Scraping", type="primary", disabled=not hashtag):
            if not hashtag:
                st.error("Please enter a hashtag to scrape.")
                return
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                status_text.text("🔍 Initializing scraper...")
                progress_bar.progress(10)
                
                status_text.text("🌐 Loading hashtag page...")
                progress_bar.progress(30)
                
                # Run the scraper
                status_text.text(f"📊 Scraping #{hashtag} videos...")
                progress_bar.progress(50)
                
                # Use asyncio to run the async scraper
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                videos = loop.run_until_complete(run_scraper(hashtag, max_loads))
                loop.close()
                
                progress_bar.progress(80)
                status_text.text("📝 Processing results...")
                
                if videos:
                    # Process videos for export
                    df = process_videos_for_export(videos)
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Scraping completed!")
                    
                    # Display results
                    st.success(f"Successfully scraped {len(videos)} videos!")
                    
                    # Show preview of data
                    st.subheader("📋 Preview of Scraped Data")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                    if len(df) > 10:
                        st.info(f"Showing first 10 rows. Total: {len(df)} videos")
                    
                    # Download section
                    st.subheader("💾 Download Results")
                    
                    # Create Excel file
                    excel_buffer = create_excel_download(df)
                    
                    # Download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"tiktok_{hashtag}_{timestamp}.xlsx"
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=excel_buffer.getvalue(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    # Show summary statistics
                    st.subheader("📊 Summary Statistics")
                    col_stats1, col_stats2, col_stats3 = st.columns(3)
                    
                    with col_stats1:
                        st.metric("Total Videos", len(df))
                        st.metric("Average Views", f"{df['views'].mean():,.0f}" if len(df) > 0 else "0")
                    
                    with col_stats2:
                        st.metric("Average Likes", f"{df['likes'].mean():,.0f}" if len(df) > 0 else "0")
                        st.metric("Average Comments", f"{df['comments'].mean():,.0f}" if len(df) > 0 else "0")
                    
                    with col_stats3:
                        st.metric("Unique Authors", df['author'].nunique() if len(df) > 0 else 0)
                        st.metric("Most Active Author", df['author'].mode()[0] if len(df) > 0 else "N/A")
                
                else:
                    progress_bar.progress(100)
                    status_text.text("❌ No videos found")
                    st.warning("No videos were found for this hashtag. This could be due to:")
                    st.markdown("""
                    - The hashtag doesn't exist or has no recent videos
                    - Network issues during scraping
                    - The website structure has changed
                    - Rate limiting or blocking
                    """)
                
            except Exception as e:
                progress_bar.progress(100)
                status_text.text("❌ Error occurred")
                st.error(f"An error occurred during scraping: {str(e)}")
                st.markdown("**Possible solutions:**")
                st.markdown("""
                - Try a different hashtag
                - Reduce the number of Load More operations
                - Check your internet connection
                - Try again in a few minutes
                """)
    
    with col2:
        st.subheader("ℹ️ How it works")
        st.markdown("""
        1. **Enter a hashtag** (without #)
        2. **Set max loads** (1-5)
        3. **Click Start Scraping**
        4. **Download Excel file** with results
        
        **Excel contains:**
        - Real TikTok URLs
        - Video statistics
        - Author information
        - Descriptions & hashtags
        - Release times
        """)
        
        st.subheader("⚠️ Important Notes")
        st.markdown("""
        - Scraping is limited to 5 loads max
        - Each load ≈ 20 videos
        - Process takes 1-3 minutes
        - Respect rate limits
        - For research/analysis only
        """)

if __name__ == "__main__":
    main()