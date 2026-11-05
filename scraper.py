import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

BASE_URL = "https://animedekho.tv/category/anime/"
FILE_NAME = "animedekho_streams.m3u"
GROUP_NAME = "AnimeDekho India"
MAX_SERIES_TO_SCRAPE = 5  # Limits how many shows to parse per run so GitHub Actions doesn't time out

def get_stealth_browser(p):
    """Launches a chromium browser configured to bypass bot detection."""
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
    return browser, context

def extract_stream_link(page, episode_url):
    """Navigates to an episode page and extracts the video stream or embedded player URL."""
    print(f"  └─ 🔍 Finding direct video link from: {episode_url}")
    video_url = None
    
    # Intercept network requests to catch direct .m3u8 or video stream endpoints
    def handle_request(request):
        nonlocal video_url
        req_url = request.url
        if ".m3u8" in req_url or ".mp4" in req_url:
            if "master.m3u8" in req_url or "index" in req_url or ".mp4" in req_url:
                video_url = req_url

    page.on("request", handle_request)

    try:
        page.goto(episode_url, timeout=45000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        # If network interception didn't capture a raw stream, extract the embedded iframe source
        if not video_url:
            soup = BeautifulSoup(page.content(), 'html.parser')
            iframe = soup.find('iframe', src=True)
            if iframe:
                video_url = iframe['src']
                if video_url.startswith('//'):
                    video_url = 'https:' + video_url

    except Exception as e:
        print(f"  └─ ⚠️ Failed to parse episode page: {e}")

    return video_url or episode_url  # Fallback to episode URL if stream extraction is blocked

def scrape_anime_dekho():
    print("🚀 Starting Deep AnimeDekho Scraper...")
    final_entries = []

    with sync_playwright() as p:
        browser, context = get_stealth_browser(p)
        page = context.new_page()

        try:
            print(f"⏳ Navigating to main category page: {BASE_URL}")
            page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for content to render past Cloudflare checks
            try:
                page.wait_for_selector('a[href*="/series-hindi/"]', timeout=20000)
            except Exception:
                page.wait_for_timeout(5000)

            soup = BeautifulSoup(page.content(), 'html.parser')

            # Step 1: Collect series card links and posters
            discovered_series = []
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if '/series-hindi/' not in href:
                    continue

                watch_link = urljoin(BASE_URL, href)
                img_tag = a_tag.find('img')
                
                poster = ""
                title = ""
                if img_tag:
                    poster = img_tag.get('data-src') or img_tag.get('src') or ""
                    title = img_tag.get('alt', '').strip()

                if not title:
                    title = a_tag.get_text(strip=True)

                if title and watch_link not in [s['link'] for s in discovered_series]:
                    discovered_series.append({
                        'title': title,
                        'link': watch_link,
                        'poster': poster
                    })

            print(f"✨ Found {len(discovered_series)} series on the main page. Processing top {MAX_SERIES_TO_SCRAPE}...")

            # Step 2: Iterate through each series to extract episode links
            for series in discovered_series[:MAX_SERIES_TO_SCRAPE]:
                print(f"\n🎬 Processing Series: {series['title']}")
                
                try:
                    page.goto(series['link'], timeout=45000, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    
                    series_soup = BeautifulSoup(page.content(), 'html.parser')
                    
                    # Find episode links inside the series page
                    ep_links = []
                    for ep_a in series_soup.find_all('a', href=True):
                        ep_href = ep_a['href']
                        if any(k in ep_href for k in ['/episode/', '-episode-', '/watch/']):
                            full_ep_url = urljoin(BASE_URL, ep_href)
                            if full_ep_url not in ep_links:
                                ep_links.append(full_ep_url)

                    # Step 3: Extract direct playable video links for each episode
                    if ep_links:
                        for idx, ep_url in enumerate(ep_links[:5], start=1):  # Scrape first 5 episodes per series
                            stream_link = extract_stream_link(page, ep_url)
                            final_entries.append({
                                'title': f"{series['title']} - Episode {idx}",
                                'link': stream_link,
                                'poster': series['poster']
                            })
                    else:
                        # Fallback if episodes are embedded directly on the main series page
                        stream_link = extract_stream_link(page, series['link'])
                        final_entries.append({
                            'title': series['title'],
                            'link': stream_link,
                            'poster': series['poster']
                        })

                except Exception as e:
                    print(f"⚠️ Error parsing series {series['title']}: {e}")

            browser.close()
            return final_entries

        except Exception as e:
            print(f"❌ Main process error: {e}")
            browser.close()
            return []

def save_to_m3u(anime_items):
    if not anime_items:
        print("❌ No streaming links found to save.")
        return

    bd_time = datetime.utcnow() + timedelta(hours=6)
    now = bd_time.strftime("%Y-%m-%d %I:%M:%S %p (BD Time)")

    with open(FILE_NAME, "w", encoding="utf-8") as f:
        f.write('#EXTM3U\n')
        f.write('# Playlist Generated Automatically by Deep AnimeDekho Stream Scraper\n')
        f.write(f'# Last Updated: {now}\n\n')

        for item in anime_items:
            f.write(f'#EXTINF:-1 tvg-logo="{item["poster"]}" group-title="{GROUP_NAME}", {item["title"]}\n')
            f.write(f'{item["link"]}\n')

    print(f"\n💾 Saved {len(anime_items)} direct play/stream links to {FILE_NAME}!")

if __name__ == "__main__":
    items = scrape_anime_dekho()
    save_to_m3u(items)
