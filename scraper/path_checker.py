import requests
import logging
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

COMMON_PATHS = [
    "/logo.png",
    "/logo.svg",
    "/images/logo.png",
    "/images/logo.svg",
    "/assets/logo.png",
    "/assets/images/logo.png",
    "/static/logo.png",
    "/themes/logo.svg",
    "/uploads/logo.png"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check_common_paths(base_url: str) -> str:
    """Tier 6: Common Logo Paths"""
    if not base_url: return ""
    if not base_url.startswith('http'):
        base_url = 'https://' + base_url
        
    for path in COMMON_PATHS:
        url = urljoin(base_url, path)
        try:
            # Use HEAD request for efficiency
            resp = requests.head(url, headers=HEADERS, timeout=5, verify=False)
            if resp.status_code == 200:
                content_type = resp.headers.get('Content-Type', '').lower()
                if 'image' in content_type:
                    return url
            # Sometimes servers block HEAD but allow GET
            elif resp.status_code == 405:
                resp_get = requests.get(url, headers=HEADERS, timeout=5, verify=False, stream=True)
                if resp_get.status_code == 200:
                    content_type = resp_get.headers.get('Content-Type', '').lower()
                    if 'image' in content_type:
                        return url
        except Exception:
            continue
            
    return ""
