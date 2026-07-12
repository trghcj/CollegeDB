import requests
from bs4 import BeautifulSoup
import json
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_homepage(url: str) -> tuple[str, BeautifulSoup]:
    """Fetches and parses the homepage HTML once."""
    if not url.startswith('http'):
        url = 'https://' + url
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        if resp.status_code == 200:
            return resp.text, BeautifulSoup(resp.text, 'lxml')
    except Exception as e:
        logger.error(f"[HTML Extractor] Failed to fetch {url}: {e}")
    return "", None

def get_favicon(soup: BeautifulSoup, base_url: str) -> str:
    """Tier 2: Favicon"""
    if not soup: return ""
    tags = [
        soup.find("link", rel=lambda x: x and 'icon' in x.lower()),
        soup.find("link", rel=lambda x: x and 'apple-touch-icon' in x.lower()),
        soup.find("link", rel=lambda x: x and 'shortcut icon' in x.lower())
    ]
    for tag in tags:
        if tag and tag.get('href'):
            href = tag.get('href')
            if 'favicon' in href.lower() or 'logo' in href.lower() or 'icon' in href.lower():
                return urljoin(base_url, href)
    return ""

def get_og_image(soup: BeautifulSoup, base_url: str) -> str:
    """Tier 3: Open Graph Image"""
    if not soup: return ""
    tags = [
        soup.find("meta", property="og:image"),
        soup.find("meta", attrs={"name": "twitter:image"})
    ]
    for tag in tags:
        if tag and tag.get('content'):
            img_url = tag.get('content')
            # STRICT FILTER: OpenGraph images are often full posters. Only accept if it says 'logo'
            if 'logo' in img_url.lower() and is_valid_logo_url(img_url):
                return urljoin(base_url, img_url)
    return ""

def get_json_ld_logo(soup: BeautifulSoup, base_url: str) -> str:
    """Tier 4: JSON-LD Structured Data"""
    if not soup: return ""
    scripts = soup.find_all("script", type="application/ld+json")
    for script in scripts:
        if not script.string: continue
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                data_list = data
            else:
                data_list = [data]
                
            for data in data_list:
                if data.get('@type') in ['CollegeOrUniversity', 'EducationalOrganization', 'Organization']:
                    if 'image' in data:
                        img = data['image']
                        url = None
                        if isinstance(img, str): url = urljoin(base_url, img)
                        elif isinstance(img, dict) and 'url' in img: url = urljoin(base_url, img['url'])
                        if url and is_valid_logo_url(url): return url
                    if 'logo' in data:
                        img = data['logo']
                        url = None
                        if isinstance(img, str): url = urljoin(base_url, img)
                        elif isinstance(img, dict) and 'url' in img: url = urljoin(base_url, img['url'])
                        if url and is_valid_logo_url(url): return url
        except json.JSONDecodeError:
            continue
    return ""

def is_valid_logo_url(url: str, alt: str = "") -> bool:
    """Checks if a URL or alt text contains badge/award or social media keywords."""
    combined = (url + " " + (alt or "")).lower()
    badges = [
        'rank', 'badge', 'award', 'metric', 'nba', 'naac', 'aicte', 'iso', 'qs', 'nirf', 
        'nptel', 'swayam', 'ugc', 'mhrd', 'azadi', 'g20', 'campaign', 'banner',
        'instagram', 'facebook', 'twitter', 'youtube', 'linkedin', 'whatsapp', 
        'telegram', 'pinterest', 'discord', 'snapchat', 'tiktok', 'social', 'x.com',
        'jubilee', 'anniversary', 'diamond', 'golden', 'silver', '60', '75', '100', 'years',
        'cms', 'erp', 'portal', 'intellect', 'samarth', 'management'
    ]
    for b in badges:
        if b in combined:
            return False
    return True

def get_header_logo(soup: BeautifulSoup, base_url: str) -> str:
    """Tier 5: Official Website Header Logo (incl. CSS background)"""
    if not soup: return ""
    
    headers = soup.find_all(['header', 'nav', 'div'], class_=lambda x: x and ('header' in x.lower() or 'nav' in x.lower() or 'logo' in x.lower()))
    if not headers:
        headers = [soup] # Fallback to whole page
        
    import re
    bg_regex = re.compile(r'url\([\'"]?([^\'"]+?)[\'"]?\)')
    
    candidates = []
        
    for header in headers:
        imgs = header.find_all("img")
        for img in imgs:
            src = img.get('src')
            if not src: continue
            alt = img.get('alt', '')
            class_str = str(img.get('class', '')).lower()
            id_str = str(img.get('id', '')).lower()
            
            if 'logo' in src.lower() or 'logo' in alt.lower() or 'logo' in class_str or 'logo' in id_str:
                if is_valid_logo_url(src, alt):
                    score = 0
                    if src.lower().endswith('/logo.png') or src.lower().endswith('/logo.svg') or src.lower().endswith('/logo.jpg'):
                        score += 10
                    if 'header' in class_str or 'brand' in class_str:
                        score += 5
                    candidates.append((score, urljoin(base_url, src)))
                    
        # Check background images
        for tag in header.find_all(True):
            style = tag.get('style', '')
            if 'background' in style.lower() and 'url' in style.lower():
                match = bg_regex.search(style)
                if match:
                    bg_url = match.group(1)
                    if 'logo' in bg_url.lower() and is_valid_logo_url(bg_url):
                        score = 0
                        if bg_url.lower().endswith('/logo.png') or bg_url.lower().endswith('/logo.svg'): score += 10
                        candidates.append((score, urljoin(base_url, bg_url)))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return ""
