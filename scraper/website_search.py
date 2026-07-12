import time
import logging
import urllib.parse
from ddgs import DDGS
from ddgs.exceptions import RatelimitException

logger = logging.getLogger(__name__)

IGNORE_KEYWORDS = [
    'wikipedia.org', 'careers360.com', 'collegedunia.com', 'shiksha.com',
    'getmyuni.com', 'collegedekho.com', 'linkedin.com', 'facebook.com',
    'instagram.com', 'twitter.com', 'youtube.com', 'justdial.com',
    'indiatoday.in', 'news', 'blog', 'indianculture.gov.in',
    'aicte-india.org', 'ugc.ac.in', 'mhrd.gov.in', 'nirfindia.org',
    'education.gov.in', 'nba-india.org', 'india.gov.in', 'netflix', 'microsoft',
    'apple', 'google', 'flag', 'emblem', 'reddit', 'byju', 'host', 'medium', 'quora', 'pinterest',
    'glassdoor', 'ambitionbox', 'naukri', 'indeed', 'mouthshut', 'justdial',
    'wordpress', 'blogspot', 'wix', 'weebly', 'site123', 'squarespace', 'netlify', 'vercel'
]

def extract_domain(url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc.lower().replace('www.', '')
    except Exception:
        return ""

def is_ignored(url: str) -> bool:
    url_lower = url.lower()
    domain = extract_domain(url_lower)
    for kw in IGNORE_KEYWORDS:
        if kw in url_lower or kw in domain:
            return True
    return False

def get_domain_priority(domain: str) -> int:
    if domain.endswith('.ac.in'):
        return 1
    elif domain.endswith('.edu.in'):
        return 2
    elif domain.endswith('.edu'):
        return 3
    elif domain.endswith('.org.in') or domain.endswith('.res.in') or domain.endswith('.ernet.in') or domain.endswith('.gov.in'):
        return 4
    return 99

import threading

search_lock = threading.Lock()

import requests

def search_clearbit(college_name: str) -> str:
    url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(college_name)}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and isinstance(data, list):
                for item in data:
                    if item.get('domain'):
                        return f"https://{item['domain']}/"
    except Exception as e:
        logger.debug(f"Clearbit error: {e}")
    return ""

def search_wikipedia_extlinks(college_name: str) -> str:
    # First search wiki to get the exact title
    import requests
    from collections import Counter
    headers = {'User-Agent': 'CollegeDB-Bot/1.0'}
    search_url = "https://en.wikipedia.org/w/api.php"
    search_params = {"action": "query", "list": "search", "srsearch": college_name, "format": "json", "utf8": 1, "srlimit": 1}
    try:
        s_resp = requests.get(search_url, headers=headers, params=search_params, timeout=5).json()
        results = s_resp.get("query", {}).get("search", [])
        if not results: return ""
        title = results[0]["title"]
        
        # Now get extlinks for this title
        ext_params = {"action": "query", "prop": "extlinks", "titles": title, "ellimit": 500, "format": "json"}
        e_resp = requests.get(search_url, headers=headers, params=ext_params, timeout=5).json()
        pages = e_resp.get("query", {}).get("pages", {})
        if not pages: return ""
        extlinks = list(pages.values())[0].get('extlinks', [])
        
        domain_counts = Counter()
        domain_to_url = {}
        
        for l in extlinks:
            url = l.get('*', '')
            if url and 'http' in url and not is_ignored(url):
                domain = extract_domain(url)
                priority = get_domain_priority(domain)
                if priority < 99:
                    domain_counts[domain] += 1
                    # Save the shortest URL for this domain (usually the homepage)
                    if domain not in domain_to_url or len(url) < len(domain_to_url[domain]):
                        domain_to_url[domain] = url
        
        if domain_counts:
            # Get the most frequent high-priority domain
            best_domain = domain_counts.most_common(1)[0][0]
            return domain_to_url[best_domain]
    except Exception as e:
        logger.debug(f"Wiki extlinks error: {e}")
    return ""

