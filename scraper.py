import cloudscraper
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

BASE_URL = "https://watchanimeworld.one"
FILE_NAME = "anime_world_latest.m3u"
GROUP_NAME = "Anime World India"

def scrape_anime_world():
    print("🚀 Starting Anime World India Scraper...")
    
    # Create scraper with modern browser user-agent and desktop headers
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Custom headers to trick Cloudflare into treating the GitHub runner like a regular visitor
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive'
    }

    try:
        response = scraper.get(BASE_URL, headers=headers, timeout=20)
        
        if response.status_code != 200:
            print(f"❌ Failed to load page. Status code: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        anime_items = []

        # Find anime/movie cards
        for card in soup.find_all(['a', 'div'], class_=re.compile(r'card|item|post|movie|show', re.I)):
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            if not link_tag or not link_tag.get('href'):
                continue
                
            watch_link = urljoin(BASE_URL, link_tag['href'])
            
            title_tag = card.find(['h3', 'h4', 'span', 'p'], class_=re.compile(r'title|name', re.I))
            title = title_tag.get_text(strip=True) if title_tag else link_tag.get_text(strip=True) or "Unknown Anime"
                
            img_tag = card.find('img')
            poster = ""
            if img_tag:
                poster = img_tag.get('data-src') or img_tag.get('src') or ""
                if poster and not poster.startswith('http'):
                    poster = urljoin(BASE_URL, poster)

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
            f.write(f'#EXTINF:-1 tvg-logo="{item["poster"]}" group-title="{GROUP_NAME}", {item["title"]}\n')
            f.write(f'{item["link"]}\n')

    print(f"💾 Playlist saved successfully to {FILE_NAME}!")

if __name__ == "__main__":
    items = scrape_anime_world()
    save_to_m3u(items)
