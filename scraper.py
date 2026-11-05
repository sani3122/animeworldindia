import cloudscraper
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

# --- Configuration ---
BASE_URL = "https://watchanimeworld.one"
FILE_NAME = "anime_world_latest.m3u"
GROUP_NAME = "Anime World India"

def get_domain(url):
    """Extracts the main domain from a full URL."""
    parsed_uri = urlparse(url)
    return '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)

def scrape_anime_world():
    """Scans the homepage of watchanimeworld.one to extract anime and cartoon titles, links, and posters."""
    print("🚀 Starting Anime World India Scraper...")
    
    # Initialize cloudscraper to bypass anti-bot protections
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    try:
        response = scraper.get(BASE_URL, timeout=15)
        if response.status_code != 200:
            print(f"❌ Failed to load page. Status code: {response.status_code}")
            return []
            
        soup = BeautifulSoup(response.text, 'html.parser')
        anime_items = []
        
        # Target movie/anime cards and links on the page
        # Note: Depending on the site's exact DOM structure, you may need to adjust the CSS selectors or tags below.
        for card in soup.find_all(['a', 'div'], class_=re.compile(r'card|item|post|movie|show', re.I)):
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            if not link_tag or not link_tag.get('href'):
                continue
                
            watch_link = urljoin(BASE_URL, link_tag['href'])
            
            # Extract title
            title_tag = card.find(['h3', 'h4', 'span', 'p'], class_=re.compile(r'title|name', re.I))
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                # Fallback to link text or alt attribute if title tag isn't explicit
                title = link_tag.get_text(strip=True) or "Unknown Anime"
                
            # Extract poster image
            img_tag = card.find('img')
            poster = ""
            if img_tag:
                poster = img_tag.get('data-src') or img_tag.get('src') or ""
                if poster and not poster.startswith('http'):
                    poster = urljoin(BASE_URL, poster)
                    
            # Avoid duplicate entries
            if watch_link not in [item['link'] for item in anime_items] and title != "Unknown Anime":
                anime_items.append({
                    'title': title,
                    'link': watch_link,
                    'poster': poster
                })
                
        print(f"✨ Successfully found {len(anime_items)} anime/cartoon titles.")
        return anime_items
        
    except Exception as e:
        print(f"⚠️ Error during scraping: {e}")
        return []

def save_to_m3u(anime_items):
    """Saves the scraped anime items into an M3U playlist file."""
    if not anime_items:
        print("❌ No items found to save.")
        return

    bd_time = datetime.utcnow() + timedelta(hours=6)
    now = bd_time.strftime("%Y-%m-%d %I:%M:%S %p (BD Time)")
    
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')
        f.write('# Playlist Generated Automatically by Anime World India Scraper\n')
        f.write(f'# Last Updated: {now}\n\n')
        
        for item in anime_items:
            title = item['title']
            link = item['link']
            poster = item['poster']
            
            f.write(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{GROUP_NAME}", {title}\n')
            f.write(f'{link}\n')
            
    print(f"💾 Playlist saved successfully to {FILE_NAME}!")

if __name__ == "__main__":
    items = scrape_anime_world()
    save_to_m3u(items)
