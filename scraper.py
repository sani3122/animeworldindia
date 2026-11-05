from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE_URL = "https://animedekho.tv/category/anime/"
FILE_NAME = "animedekho_latest.m3u"
GROUP_NAME = "AnimeDekho India"

def scrape_animedekho():
    print("🚀 Starting AnimeDekho Scraper with Stealth Playwright...")
    anime_items = []
    
    with sync_playwright() as p:
        # Launch browser with arguments to hide automation and bypass bot detection
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Asia/Kolkata"
        )
        
        page = context.new_page()
        
        try:
            print(f"⏳ Navigating to {BASE_URL}...")
            page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for Cloudflare to pass and the actual anime cards/images to render
            print("🛡️ Waiting for page content to load past security checks...")
            try:
                page.wait_for_selector('img', timeout=20000)
            except Exception:
                print("⚠️ Selector timeout, proceeding with current DOM...")
                
            page.wait_for_timeout(5000) # Extra safety buffer
            
            # Check if we landed on a Cloudflare challenge page
            page_title = page.title()
            print(f"📄 Current Page Title: {page_title}")
            if "Just a moment" in page_title or "Attention Required" in page_title:
                print("❌ Blocked by Cloudflare challenge screen!")
                browser.close()
                return []

            soup = BeautifulSoup(page.content(), 'html.parser')

            # Broad search for any links pointing to series or containing images
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # Look for series links or standard anime card links
                if 'series' not in href and 'anime' not in href:
                    continue
                
                watch_link = urljoin(BASE_URL, href)
                
                # Find poster image inside the tag
                img_tag = a_tag.find('img')
                if not img_tag:
                    continue
                
                poster = img_tag.get('data-src') or img_tag.get('src') or ""
                
                # Extract title from alt attribute or text
                title = img_tag.get('alt', '').strip()
                if not title:
                    title = a_tag.get_text(strip=True)
                
                if not title or len(title) < 2 or "Image" in title:
                    continue
                
                # Avoid duplicates
                if watch_link not in [item['link'] for item in anime_items]:
                    anime_items.append({
                        'title': title,
                        'link': watch_link,
                        'poster': poster
                    })

            print(f"✨ Successfully found {len(anime_items)} anime series titles.")
            browser.close()
            return anime_items

        except Exception as e:
            print(f"⚠️ Error during Playwright scraping: {e}")
            browser.close()
            return []

def save_to_m3u(anime_items):
    if not anime_items:
        print("❌ No items found to save.")
        return

    bd_time = datetime.utcnow() + timedelta(hours=6)
    now = bd_time.strftime("%Y-%m-%d %I:%M:%S %p (BD Time)")

    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')
        f.write('# Playlist Generated Automatically by AnimeDekho Scraper\n')
        f.write(f'# Last Updated: {now}\n\n')

        for item in anime_items:
            f.write(f'#EXTINF:-1 tvg-logo="{item["poster"]}" group-title="{GROUP_NAME}", {item["title"]}\n')
            f.write(f'{item["link"]}\n')

    print(f"💾 Playlist saved successfully to {FILE_NAME}!")

if __name__ == "__main__":
    items = scrape_animedekho()
    save_to_m3u(items)
    
