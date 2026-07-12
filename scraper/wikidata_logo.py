import requests
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

def get_wikidata_logo(entity_id: str) -> str:
    """
    Given a Wikidata entity ID (e.g. Q123456), queries for the P154 property (Logo image).
    Returns the filename if found, else empty string.
    """
    if not entity_id:
        return ""
        
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetclaims",
        "entity": entity_id,
        "property": "P154",
        "format": "json"
    }
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            claims = data.get("claims", {}).get("P154", [])
            if claims:
                datavalue = claims[0].get("mainsnak", {}).get("datavalue", {})
                if datavalue.get("type") == "string":
                    filename = datavalue.get("value")
                    logger.info(f"[Wikidata] Found P154 logo for {entity_id}: {filename}")
                    return filename
    except Exception as e:
        logger.error(f"[Wikidata] Error getting P154 for {entity_id}: {e}")
        
    return ""
