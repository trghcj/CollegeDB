import requests
import logging
import urllib.parse
from typing import Optional, Dict

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

def get_commons_url(filename: str) -> Optional[str]:
    """Fetches the direct image URL for a Wikimedia Commons filename."""
    if not filename.lower().startswith('file:'):
        filename = f"File:{filename}"
        
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": filename,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json"
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if "imageinfo" in page_info:
                    return page_info["imageinfo"][0]["url"]
    except Exception as e:
        logger.error(f"[WikiClient] Error fetching Commons URL for {filename}: {e}")
        
    return None

def search_wikidata_for_college(college_name: str) -> Dict[str, Optional[str]]:
    """
    Searches Wikidata for the college entity and checks for P154 (logo image) and P856 (website).
    Returns a dict with 'logo_url' and 'website'.
    """
    result = {'logo_url': None, 'website': None}
    url = "https://www.wikidata.org/w/api.php"
    search_params = {
        "action": "wbsearchentities",
        "search": college_name,
        "language": "en",
        "format": "json",
        "limit": 1
    }
    
    try:
        response = requests.get(url, params=search_params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            search_results = data.get("search", [])
            if not search_results:
                return result
                
            entity_id = search_results[0]["id"]
            
            # Fetch claims for this entity
            claims_params = {
                "action": "wbgetclaims",
                "entity": entity_id,
                "format": "json"
            }
            claims_response = requests.get(url, params=claims_params, headers=HEADERS, timeout=10)
            if claims_response.status_code == 200:
                claims_data = claims_response.json()
                claims = claims_data.get("claims", {})
                
                # Check for Logo (P154)
                if "P154" in claims:
                    datavalue = claims["P154"][0].get("mainsnak", {}).get("datavalue", {})
                    if datavalue.get("type") == "string":
                        filename = datavalue.get("value")
                        logger.info(f"[WikiClient] Found Wikidata logo for {college_name}: {filename}")
                        result['logo_url'] = get_commons_url(filename)
                        
                # Check for Official Website (P856)
                if "P856" in claims:
                    datavalue = claims["P856"][0].get("mainsnak", {}).get("datavalue", {})
                    if datavalue.get("type") == "string":
                        website = datavalue.get("value")
                        logger.info(f"[WikiClient] Found Wikidata website for {college_name}: {website}")
                        result['website'] = website
                        
    except Exception as e:
        logger.error(f"[WikiClient] Error querying Wikidata for {college_name}: {e}")
        
    return result

def search_commons_directly(college_name: str) -> Optional[str]:
    """
    Searches Wikimedia Commons directly for a file titled with the college name and 'logo'.
    """
    url = "https://commons.wikimedia.org/w/api.php"
    query = f'"{college_name}" logo'
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"intitle:{query}",
        "srnamespace": "6", # File namespace
        "format": "json",
        "limit": 1
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get("query", {}).get("search", [])
            if results:
                title = results[0]["title"]
                logger.info(f"[WikiClient] Found direct Commons logo for {college_name}: {title}")
                return get_commons_url(title)
    except Exception as e:
        logger.error(f"[WikiClient] Error querying Commons directly for {college_name}: {e}")
        
    return None

def get_official_data(college_name: str) -> Dict[str, Optional[str]]:
    """Orchestrates Wikidata -> Commons search."""
    data = search_wikidata_for_college(college_name)
    
    if not data['logo_url']:
        # If Wikidata logo fails, try direct Commons search
        data['logo_url'] = search_commons_directly(college_name)
        
    return data
