import os
import csv
import logging
import pandas as pd
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# New Wikipedia-First modules
from scraper.wiki_search import search_wikipedia
from scraper.wikidata_logo import get_wikidata_logo
from scraper.logo_resolver import get_infobox_logo, get_best_page_image
from scraper.path_checker import check_common_paths
from scraper.html_extractor import fetch_homepage, get_favicon, get_og_image, get_json_ld_logo, get_header_logo
from scraper.commons_downloader import resolve_commons_url, download_commons_logo, search_commons
from scraper.website_search import search_official_website, search_github_logo, search_filetype, search_ddg_image, extract_domain
from scraper.logo_downloader import download_logo
from scraper.image_validator import is_valid_logo
from scraper.unilogo_search import search_unilogo

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    filename='logs/scraper.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

INPUT_CSV = 'colleges.csv'
OUTPUT_CSV = 'engineering_colleges.csv'
FAILED_CSV = 'failed.csv'
MAX_WORKERS = 1

def validate_and_return(local_path, result_dict, source, url, confidence, original_name):
    if local_path and is_valid_logo(local_path):
        result_dict['Logo Source'] = source
        result_dict['Logo URL'] = url
        result_dict['Logo Path'] = local_path
        result_dict['Confidence'] = confidence
        result_dict['status'] = 'success'
        logger.info(f"[{original_name}] Successfully downloaded valid logo via {source}")
        return True
    elif local_path:
        os.remove(local_path)
    return False

import re

def clean_search_name(name: str) -> str:
    # If there is a hyphen, usually one part is an abbreviation and the other is the full name.
    # Take the longest part to ensure Wikipedia search works.
    parts = str(name).split('-')
    if len(parts) > 1:
        name = max(parts, key=len).strip()
        
    name = name.replace(',', ' ')
    name = name.replace('&', 'and')
    # Remove things in parentheses
    name = re.sub(r'\(.*?\)', '', name)
    # Strip extra whitespace
    return re.sub(r'\s+', ' ', name).strip()

