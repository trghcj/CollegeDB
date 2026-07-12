import os
import shutil
from rapidfuzz import fuzz

UNILOGO_DIR = os.path.join("UniLogo", "images", "img_transparent")

def search_unilogo(college_name: str, save_dir: str = 'logos') -> str:
    """Tier 0: Local UniLogo Repository Search"""
    if not os.path.exists(UNILOGO_DIR):
        return ""
        
    # Get list of all available logos
    available_files = os.listdir(UNILOGO_DIR)
    
    best_match = None
    best_score = 0
    
    # Simple string normalization
    query = college_name.lower().replace(',', '').replace('-', ' ').replace('_', ' ')
    
    for file in available_files:
        if not file.endswith('.png'): continue
        
        # Remove .png and normalize
        filename_no_ext = file[:-4].lower().replace(',', '').replace('-', ' ').replace('_', ' ')
        
        # We need an extremely high confidence match to avoid mismatched colleges
        score = fuzz.ratio(query, filename_no_ext)
        if score > best_score:
            best_score = score
            best_match = file
            
    # Require 98% match to avoid confusing IIT Kanpur with IIT Kharagpur
    if best_score >= 98 and best_match:
        source_path = os.path.join(UNILOGO_DIR, best_match)
        
        # Clean college name for save_path
        import re
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', college_name)
        safe_name = re.sub(r'_+', '_', safe_name).strip('_').lower()
        save_path = os.path.join(save_dir, f"{safe_name}.png")
        
        os.makedirs(save_dir, exist_ok=True)
        shutil.copy2(source_path, save_path)
        return save_path
        
    return ""