def search_official_website(college_name: str, city: str = "", state: str = "", max_retries: int = 3) -> str:
    # 1. Fast, highly accurate lookup
    cb_url = search_clearbit(college_name)
    if cb_url:
        logger.info(f"Found official website via Clearbit: {cb_url}")
        return cb_url
        
    # 2. Wikipedia External Links lookup
    wiki_url = search_wikipedia_extlinks(college_name)
    if wiki_url:
        logger.info(f"Found official website via Wikipedia ExtLinks: {wiki_url}")
        return wiki_url

    # 3. Fallback to DDGS (rate-limited)
    query = f"{college_name} official website"
    
    for attempt in range(max_retries):
        try:
            with search_lock:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=15))
                
                valid_urls = []
                for res in results:
                    url = res.get('href', '')
                    if url and not is_ignored(url):
                        valid_urls.append(url)
                
                if not valid_urls:
                    print(f"DEBUG: No valid urls for {query}")
                    return ""
                    
                # Rank valid URLs based on domain priority
                ranked_urls = []
                # Extract long words from college name to match against domains
                import re
                ignore_words = ['college', 'institute', 'engineering', 'technology', 'university', 'science', 'school', 'management', 'research', 'academy']
                if city: ignore_words.extend(city.lower().split())
                if state: ignore_words.extend(state.lower().split())
                name_words = [w.lower() for w in re.split(r'\W+', college_name) if len(w) >= 5 and w.lower() not in ignore_words]
                
                for url in valid_urls:
                    domain = extract_domain(url)
                    priority = get_domain_priority(domain)
                    
                    # Boost priority if a unique word from the college name is in the domain
                    matched_words = sum(1 for w in name_words if w in domain)
                    priority -= (matched_words * 2) # Heavily boost matching domains
                    
                    print(f"DEBUG: Domain {domain} priority {priority}")
                    if priority < 99:
                        ranked_urls.append((priority, url))
                    
                if not ranked_urls:
                    print(f"DEBUG: No ranked urls for {query}")
                    continue
                    
                # Sort by priority, then by domain length (to prefer base domains)
                ranked_urls.sort(key=lambda x: (x[0], len(extract_domain(x[1]))))
                
                # Return the best match
                print(f"DEBUG: Best match for {query}: {ranked_urls[0][1]}")
                return ranked_urls[0][1]
                
        except RatelimitException:
            logger.warning(f"DDGS Rate limit hit for {college_name}. Retrying ({attempt+1}/{max_retries})...")
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Error searching for {college_name}: {e}")
            time.sleep(1)
            
    return ""

def search_github_logo(college_name: str, max_retries: int = 2) -> str:
    """Tier 7: Search GitHub for logo files."""
    query = f"site:github.com {college_name} logo.png"
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for res in results:
                    url = res.get('href', '')
                    if url and 'github.com' in url and url.endswith('.png'):
                        return url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
        except Exception as e:
            time.sleep(1)
    return ""

def search_filetype(college_name: str, filetype: str, max_retries: int = 2) -> str:
    """Tier 8: Exact filetype search."""
    query = f"{college_name} logo filetype:{filetype}"
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for res in results:
                    url = res.get('href', '')
                    if url and url.lower().endswith(f".{filetype}"):
                        return url
        except Exception as e:
            time.sleep(1)
    return ""

def search_ddg_image(college_name: str, max_retries: int = 2) -> str:
    """Tier 10: DuckDuckGo Image Search Fallback"""
    query = f"{college_name} logo"
    for attempt in range(max_retries):
        try:
            with DDGS() as ddgs:
                # We specifically look for images with "logo" in the filename/url to avoid event photos
                results = list(ddgs.images(query, max_results=10))
                for res in results:
                    url = res.get('image', '')
                    if url and not any(kw in url.lower() for kw in IGNORE_KEYWORDS):
                        if 'logo' in url.lower() or url.lower().endswith(('.svg', '.png')):
                            return url
        except Exception as e:
            time.sleep(1)
    return ""
