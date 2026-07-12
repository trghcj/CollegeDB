import requests
import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

BAD_KEYWORDS = ['born', 'actor', 'actress', 'politician', 'author', 'company', 'film', 'movie', 'district', 'village', 'town', 'city', 'book', 'novel', 'album']
GOOD_KEYWORDS = ['institute', 'university', 'college', 'school', 'academy']

def get_wikidata_id(title: str) -> str:
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageprops",
        "titles": title,
        "format": "json"
    }
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for page_id, info in pages.items():
                return info.get("pageprops", {}).get("wikibase_item", "")
    except Exception as e:
        logger.error(f"[WikiSearch] Error getting wikidata ID for {title}: {e}")
    return ""

def search_wikipedia(college_name: str) -> tuple[str, str]:
    """
    Searches Wikipedia and resolves disambiguation/relevance.
    Automatically handles hyphenated names (e.g. 'IIT Delhi - Indian Institute of Technology').
    Returns (wikipedia_title, wikidata_id).
    """
    url = "https://en.wikipedia.org/w/api.php"
    
    # Generate search variants
    variants = [college_name]
    best_title = ""
    best_score = -1
    
    for search_term in variants:
        if len(search_term) < 3: continue
        
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_term,
            "format": "json",
            "utf8": 1,
            "srlimit": 5
        }
        
        for attempt in range(3):
            try:
                resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
                if resp.status_code == 429:
                    import time
                    time.sleep(2)
                    continue
                if resp.status_code != 200: 
                    break
                    
                results = resp.json().get("query", {}).get("search", [])
                for res in results:
                    title = res["title"]
                    snippet = res.get("snippet", "").lower()
                    
                    # Reject bad entities
                    if any(bad in snippet or bad in title.lower() for bad in BAD_KEYWORDS):
                        continue
                        
                    import re
                    clean_snippet = re.sub(r'<[^>]+>', '', snippet).lower()
                    
                    score = fuzz.ratio(search_term.lower(), title.lower())
                    
                    # Boost if acronym matches title
                    acronym = "".join([w[0] for w in search_term.replace('-', ' ').split() if w.lower() not in ['of', 'and', 'the', 'for', 'in', '&']]).upper()
                    if len(acronym) >= 3 and acronym in title.upper().replace(' ', ''):
                        score += 50
                        
                    # Boost if search term is heavily present in snippet
                    if search_term.lower() in clean_snippet:
                        score += 30
                    elif len(search_term) > 10 and fuzz.partial_ratio(search_term.lower(), clean_snippet) > 90:
                        score += 20
                    
                    # Boost if it contains good keywords
                    if any(good in title.lower() or good in snippet for good in GOOD_KEYWORDS):
                        score += 15
                        
                    # Penalize regional campuses if 'campus' not in search term
                    if 'campus' in title.lower() and 'campus' not in search_term.lower():
                        score -= 50
                        
                    if score > best_score:
                        best_score = score
                        best_title = title
                        
                break # If we succeed, break out of retry loop
                        
            except Exception as e:
                logger.error(f"[WikiSearch] Search failed for {search_term}: {e}")
                import time
                time.sleep(1)
            
    if best_title:
        wd_id = get_wikidata_id(best_title)
        return best_title, wd_id
        
    return "", ""
