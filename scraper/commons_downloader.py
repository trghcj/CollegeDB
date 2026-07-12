import requests
import logging
import os
import re
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

def to_snake_case(name: str) -> str:
    name = re.sub(r'[^a-zA-Z0-9]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name.lower()

def resolve_commons_url(filename: str) -> str:
    if not filename.lower().startswith('file:'):
        filename = f"File:{filename}"
        
    url = "https://en.wikipedia.org/w/api.php"
    is_svg = filename.lower().endswith('.svg')
    params = {
        "action": "query",
        "titles": filename,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    if is_svg:
        params["iiurlwidth"] = 500
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for page_id, info in pages.items():
                if "imageinfo" in info:
                    if is_svg and "thumburl" in info["imageinfo"][0]:
                        return info["imageinfo"][0]["thumburl"]
                    return info["imageinfo"][0]["url"]
    except Exception as e:
        logger.error(f"[Commons] Error resolving URL for {filename}: {e}")
        
    return ""

def download_commons_logo(url: str, college_name: str, save_dir: str = 'logos') -> str:
    if not url:
        return ""
    if url.lower().endswith('.svg'):
        logger.warning(f"Rejected SVG from Commons: {url}")
        return ""
        
    blacklisted = ['flag', 'emblem', 'netflix', 'microsoft', 'apple', 'google', 'g20', 'g-20', 'amrit', 'mahotsav', 'azadi']
    if any(b in url.lower() for b in blacklisted):
        logger.warning(f"Rejected blacklisted Commons URL: {url}")
        return ""
        
    os.makedirs(save_dir, exist_ok=True)
    base_name = to_snake_case(college_name)
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        
        # Check initial extension
        ext = os.path.splitext(urllib_parse_path(url))[1].lower()
        
        content_type = resp.headers.get('Content-Type', '').lower()
        if 'image/svg' in content_type or ext == '.svg':
            ext = '.svg'
        elif 'image/jpeg' in content_type or 'image/jpg' in content_type:
            ext = '.jpg'
        elif 'image/png' in content_type:
            ext = '.png'
        elif 'image/webp' in content_type:
            ext = '.webp'
            
        if ext == '.svg':
            save_path = os.path.join(save_dir, f"{base_name}.svg")
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return save_path
            
        # Pillow processing
        try:
            img = Image.open(BytesIO(resp.content))
            if img.format == 'WEBP':
                img = img.convert('RGBA')
                ext = '.png'
                save_path = os.path.join(save_dir, f"{base_name}{ext}")
                img.save(save_path, 'PNG')
                return save_path
                
            if img.format == 'JPEG': ext = '.jpg'
            elif img.format == 'PNG': ext = '.png'
            
            save_path = os.path.join(save_dir, f"{base_name}{ext}")
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return save_path
            
        except Exception:
            # Fallback to raw save if Pillow fails
            if ext == '.png':
                save_path = os.path.join(save_dir, f"{base_name}{ext}")
                with open(save_path, 'wb') as f:
                    f.write(resp.content)
                return save_path
                
    except Exception as e:
        logger.error(f"[Commons] Download failed for {url}: {e}")
        
    return ""

def urllib_parse_path(url):
    import urllib.parse
    return urllib.parse.urlparse(url).path

def search_commons(college_name: str) -> str:
    """Tier 9: Direct Wikimedia Commons Search"""
    url = "https://commons.wikimedia.org/w/api.php"
    query = f"{college_name} logo"
    
    # Try different queries if hyphenated
    variants = [query]
    if '-' in college_name:
        variants.append(f"{college_name.split('-')[0].strip()} logo")
        
    for q in variants:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": q,
            "srnamespace": "6", # Namespace 6 is File
            "format": "json"
        }
        
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
            if resp.status_code == 200:
                results = resp.json().get("query", {}).get("search", [])
                for res in results:
                    title = res["title"]
                    # Strictly check it's an image
                    if title.lower().endswith(('.svg', '.png', '.jpg', '.jpeg')):
                        # Resolve url
                        file_url = resolve_commons_url(title)
                        if file_url:
                            return file_url
        except Exception as e:
            logger.error(f"[Commons] Search failed for {q}: {e}")
            
    return ""