def process_college(college_data: dict) -> dict:
    time.sleep(1)
    original_name = college_data['college_name']
    
    result = {
        'College Name': original_name,
        'City': college_data['city'],
        'State': college_data['state'],
        'Rank': college_data.get('rank', ''),
        'Wikipedia Page': '',
        'Wikidata ID': '',
        'Logo Source': '',
        'Logo URL': '',
        'Logo Path': '',
        'Confidence': '',
        'status': 'failed',
        'reason': ''
    }
    
    try:
        search_name = clean_search_name(original_name)
        logger.info(f"Original: {original_name} -> Cleaned Search: {search_name}")
        
        # ---------------------------------------------------------
        # TIER 0: Local UniLogo Match
        # ---------------------------------------------------------
        unilogo_path = search_unilogo(search_name)
        if validate_and_return(unilogo_path, result, "Tier 0: UniLogo GitHub Repo", "Local Repository", "Very High", original_name):
            return result
        
        # ---------------------------------------------------------
        # TIER 1: Wikipedia Pipeline
        # ---------------------------------------------------------
        wiki_title, wiki_id = search_wikipedia(search_name)
        result['Wikipedia Page'] = wiki_title
        result['Wikidata ID'] = wiki_id
        
        filename = ""
        source = ""
        
        if wiki_id:
            filename = get_wikidata_logo(wiki_id)
            if filename: source = "Tier 1: Wikidata P154"
                
        if not filename and wiki_title:
            filename = get_infobox_logo(wiki_title)
            if filename: source = "Tier 1: Wikipedia Infobox"
                
        if not filename and wiki_title:
            filename = get_best_page_image(wiki_title)
            if filename: source = "Tier 1: Wikipedia Page Image"
                
        if filename:
            url = resolve_commons_url(filename)
            if url:
                local_path = download_commons_logo(url, original_name)
                if validate_and_return(local_path, result, source, url, "Very High (Wikipedia)", original_name):
                    return result

        # ---------------------------------------------------------
        # TIER 2: Website Search Pipeline
        # ---------------------------------------------------------
        website = search_official_website(search_name, college_data.get('city', ''), college_data.get('state', ''))
        if website:
            domain = extract_domain(website)
            
            # (Favicon API demoted to Tier 8)
            
            html_content, soup = fetch_homepage(website)
            
            # TIER 3: Favicon
            favicon_url = get_favicon(soup, website)
            if favicon_url:
                local_path = download_logo(favicon_url, original_name)
                if validate_and_return(local_path, result, "Tier 3: Favicon HTML", favicon_url, "High", original_name):
                    return result
                    
            # TIER 4: OpenGraph Image
            og_url = get_og_image(soup, website)
            if og_url:
                local_path = download_logo(og_url, original_name)
                if validate_and_return(local_path, result, "Tier 4: OpenGraph", og_url, "High", original_name):
                    return result
                    
            # TIER 5: Header Logo
            header_url = get_header_logo(soup, website)
            if header_url:
                local_path = download_logo(header_url, original_name)
                if validate_and_return(local_path, result, "Tier 5: Header Logo", header_url, "Medium", original_name):
                    return result
                    
            # TIER 6: JSON-LD Structured Data
            ld_url = get_json_ld_logo(soup, website)
            if ld_url:
                local_path = download_logo(ld_url, original_name)
                if validate_and_return(local_path, result, "Tier 6: JSON-LD", ld_url, "Medium", original_name):
                    return result
                    
            # TIER 7: Common Paths
            path_url = check_common_paths(website)
            if path_url:
                local_path = download_logo(path_url, original_name)
                if validate_and_return(local_path, result, "Tier 7: Common Path", path_url, "Medium", original_name):
                    return result

        # ---------------------------------------------------------
        # Search Engine Fallbacks (Tiers 8-10)
        # ---------------------------------------------------------
        
        # TIER 8: GitHub Search
        github_url = search_github_logo(search_name)
        if github_url:
            local_path = download_logo(github_url, original_name)
            if validate_and_return(local_path, result, "Tier 8: GitHub", github_url, "Medium", original_name):
                return result
                
        # TIER 9: Filetype Search
        filetype_url = search_filetype(search_name, "png") or search_filetype(search_name, "svg")
        if filetype_url:
            local_path = download_logo(filetype_url, original_name)
            if validate_and_return(local_path, result, "Tier 9: Filetype Search", filetype_url, "Low", original_name):
                return result
                
        # TIER 10: DuckDuckGo Image Search
        ddg_image_url = search_ddg_image(search_name)
        if ddg_image_url:
            local_path = download_logo(ddg_image_url, original_name)
            if validate_and_return(local_path, result, "Tier 10: DDG Images", ddg_image_url, "Low", original_name):
                return result

        result['reason'] = 'All Tiers Exhausted'
        logger.warning(f"[{original_name}] All Tiers exhausted. Failed.")
        
    except Exception as e:
        logger.error(f"Error processing {original_name}: {e}")
        result['reason'] = f'Exception: {e}'
        
    return result

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return
        
    df = pd.read_csv(INPUT_CSV)
    col_map = {c.lower().strip(): c for c in df.columns}
    name_col = col_map.get('college name', col_map.get('college_name', col_map.get('name')))
    city_col = col_map.get('city')
    state_col = col_map.get('state')
    rank_col = col_map.get('rank')
    
    if not name_col:
        print("Could not find a valid college name column in CSV.")
        return
        
    processed_names = set()
    if os.path.exists(OUTPUT_CSV):
        try:
            out_df = pd.read_csv(OUTPUT_CSV)
            if 'College Name' in out_df.columns:
                processed_names.update(out_df['College Name'].dropna().astype(str).str.strip().tolist())
        except Exception:
            pass
            
    if os.path.exists(FAILED_CSV):
        try:
            fail_df = pd.read_csv(FAILED_CSV)
            if 'College Name' in fail_df.columns:
                processed_names.update(fail_df['College Name'].dropna().astype(str).str.strip().tolist())
        except Exception:
            pass

    to_process = []
    for _, row in df.iterrows():
        name = str(row[name_col]).strip()
        if not name or name == 'nan': continue
        if name in processed_names: continue
            
        to_process.append({
            'college_name': name,
            'city': str(row[city_col]).strip() if city_col and pd.notnull(row[city_col]) else "Unknown",
            'state': str(row[state_col]).strip() if state_col and pd.notnull(row[state_col]) else "Unknown",
            'rank': str(row[rank_col]).strip() if rank_col and pd.notnull(row[rank_col]) else ""
        })
    
    logger.info(f"Total to process: {len(to_process)}")
    if not to_process:
        print("All colleges have already been processed.")
        return

    out_file_exists = os.path.exists(OUTPUT_CSV)
    fail_file_exists = os.path.exists(FAILED_CSV)
    
    with open(OUTPUT_CSV, mode='a', newline='', encoding='utf-8') as out_f, \
         open(FAILED_CSV, mode='a', newline='', encoding='utf-8') as fail_f:
         
        out_writer = csv.DictWriter(out_f, fieldnames=['College Name', 'City', 'State', 'Rank', 'Wikipedia Page', 'Wikidata ID', 'Logo Source', 'Logo URL', 'Logo Path', 'Confidence'])
        fail_writer = csv.DictWriter(fail_f, fieldnames=['College Name', 'Reason'])
        
        if not out_file_exists: out_writer.writeheader()
        if not fail_file_exists: fail_writer.writeheader()
            
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_college = {executor.submit(process_college, c): c for c in to_process}
            
            for future in tqdm(as_completed(future_to_college), total=len(to_process), desc="Scraping Logos"):
                try:
                    res = future.result()
                    if res['status'] == 'success':
                        out_writer.writerow({k: res[k] for k in out_writer.fieldnames})
                        out_f.flush()
                    else:
                        fail_writer.writerow({'College Name': res['College Name'], 'Reason': res['reason']})
                        fail_f.flush()
                except Exception as exc:
                    logger.error(f"Exception generated: {exc}")

if __name__ == "__main__":
    main()
