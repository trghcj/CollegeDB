import requests
import mwparserfromhell
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

def get_infobox_logo(wikipedia_title: str) -> str:
    """
    Priority 3: Fetches wikitext and parses the infobox for logo parameters.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": wikipedia_title,
        "format": "json"
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for page_id, info in pages.items():
                if "revisions" in info:
                    content = info["revisions"][0]["slots"]["main"]["*"]
                    
                    wikicode = mwparserfromhell.parse(content)
                    templates = wikicode.filter_templates()
                    
                    for tpl in templates:
                        if 'infobox' in str(tpl.name).lower():
                            for param in ['logo', 'image', 'emblem', 'crest']:
                                if tpl.has(param):
                                    val = str(tpl.get(param).value).strip()
                                    if val and not val.startswith('<!--'):
                                        # Clean up brackets or comments if any
                                        val = val.split('<')[0].split('|')[0].strip()
                                        if 'px' not in val.lower():
                                            logger.info(f"[Resolver] Found Infobox logo for {wikipedia_title}: {val}")
                                            return val
    except Exception as e:
        logger.error(f"[Resolver] Error parsing Infobox for {wikipedia_title}: {e}")
        
    return ""

def score_page_image(filename: str) -> int:
    score = 0
    name = filename.lower()
    
    # Positive
    if name.endswith('.svg'): score += 150
    if 'logo' in name: score += 120
    if 'seal' in name: score += 100
    if 'crest' in name: score += 100
    if 'emblem' in name: score += 100
    if name.endswith('.png'): score += 80
    
    # Negative
    bad_words = ['campus', 'students', 'building', 'gallery', 'event', 'banner', 'hero', 'faculty', 'map', 'portrait']
    for bad in bad_words:
        if bad in name:
            score -= 500
            
    return score

def get_best_page_image(wikipedia_title: str) -> str:
    """
    Priority 4: Fetches all images on the page and scores them.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "images",
        "titles": wikipedia_title,
        "imlimit": 50,
        "format": "json"
    }
    
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for page_id, info in pages.items():
                if "images" in info:
                    images = [img["title"] for img in info["images"]]
                    
                    best_score = -9999
                    best_img = ""
                    
                    for img in images:
                        if img.lower().endswith('.svg') or img.lower().endswith('.png') or img.lower().endswith('.jpg'):
                            score = score_page_image(img)
                            if score > best_score:
                                best_score = score
                                best_img = img
                                
                    if best_score > 0 and best_img:
                        logger.info(f"[Resolver] Found Page Image for {wikipedia_title} (Score: {best_score}): {best_img}")
                        return best_img
    except Exception as e:
        logger.error(f"[Resolver] Error fetching page images for {wikipedia_title}: {e}")
        
    return ""
