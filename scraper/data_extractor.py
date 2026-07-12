import requests
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 CollegeDB-Bot/1.0'
}

def clean_text(text: str) -> str:
    """Removes citations like [1], [2] and extra whitespace."""
    if not text:
        return ""
    text = re.sub(r'\[\d+\]', '', text)
    # Remove hidden spans or extra breaks
    return re.sub(r'\s+', ' ', text).strip()

def extract_college_details(wiki_title: str) -> dict:
    """
    Fetches the Wikipedia page for a given title and parses the infobox 
    to extract City, State, and Rank.
    """
    data = {
        'City': 'Unknown',
        'State': 'Unknown',
        'Rank': ''
    }
    
    if not wiki_title:
        return data

    url = f"https://en.wikipedia.org/wiki/{wiki_title.replace(' ', '_')}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return data
            
        soup = BeautifulSoup(response.content, 'html.parser')
        infobox = soup.find('table', class_='infobox')
        
        if not infobox:
            return data
            
        rows = infobox.find_all('tr')
        
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
                
            header = th.get_text(strip=True).lower()
            value = clean_text(td.get_text(separator=' ', strip=True))
            
            # Location parsing
            if header in ['location', 'city']:
                parts = [p.strip() for p in value.split(',')]
                if len(parts) >= 3:
                    # Usually: ..., City, State, Country
                    data['State'] = parts[-2]
                    data['City'] = parts[-3]
                elif len(parts) == 2:
                    data['City'] = parts[0]
                    data['State'] = parts[1]
                else:
                    data['City'] = parts[0]
                    
            elif header == 'state' or header == 'province':
                data['State'] = value
                
            # Rank parsing (e.g., "NIRF ranking", "Rankings", "National rank")
            elif 'rank' in header or 'nirf' in header:
                data['Rank'] = value
                
        # If still missing rank, look for text containing NIRF anywhere in infobox
        if not data['Rank']:
            for td in infobox.find_all('td'):
                td_text = clean_text(td.get_text(separator=' ', strip=True))
                if 'NIRF' in td_text or 'Rank' in td_text:
                    # simplistic extraction: find numbers near the word NIRF
                    match = re.search(r'(?:NIRF|Rank).*?(\d+)', td_text, re.IGNORECASE)
                    if match:
                        data['Rank'] = match.group(1)
                        break
                
        logger.info(f"[DataExtractor] Extracted details for {wiki_title}: {data}")
        
    except Exception as e:
        logger.error(f"[DataExtractor] Error parsing Wikipedia for {wiki_title}: {e}")
        
    return data
