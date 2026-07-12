import os
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def is_valid_logo(image_path: str) -> bool:
    """
    Validates if a downloaded image is actually a logo and not a photograph.
    Returns True if it's a valid logo, False if it looks like a photo.
    """
    if not os.path.exists(image_path):
        return False
        
    try:
        # SVG files are almost always vectors/logos
        if image_path.lower().endswith('.svg'):
            return True
            
        with Image.open(image_path) as img:
            # Convert to RGBA to check for transparency
            img = img.convert('RGBA')
            
            # 1. Size check: Very large images are usually photos/banners, tiny images are favicons
            width, height = img.size
            if width > 1200 or height > 1200:
                logger.info(f"Rejected {image_path}: Too large ({width}x{height})")
                return False
            if width < 100 and height < 100:
                logger.info(f"Rejected {image_path}: Too small ({width}x{height})")
                return False
                
            # 2. Aspect Ratio: Extreme panoramic banners are not logos
            aspect_ratio = max(width, height) / min(width, height)
            if aspect_ratio > 3.0:
                logger.info(f"Rejected {image_path}: Extreme aspect ratio ({aspect_ratio:.1f})")
                return False
                
            # 3. Transparency check: WE NOW STRICTLY REQUIRE TRANSPARENCY
            # Sample pixels to find any fully transparent one
            extrema = img.getextrema()
            if len(extrema) == 4: # RGBA
                alpha_min, alpha_max = extrema[3]
                if alpha_min < 255:
                    return True # Has transparency -> Valid Logo!
            
            logger.info(f"Rejected {image_path}: Missing transparency (Likely a photo or banner)")
            return False
            
    except Exception as e:
        logger.error(f"Error validating image {image_path}: {e}")
        return False
