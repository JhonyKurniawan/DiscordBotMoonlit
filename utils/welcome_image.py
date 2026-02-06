"""
Welcome Image Generator
=======================
Generate custom welcome/goodbye images using Pillow.
"""

import io
import asyncio
import os
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import aiohttp

# Default settings
DEFAULT_IMAGE_SIZE = (1000, 400)
DEFAULT_AVATAR_SIZE = 180
DEFAULT_WELCOME_TEXT = "WELCOME"
DEFAULT_GOODBYE_TEXT = "GOODBYE"
DEFAULT_TEXT_COLOR = "#FFD700"  # Gold
DEFAULT_SHADOW_COLOR = "#000000"
DEFAULT_PROFILE_POSITION = "center"

# Cache directory for downloaded Google Fonts
FONT_CACHE_DIR = Path(__file__).parent.parent / 'fonts' / 'cached'
FONT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Custom font upload directory
CUSTOM_FONT_DIR = Path(__file__).parent.parent / 'fonts' / 'custom'
CUSTOM_FONT_DIR.mkdir(parents=True, exist_ok=True)

# Font paths for Windows system fonts
FONTS = {
    'arial': [
        "C:/Windows/Fonts/arialbd.ttf",
        "arialbd.ttf",
        "arial.ttf",
    ],
    'impact': [
        "C:/Windows/Fonts/impact.ttf",
        "impact.ttf",
    ],
    'verdana': [
        "C:/Windows/Fonts/verdanab.ttf",
        "verdanab.ttf",
        "verdana.ttf",
    ],
    'times': [
        "C:/Windows/Fonts/timesbd.ttf",
        "timesbd.ttf",
        "times.ttf",
    ],
    'comic': [
        "C:/Windows/Fonts/comicbd.ttf",
        "comicbd.ttf",
        "comic.ttf",
    ],
    'georgia': [
        "C:/Windows/Fonts/georgiab.ttf",
        "georgiab.ttf",
        "georgia.ttf",
    ],
    'courier': [
        "C:/Windows/Fonts/courbd.ttf",
        "courbd.ttf",
        "cour.ttf",
    ],
    # Additional fonts
    'segoe': [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "segoeui.ttf",
    ],
    'tahoma': [
        "C:/Windows/Fonts/tahomabd.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "tahoma.ttf",
    ],
    'trebuchet': [
        "C:/Windows/Fonts/trebucbd.ttf",
        "C:/Windows/Fonts/trebucon.ttf",
        "trebuc.ttf",
    ],
    'arialblack': [
        "C:/Windows/Fonts/ariblk.ttf",
        "ariblk.ttf",
    ],
    'franklin': [
        "C:/Windows/Fonts/frank.ttf",
        "frank.ttf",
    ],
    'lucida': [
        "C:/Windows/Fonts/lucon.ttf",
        "lucon.ttf",
    ],
    'palatino': [
        "C:/Windows/Fonts/palab.ttf",
        "C:/Windows/Fonts/pala.ttf",
        "pala.ttf",
    ],
    'century': [
        "C:/Windows/Fonts/century.ttf",
        "century.ttf",
    ],
    'rockwell': [
        "C:/Windows/Fonts/rockbd.ttf",
        "C:/Windows/Fonts/rock.ttf",
        "rock.ttf",
    ],
    'calibri': [
        "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "calibri.ttf",
    ],
    'cambria': [
        "C:/Windows/Fonts/cambriab.ttf",
        "C:/Windows/Fonts/cambria.ttf",
        "cambria.ttf",
    ],
    'consolas': [
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "consola.ttf",
    ],
}

# Google Fonts URLs (using direct CDN links for TTF files)
GOOGLE_FONTS = {
    'roboto': {
        'normal': 'https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Me5Q.ttf',
        'bold': 'https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmWUlfw.ttf',
        'italic': 'https://fonts.gstatic.com/s/roboto/v30/KFOkCnqEu92Fr1Mu51xMIzI.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/roboto/v30/KFOjCnqEu92Fr1Mu51TzI.ttf',
    },
    'poppins': {
        'normal': 'https://fonts.gstatic.com/s/poppins/v20/pxiEyp8tv8GLP3w6A.ttf',
        'bold': 'https://fonts.gstatic.com/s/poppins/v20/pxiByp8kv8JHgFVrLEj6Z1xlFd2JQEk.ttf',
        'italic': 'https://fonts.gstatic.com/s/poppins/v20/pxiGyp8tv8GLP3w6A.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/poppins/v20/pxiDyp8kv8JHgFVrJJLmy15lFg.ttf',
    },
    'montserrat': {
        'normal': 'https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Ew-.ttf',
        'bold': 'https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr70E.ttf',
        'italic': 'https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr7Hw.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/montserrat/v25/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCvr78H0.ttf',
    },
    'opensans': {
        'normal': 'https://fonts.gstatic.com/s/opensans/v35/memSYaGs126MiZpBA-UvWbX2vVnXBbObj2OVZyOOSr4dVJWUgsjZ0B4gaVc.ttf',
        'bold': 'https://fonts.gstatic.com/s/opensans/v35/memSYaGs126MiZpBA-UvWbX2vVnXBbObj2OVZyOOSr4dVJWUgsg-1x4gaVc.ttf',
        'italic': 'https://fonts.gstatic.com/s/opensans/v35/memQYaGs126MiZpBA-UFUIcVXSCEkx2cmqvXlWqWuk6F15M.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/opensans/v35/memQYaGs126MiZpBA-UFUIcVXSCEkx2cmqvXlWqWu06F15M.ttf',
    },
    'lato': {
        'normal': 'https://fonts.gstatic.com/s/lato/v24/S6uyw4BMUTPHjx4wXiWtFCc.ttf',
        'bold': 'https://fonts.gstatic.com/s/lato/v24/S6u9w4BMUTPHh6UVSwiPGQ3q5d0.ttf',
        'italic': 'https://fonts.gstatic.com/s/lato/v24/S6u8w4BMUTPHjxsAUi-ejQ.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/lato/v24/S6u_w4BMUTPHjxsI3w-GQlcHKw.ttf',
    },
    'oswald': {
        'normal': 'https://fonts.gstatic.com/s/oswald/v49/TK3_WkUHHAIjg75cFRf3bXL8LICs1_FvsUtiZTaR.ttf',
        'bold': 'https://fonts.gstatic.com/s/oswald/v49/TK3_WkUHHAIjg75cFRf3bXL8LICs18_FvsUtiZTaR.ttf',
        'italic': 'https://fonts.gstatic.com/s/oswald/v49/TK3_WkUHHAIjg75cFRf3bXL8LICs1_FvsUZiZTaR.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/oswald/v49/TK3_WkUHHAIjg75cFRf3bXL8LICs18_FvsUZiZTaR.ttf',
    },
    'raleway': {
        'normal': 'https://fonts.gstatic.com/s/raleway/v28/1Ptug8zYS_SKggPNyC0ITw.ttf',
        'bold': 'https://fonts.gstatic.com/s/raleway/v28/1Ptug8zYS_SKggPNyC0ITw.ttf',
        'italic': 'https://fonts.gstatic.com/s/raleway/v28/1Ptsg8zYS_SKggPNyCg4QIFqPfE.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/raleway/v28/1Ptsg8zYS_SKggPNyCg4QIFqPfE.ttf',
    },
    'ptsans': {
        'normal': 'https://fonts.gstatic.com/s/ptsans/v17/jizaRExUiTo99u79D0KExQ.ttf',
        'bold': 'https://fonts.gstatic.com/s/ptsans/v17/jizfRExUiTo99u79B_mh4Ow.ttf',
        'italic': 'https://fonts.gstatic.com/s/ptsans/v17/jizYRExUiTo99u79D0e0w3mN.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/ptsans/v17/jizdRExUiTo99u79D0e8fOytLQ.ttf',
    },
    'nunito': {
        'normal': 'https://fonts.gstatic.com/s/nunito/v25/XRXV3I6Li01BKofIOOaBTMnFcQIG.ttf',
        'bold': 'https://fonts.gstatic.com/s/nunito/v25/XRXV3I6Li01BKofIOuaBTMnFcQIG.ttf',
        'italic': 'https://fonts.gstatic.com/s/nunito/v25/XRXQ3I6Li01BKofIMN4Y9bnHw.ttf',
        'bolditalic': 'https://fonts.gstatic.com/s/nunito/v25/XRXQ3I6Li01BKofIMN4Y9bnHw.ttf',
    },
    'bebasneue': {
        'normal': 'https://fonts.gstatic.com/s/bebasneue/v14/JTUSjIg69CK48gW7PXoo9WdhyzM.woff2',
        'bold': 'https://fonts.gstatic.com/s/bebasneue/v14/JTUSjIg69CK48gW7PXoo9WdhyzM.woff2',
        'italic': 'https://fonts.gstatic.com/s/bebasneue/v14/JTUSjIg69CK48gW7PXoo9WdhyzM.woff2',
        'bolditalic': 'https://fonts.gstatic.com/s/bebasneue/v14/JTUSjIg69CK48gW7PXoo9WdhyzM.woff2',
    },
}


# Windows font style variants mapping
FONT_VARIANTS = {
    'arial': {
        'normal': ['arial.ttf', 'C:/Windows/Fonts/arial.ttf'],
        'bold': ['arialbd.ttf', 'C:/Windows/Fonts/arialbd.ttf'],
        'italic': ['ariali.ttf', 'C:/Windows/Fonts/ariali.ttf'],
        'bolditalic': ['arialbi.ttf', 'C:/Windows/Fonts/arialbi.ttf'],
    },
    'arialblack': {
        'normal': ['ariblk.ttf', 'C:/Windows/Fonts/ariblk.ttf'],
        'bold': ['ariblk.ttf', 'C:/Windows/Fonts/ariblk.ttf'],
        'italic': ['ariblk.ttf', 'C:/Windows/Fonts/ariblk.ttf'],
        'bolditalic': ['ariblk.ttf', 'C:/Windows/Fonts/ariblk.ttf'],
    },
    'impact': {
        'normal': ['impact.ttf', 'C:/Windows/Fonts/impact.ttf'],
        'bold': ['impact.ttf', 'C:/Windows/Fonts/impact.ttf'],
        'italic': ['impact.ttf', 'C:/Windows/Fonts/impact.ttf'],
        'bolditalic': ['impact.ttf', 'C:/Windows/Fonts/impact.ttf'],
    },
    'verdana': {
        'normal': ['verdana.ttf', 'C:/Windows/Fonts/verdana.ttf'],
        'bold': ['verdanab.ttf', 'C:/Windows/Fonts/verdanab.ttf'],
        'italic': ['verdanai.ttf', 'C:/Windows/Fonts/verdanai.ttf'],
        'bolditalic': ['verdanaz.ttf', 'C:/Windows/Fonts/verdanaz.ttf'],
    },
    'times': {
        'normal': ['times.ttf', 'C:/Windows/Fonts/times.ttf'],
        'bold': ['timesbd.ttf', 'C:/Windows/Fonts/timesbd.ttf'],
        'italic': ['timesi.ttf', 'C:/Windows/Fonts/timesi.ttf'],
        'bolditalic': ['timesbi.ttf', 'C:/Windows/Fonts/timesbi.ttf'],
    },
    'comic': {
        'normal': ['comic.ttf', 'C:/Windows/Fonts/comic.ttf'],
        'bold': ['comicbd.ttf', 'C:/Windows/Fonts/comicbd.ttf'],
        'italic': ['comici.ttf', 'C:/Windows/Fonts/comici.ttf'],
        'bolditalic': ['comicz.ttf', 'C:/Windows/Fonts/comicz.ttf'],
    },
    'georgia': {
        'normal': ['georgia.ttf', 'C:/Windows/Fonts/georgia.ttf'],
        'bold': ['georgiab.ttf', 'C:/Windows/Fonts/georgiab.ttf'],
        'italic': ['georgiai.ttf', 'C:/Windows/Fonts/georgiai.ttf'],
        'bolditalic': ['georgiaz.ttf', 'C:/Windows/Fonts/georgiaz.ttf'],
    },
    'courier': {
        'normal': ['cour.ttf', 'C:/Windows/Fonts/cour.ttf'],
        'bold': ['courbd.ttf', 'C:/Windows/Fonts/courbd.ttf'],
        'italic': ['couri.ttf', 'C:/Windows/Fonts/couri.ttf'],
        'bolditalic': ['courbi.ttf', 'C:/Windows/Fonts/courbi.ttf'],
    },
    'segoe': {
        'normal': ['segoeui.ttf', 'C:/Windows/Fonts/segoeui.ttf'],
        'bold': ['segoeuib.ttf', 'C:/Windows/Fonts/segoeuib.ttf'],
        'italic': ['segoeuii.ttf', 'C:/Windows/Fonts/segoeuii.ttf'],
        'bolditalic': ['segoeuiz.ttf', 'C:/Windows/Fonts/segoeuiz.ttf'],
    },
    'tahoma': {
        'normal': ['tahoma.ttf', 'C:/Windows/Fonts/tahoma.ttf'],
        'bold': ['tahomabd.ttf', 'C:/Windows/Fonts/tahomabd.ttf'],
        'italic': ['tahoma.ttf', 'C:/Windows/Fonts/tahoma.ttf'],
        'bolditalic': ['tahomabd.ttf', 'C:/Windows/Fonts/tahomabd.ttf'],
    },
    'trebuchet': {
        'normal': ['trebuc.ttf', 'C:/Windows/Fonts/trebuc.ttf'],
        'bold': ['trebucbd.ttf', 'C:/Windows/Fonts/trebucbd.ttf'],
        'italic': ['trebucit.ttf', 'C:/Windows/Fonts/trebucit.ttf'],
        'bolditalic': ['trebucbi.ttf', 'C:/Windows/Fonts/trebucbi.ttf'],
    },
    'calibri': {
        'normal': ['calibri.ttf', 'C:/Windows/Fonts/calibri.ttf'],
        'bold': ['calibrib.ttf', 'C:/Windows/Fonts/calibrib.ttf'],
        'italic': ['calibrii.ttf', 'C:/Windows/Fonts/calibrii.ttf'],
        'bolditalic': ['calibriz.ttf', 'C:/Windows/Fonts/calibriz.ttf'],
    },
    'cambria': {
        'normal': ['cambria.ttf', 'C:/Windows/Fonts/cambria.ttf'],
        'bold': ['cambriab.ttf', 'C:/Windows/Fonts/cambriab.ttf'],
        'italic': ['cambriai.ttf', 'C:/Windows/Fonts/cambriai.ttf'],
        'bolditalic': ['cambriaz.ttf', 'C:/Windows/Fonts/cambriaz.ttf'],
    },
    'consolas': {
        'normal': ['consola.ttf', 'C:/Windows/Fonts/consola.ttf'],
        'bold': ['consolab.ttf', 'C:/Windows/Fonts/consolab.ttf'],
        'italic': ['consolai.ttf', 'C:/Windows/Fonts/consolai.ttf'],
        'bolditalic': ['consolaz.ttf', 'C:/Windows/Fonts/consolaz.ttf'],
    },
    'lucida': {
        'normal': ['lucon.ttf', 'C:/Windows/Fonts/lucon.ttf'],
        'bold': ['lucon.ttf', 'C:/Windows/Fonts/lucon.ttf'],
        'italic': ['lucon.ttf', 'C:/Windows/Fonts/lucon.ttf'],
        'bolditalic': ['lucon.ttf', 'C:/Windows/Fonts/lucon.ttf'],
    },
    'palatino': {
        'normal': ['pala.ttf', 'C:/Windows/Fonts/pala.ttf'],
        'bold': ['palab.ttf', 'C:/Windows/Fonts/palab.ttf'],
        'italic': ['palai.ttf', 'C:/Windows/Fonts/palai.ttf'],
        'bolditalic': ['palabi.ttf', 'C:/Windows/Fonts/palabi.ttf'],
    },
    'century': {
        'normal': ['century.ttf', 'C:/Windows/Fonts/century.ttf'],
        'bold': ['century.ttf', 'C:/Windows/Fonts/century.ttf'],
        'italic': ['century.ttf', 'C:/Windows/Fonts/century.ttf'],
        'bolditalic': ['century.ttf', 'C:/Windows/Fonts/century.ttf'],
    },
    'rockwell': {
        'normal': ['rock.ttf', 'C:/Windows/Fonts/rock.ttf'],
        'bold': ['rockbd.ttf', 'C:/Windows/Fonts/rockbd.ttf'],
        'italic': ['rocki.ttf', 'C:/Windows/Fonts/rocki.ttf'],
        'bolditalic': ['rockbi.ttf', 'C:/Windows/Fonts/rockbi.ttf'],
    },
    'franklin': {
        'normal': ['frank.ttf', 'C:/Windows/Fonts/frank.ttf'],
        'bold': ['frank.ttf', 'C:/Windows/Fonts/frank.ttf'],
        'italic': ['frank.ttf', 'C:/Windows/Fonts/frank.ttf'],
        'bolditalic': ['frank.ttf', 'C:/Windows/Fonts/frank.ttf'],
    },
}


async def download_google_font(font_name: str, bold: bool = False, italic: bool = False) -> Optional[str]:
    """Download a Google Font and cache it locally. Returns the path to the cached font."""
    if font_name not in GOOGLE_FONTS:
        return None

    # Determine the variant to use
    if bold and italic:
        variant = 'bolditalic'
    elif bold:
        variant = 'bold'
    elif italic:
        variant = 'italic'
    else:
        variant = 'normal'

    font_url = GOOGLE_FONTS[font_name].get(variant)
    if not font_url:
        font_url = GOOGLE_FONTS[font_name].get('normal')

    # Create cache filename
    import hashlib
    url_hash = hashlib.md5(font_url.encode()).hexdigest()
    cache_filename = f"{font_name}_{variant}_{url_hash}.ttf"
    cache_path = FONT_CACHE_DIR / cache_filename

    # Check if already cached
    if cache_path.exists():
        return str(cache_path)

    # Download the font
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(font_url) as response:
                if response.status == 200:
                    font_data = await response.read()
                    with open(cache_path, 'wb') as f:
                        f.write(font_data)
                    print(f"[Welcome Image] Downloaded Google Font: {font_name} ({variant})")
                    return str(cache_path)
    except Exception as e:
        print(f"[Welcome Image] Error downloading Google Font {font_name}: {e}")

    return None


def get_font(size: int, font_family: str = 'arial', bold: bool = False,
             italic: bool = False, custom_font_path: Optional[str] = None,
             google_font_family: Optional[str] = None) -> ImageFont.FreeTypeFont:
    """Get a font by family name with style variants, trying system fonts first."""

    # If custom font path is provided, use it
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            return ImageFont.truetype(custom_font_path, size)
        except (OSError, IOError):
            print(f"[Welcome Image] Failed to load custom font: {custom_font_path}")

    # If Google Font is specified, check cache or return system fallback
    if google_font_family and google_font_family.lower() in GOOGLE_FONTS:
        # This is async - caller should handle downloading
        # For now, try to load from cache
        import hashlib
        font_name = google_font_family.lower()
        variant = 'bolditalic' if (bold and italic) else ('bold' if bold else ('italic' if italic else 'normal'))
        # Find cached font
        for cached_file in FONT_CACHE_DIR.glob(f"{google_font_family}_{variant}_*.ttf"):
            try:
                return ImageFont.truetype(str(cached_file), size)
            except (OSError, IOError):
                continue

    # Determine the variant key
    if bold and italic:
        variant = 'bolditalic'
    elif bold:
        variant = 'bold'
    elif italic:
        variant = 'italic'
    else:
        variant = 'normal'

    # Try font variants first
    font_family_lower = font_family.lower()
    if font_family_lower in FONT_VARIANTS:
        font_candidates = FONT_VARIANTS[font_family_lower].get(variant, [])
        # Fallback to normal if variant not available
        if not font_candidates and variant != 'normal':
            font_candidates = FONT_VARIANTS[font_family_lower].get('normal', [])
    else:
        # Use legacy FONTS dict as fallback
        font_candidates = FONTS.get(font_family_lower, FONTS['arial'])

    for font_path in font_candidates:
        try:
            return ImageFont.truetype(font_path, size)
        except (OSError, IOError):
            continue

    # Ultimate fallback to default
    try:
        return ImageFont.load_default(size=size)
    except:
        return ImageFont.load_default()


async def download_image(url: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[bytes]:
    """Download image from URL. For GIFs, extracts the first frame."""
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        print(f"[Welcome Image] Downloading: {url}")
        async with session.get(url) as response:
            print(f"[Welcome Image] Response status: {response.status}")
            if response.status == 200:
                data = await response.read()
                print(f"[Welcome Image] Downloaded {len(data)} bytes")

                # Check if this is a GIF (by URL or content type)
                is_gif = url.lower().endswith('.gif') or response.headers.get('Content-Type', '').startswith('image/gif')

                if is_gif:
                    print("[Welcome Image] GIF detected, extracting first frame...")
                    # Extract first frame from GIF
                    try:
                        from PIL import Image
                        gif_img = Image.open(io.BytesIO(data))
                        # Convert first frame to RGB and save as PNG bytes
                        if gif_img.mode == 'P':
                            # Convert palette mode to RGB
                            gif_img = gif_img.convert('RGB')
                        elif gif_img.mode != 'RGB':
                            gif_img = gif_img.convert('RGB')

                        output = io.BytesIO()
                        gif_img.save(output, format='PNG')
                        output.seek(0)
                        data = output.getvalue()
                        print(f"[Welcome Image] First frame extracted: {len(data)} bytes")
                    except Exception as e:
                        print(f"[Welcome Image] Error extracting GIF frame: {e}")
                        # Fall back to original data if extraction fails

                return data
            else:
                print(f"[Welcome Image] Failed: HTTP {response.status}")
    except Exception as e:
        print(f"[Welcome Image] Error downloading image: {e}")
    finally:
        if close_session:
            await session.close()

    return None


async def download_gif_as_is(url: str, session: Optional[aiohttp.ClientSession] = None) -> Optional[bytes]:
    """Download GIF without conversion - returns original bytes for animated GIF."""
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        print(f"[Welcome Image] Downloading GIF as-is: {url}")
        async with session.get(url) as response:
            print(f"[Welcome Image] Response status: {response.status}")
            if response.status == 200:
                data = await response.read()
                print(f"[Welcome Image] Downloaded {len(data)} bytes (original GIF)")

                # Verify it's actually a GIF
                content_type = response.headers.get('Content-Type', '')
                if not (url.lower().endswith('.gif') or content_type.startswith('image/gif')):
                    print(f"[Welcome Image] Warning: URL may not be a GIF. Content-Type: {content_type}")

                return data
            else:
                print(f"[Welcome Image] Failed: HTTP {response.status}")
    except Exception as e:
        print(f"[Welcome Image] Error downloading GIF: {e}")
    finally:
        if close_session:
            await session.close()

    return None


async def is_gif_url(url: str, session: Optional[aiohttp.ClientSession] = None) -> bool:
    """Check if URL points to a GIF image."""
    if url.lower().endswith('.gif'):
        return True

    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        async with session.head(url) as response:
            content_type = response.headers.get('Content-Type', '')
            return content_type.startswith('image/gif')
    except:
        return False
    finally:
        if close_session:
            await session.close()

    return False


def create_gradient_background(size: Tuple[int, int], color1: str = "#3498db", color2: str = "#2980b9") -> Image.Image:
    """Create a gradient background."""
    width, height = size
    img = Image.new('RGB', size)
    draw = ImageDraw.Draw(img)
    
    # Parse colors
    r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    
    # Draw horizontal gradient
    for x in range(width):
        ratio = x / width
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))
    
    return img


def create_circular_avatar(avatar_img: Image.Image, size: int, border_width: int = 6, border_color: str = "#FFFFFF") -> Image.Image:
    """Create circular avatar with border. Kept for backward compatibility."""
    return create_shaped_avatar(avatar_img, size, 'circle', border_width, border_color)


def create_shaped_avatar(avatar_img: Image.Image, size: int, shape: str = 'circle',
                         border_width: int = 6, border_color: str = "#FFFFFF",
                         border_enabled: bool = True) -> Image.Image:
    """Create avatar with different shapes: circle, square, rounded, hexagon, star, diamond."""
    # Resize avatar
    avatar = avatar_img.resize((size, size), Image.Resampling.LANCZOS)

    # Create mask based on shape
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)

    shape_lower = shape.lower()

    if shape_lower == 'circle':
        # Circle (ellipse with equal width/height)
        draw.ellipse((0, 0, size, size), fill=255)

    elif shape_lower == 'square':
        # Square - no mask needed (full rectangle)
        draw.rectangle((0, 0, size, size), fill=255)

    elif shape_lower == 'rounded':
        # Rounded rectangle
        corner_radius = size // 6
        draw.rounded_rectangle((0, 0, size, size), radius=corner_radius, fill=255)

    elif shape_lower == 'hexagon':
        # Hexagon
        center = size / 2
        radius = size / 2
        points = []
        for i in range(6):
            angle = 60 * i - 30  # Start at -30 degrees for pointy top
            import math
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            points.append((x, y))
        draw.polygon(points, fill=255)

    elif shape_lower == 'star':
        # 5-pointed star
        center = size / 2
        outer_radius = size / 2
        inner_radius = size / 4
        points = []
        import math
        for i in range(10):
            angle = 36 * i - 90  # Start at -90 degrees for point up
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            points.append((x, y))
        draw.polygon(points, fill=255)

    elif shape_lower == 'diamond':
        # Diamond (rotated square)
        center = size / 2
        points = [
            (center, 0),           # Top
            (size, center),        # Right
            (center, size),        # Bottom
            (0, center)            # Left
        ]
        draw.polygon(points, fill=255)

    elif shape_lower == 'triangle':
        # Triangle pointing up
        points = [
            (size / 2, 0),         # Top
            (size, size),          # Bottom right
            (0, size)              # Bottom left
        ]
        draw.polygon(points, fill=255)

    elif shape_lower == 'squircle':
        # Squircle (super-ellipse-like shape - rounded with more curve)
        # Approximated with rounded rectangle and higher radius
        corner_radius = size // 3
        draw.rounded_rectangle((0, 0, size, size), radius=corner_radius, fill=255)

    else:
        # Default to circle
        draw.ellipse((0, 0, size, size), fill=255)

    # Apply mask to avatar
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(avatar, (0, 0))
    output.putalpha(mask)

    # If border is disabled, return just the masked avatar
    if not border_enabled:
        return output

    # Create bordered version
    border_size = size + border_width * 2
    bordered = Image.new('RGBA', (border_size, border_size), (0, 0, 0, 0))

    # Debug print

    # Draw border based on shape
    border_draw = ImageDraw.Draw(bordered)
    border_rgb = tuple(int(border_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    if shape_lower == 'circle':
        border_draw.ellipse((0, 0, border_size - 1, border_size - 1), fill=(*border_rgb, 255))

    elif shape_lower == 'square':
        border_draw.rectangle((0, 0, border_size - 1, border_size - 1), fill=(*border_rgb, 255))

    elif shape_lower == 'rounded' or shape_lower == 'squircle':
        corner_radius = (size // 6) + border_width if shape_lower == 'rounded' else (size // 3) + border_width
        border_draw.rounded_rectangle((0, 0, border_size - 1, border_size - 1), radius=corner_radius, fill=(*border_rgb, 255))

    elif shape_lower == 'hexagon':
        center = border_size / 2
        radius = border_size / 2 - 0.5
        points = []
        import math
        for i in range(6):
            angle = 60 * i - 30
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            points.append((x, y))
        border_draw.polygon(points, fill=(*border_rgb, 255))

    elif shape_lower == 'star':
        center = border_size / 2
        outer_radius = border_size / 2 - 0.5
        inner_radius = border_size / 4
        points = []
        import math
        for i in range(10):
            angle = 36 * i - 90
            radius = outer_radius if i % 2 == 0 else inner_radius
            x = center + radius * math.cos(math.radians(angle))
            y = center + radius * math.sin(math.radians(angle))
            points.append((x, y))
        border_draw.polygon(points, fill=(*border_rgb, 255))

    elif shape_lower == 'diamond':
        center = border_size / 2
        points = [
            (center, 0),
            (border_size, center),
            (center, border_size),
            (0, center)
        ]
        border_draw.polygon(points, fill=(*border_rgb, 255))

    elif shape_lower == 'triangle':
        points = [
            (border_size / 2, 0),
            (border_size, border_size),
            (0, border_size)
        ]
        border_draw.polygon(points, fill=(*border_rgb, 255))

    else:
        # Default to circle
        border_draw.ellipse((0, 0, border_size - 1, border_size - 1), fill=(*border_rgb, 255))

    # Paste avatar on top
    bordered.paste(output, (border_width, border_width), output)

    return bordered


def get_avatar_position(img_size: Tuple[int, int], avatar_size: int, position: str,
                        offset_x: int = 0, offset_y: int = 0) -> Tuple[int, int]:
    """Get avatar position based on setting with manual offset for precise positioning."""
    width, height = img_size
    border_offset = 6  # Border width
    total_avatar_size = avatar_size + border_offset * 2

    positions = {
        "center": (
            (width - total_avatar_size) // 2,
            (height - total_avatar_size) // 2 - 40  # Offset up for text
        ),
        "top-left": (30, 30),
        "top-right": (width - total_avatar_size - 30, 30),
        "top-center": ((width - total_avatar_size) // 2, 30),
        "bottom-left": (30, height - total_avatar_size - 30),
        "bottom-right": (width - total_avatar_size - 30, height - total_avatar_size - 30),
        "bottom-center": ((width - total_avatar_size) // 2, height - total_avatar_size - 30),
    }

    base_x, base_y = positions.get(position, positions["center"])

    # Apply manual offset for precise positioning
    return (base_x + offset_x, base_y + offset_y)


def draw_text_with_shadow(
    draw: ImageDraw.Draw,
    text: str,
    position: Tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill_color: str = "#FFD700",
    shadow_color: str = "#000000",
    shadow_offset: int = 3,
    underline: bool = False
):
    """Draw text with shadow effect and optional underline."""
    x, y = position

    # Parse colors
    shadow_rgb = tuple(int(shadow_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    fill_rgb = tuple(int(fill_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

    # Get text bounding box for underline positioning
    bbox = draw.textbbox((x, y), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Draw shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_rgb)

    # Draw main text
    draw.text((x, y), text, font=font, fill=fill_rgb)

    # Draw underline if requested
    if underline:
        # Calculate underline position (slightly below the text)
        underline_y = y + text_height + 4
        underline_width = max(2, text_height // 12)  # Scale with text size

        # Draw shadow for underline
        draw.rectangle(
            [x - 2 + shadow_offset, underline_y + shadow_offset,
             x + text_width + 2 + shadow_offset, underline_y + underline_width + shadow_offset],
            fill=shadow_rgb
        )
        # Draw main underline
        draw.rectangle(
            [x - 2, underline_y, x + text_width + 2, underline_y + underline_width],
            fill=fill_rgb
        )


async def generate_welcome_image(
    avatar_url: str,
    username: str,
    banner_url: Optional[str] = None,
    welcome_text: str = DEFAULT_WELCOME_TEXT,
    profile_position: str = DEFAULT_PROFILE_POSITION,
    text_color: str = DEFAULT_TEXT_COLOR,
    font_family: str = 'arial',
    banner_offset_x: int = 0,
    banner_offset_y: int = 0,
    avatar_offset_x: int = 0,
    avatar_offset_y: int = 0,
    text_offset_x: int = 0,
    text_offset_y: int = 0,
    welcome_text_size: int = 56,
    username_text_size: int = 32,
    avatar_size: int = DEFAULT_AVATAR_SIZE,
    session: Optional[aiohttp.ClientSession] = None,
    # Text style parameters
    welcome_text_bold: bool = False,
    welcome_text_italic: bool = False,
    welcome_text_underline: bool = False,
    username_text_bold: bool = False,
    username_text_italic: bool = False,
    username_text_underline: bool = False,
    # Font source parameters
    google_font_family: Optional[str] = None,
    custom_font_path: Optional[str] = None,
    # Avatar shape parameter
    avatar_shape: str = 'circle',
    # Avatar border parameters
    avatar_border_enabled: bool = True,
    avatar_border_width: int = 6,
    avatar_border_color: str = '#FFFFFF'
) -> Optional[bytes]:
    """
    Generate a welcome image.

    Args:
        avatar_url: URL of the user's avatar
        username: Username to display
        banner_url: Optional custom banner URL
        welcome_text: Text to display (e.g., "WELCOME")
        profile_position: Avatar position (center, top-left, etc.)
        text_color: Hex color for the welcome text
        font_family: Font family to use (arial, impact, verdana, etc.)
        banner_offset_x: Horizontal offset for banner positioning
        banner_offset_y: Vertical offset for banner positioning
        avatar_offset_x: Horizontal offset for avatar precise positioning
        avatar_offset_y: Vertical offset for avatar precise positioning
        text_offset_x: Horizontal offset for text precise positioning
        text_offset_y: Vertical offset for text precise positioning
        welcome_text_size: Font size for welcome text
        username_text_size: Font size for username text
        avatar_size: Size of the avatar
        session: Optional aiohttp session for reuse
        welcome_text_bold: Whether welcome text should be bold
        welcome_text_italic: Whether welcome text should be italic
        welcome_text_underline: Whether welcome text should be underlined
        username_text_bold: Whether username text should be bold
        username_text_italic: Whether username text should be italic
        username_text_underline: Whether username text should be underlined
        google_font_family: Google Font family name (if using Google Fonts)
        custom_font_path: Path to custom uploaded font file

    Returns:
        PNG image bytes or None on error
    """
    try:
        print(f"[Welcome Image] Generating welcome image for {username}")
        print(f"[Welcome Image] Avatar URL: {avatar_url}")
        print(f"[Welcome Image] Banner URL: {banner_url}")
        print(f"[Welcome Image] Offsets - avatar_x: {avatar_offset_x}, avatar_y: {avatar_offset_y}, text_x: {text_offset_x}, text_y: {text_offset_y}")

        # Download avatar
        avatar_data = await download_image(avatar_url, session)
        if not avatar_data:
            print("[Welcome Image] Failed to download avatar!")
            return None
        print("[Welcome Image] Avatar downloaded successfully")
        
        avatar_img = Image.open(io.BytesIO(avatar_data)).convert('RGBA')
        
        # Create or load background
        if banner_url:
            print("[Welcome Image] Downloading banner background...")
            banner_data = await download_image(banner_url, session)
            if banner_data:
                print("[Welcome Image] Banner downloaded, processing...")
                background = Image.open(io.BytesIO(banner_data)).convert('RGB')
                # Resize to fit our dimensions while maintaining aspect ratio
                bg_ratio = background.width / background.height
                target_ratio = DEFAULT_IMAGE_SIZE[0] / DEFAULT_IMAGE_SIZE[1]

                if bg_ratio > target_ratio:
                    new_height = DEFAULT_IMAGE_SIZE[1]
                    new_width = int(new_height * bg_ratio)
                else:
                    new_width = DEFAULT_IMAGE_SIZE[0]
                    new_height = int(new_width / bg_ratio)

                background = background.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center crop with offset (Canva-style positioning)
                left = (new_width - DEFAULT_IMAGE_SIZE[0]) // 2 + banner_offset_x
                top = (new_height - DEFAULT_IMAGE_SIZE[1]) // 2 + banner_offset_y

                # Clamp values to ensure valid crop region
                left = max(0, min(left, new_width - DEFAULT_IMAGE_SIZE[0]))
                top = max(0, min(top, new_height - DEFAULT_IMAGE_SIZE[1]))

                background = background.crop((left, top, left + DEFAULT_IMAGE_SIZE[0], top + DEFAULT_IMAGE_SIZE[1]))
            else:
                print("[Welcome Image] Banner download failed, using gradient")
                background = create_gradient_background(DEFAULT_IMAGE_SIZE)
        else:
            background = create_gradient_background(DEFAULT_IMAGE_SIZE)

        # No border - use background directly
        final_img = background.convert('RGBA')

        # Create shaped avatar
        shaped_avatar = create_shaped_avatar(avatar_img, avatar_size, avatar_shape,
                                             border_width=avatar_border_width,
                                             border_color=avatar_border_color,
                                             border_enabled=avatar_border_enabled)

        # Get avatar position with manual offset
        avatar_pos = get_avatar_position(final_img.size, avatar_size, profile_position,
                                          avatar_offset_x, avatar_offset_y)

        # Paste avatar
        final_img.paste(shaped_avatar, avatar_pos, shaped_avatar)

        # Draw text
        draw = ImageDraw.Draw(final_img)

        # Download Google Font if specified
        if google_font_family:
            await download_google_font(google_font_family, welcome_text_bold, welcome_text_italic)

        # Welcome text - use selected font family and dynamic size with style
        welcome_font = get_font(
            welcome_text_size,
            font_family=font_family,
            bold=welcome_text_bold,
            italic=welcome_text_italic,
            custom_font_path=custom_font_path,
            google_font_family=google_font_family
        )
        username_font = get_font(
            username_text_size,
            font_family=font_family,
            bold=username_text_bold,
            italic=username_text_italic,
            custom_font_path=custom_font_path,
            google_font_family=google_font_family
        )
        
        # Calculate text positions
        width, height = final_img.size

        # Get text bounding boxes for centering
        welcome_bbox = draw.textbbox((0, 0), welcome_text.upper(), font=welcome_font)
        welcome_width = welcome_bbox[2] - welcome_bbox[0]

        username_bbox = draw.textbbox((0, 0), username.upper(), font=username_font)
        username_width = username_bbox[2] - username_bbox[0]

        # Base text position (top area, independent from avatar)
        BASE_TEXT_Y = 120  # Fixed base Y position for text
        BASE_TEXT_X = width // 2  # Center horizontally

        # Apply text offset for precise positioning
        text_y = BASE_TEXT_Y + text_offset_y
        text_x = BASE_TEXT_X + text_offset_x

        welcome_x = text_x - welcome_width // 2
        username_x = text_x - username_width // 2

        # Draw welcome text with shadow
        draw_text_with_shadow(
            draw, welcome_text.upper(),
            (welcome_x, text_y),
            welcome_font,
            fill_color=text_color,
            shadow_color="#000000",
            shadow_offset=3,
            underline=welcome_text_underline
        )

        # Draw username with shadow
        draw_text_with_shadow(
            draw, username.upper(),
            (username_x, text_y + welcome_text_size + 10),
            username_font,
            fill_color="#FFFFFF",
            shadow_color="#000000",
            shadow_offset=2,
            underline=username_text_underline
        )
        
        # Convert to bytes
        output = io.BytesIO()
        final_img = final_img.convert('RGB')
        final_img.save(output, format='PNG', quality=95)
        output.seek(0)
        
        return output.getvalue()
    
    except Exception as e:
        print(f"Error generating welcome image: {e}")
        import traceback
        traceback.print_exc()
        return None


async def generate_animated_welcome_image(
    avatar_url: str,
    username: str,
    banner_url: Optional[str] = None,
    welcome_text: str = DEFAULT_WELCOME_TEXT,
    profile_position: str = DEFAULT_PROFILE_POSITION,
    text_color: str = DEFAULT_TEXT_COLOR,
    font_family: str = 'arial',
    banner_offset_x: int = 0,
    banner_offset_y: int = 0,
    avatar_offset_x: int = 0,
    avatar_offset_y: int = 0,
    text_offset_x: int = 0,
    text_offset_y: int = 0,
    welcome_text_size: int = 56,
    username_text_size: int = 32,
    avatar_size: int = DEFAULT_AVATAR_SIZE,
    session: Optional[aiohttp.ClientSession] = None,
    # Text style parameters
    welcome_text_bold: bool = False,
    welcome_text_italic: bool = False,
    welcome_text_underline: bool = False,
    username_text_bold: bool = False,
    username_text_italic: bool = False,
    username_text_underline: bool = False,
    # Font source parameters
    google_font_family: Optional[str] = None,
    custom_font_path: Optional[str] = None,
    # Avatar shape parameter
    avatar_shape: str = 'circle',
    # Avatar border parameters
    avatar_border_enabled: bool = True,
    avatar_border_width: int = 6,
    avatar_border_color: str = '#FFFFFF'
) -> Optional[bytes]:
    """
    Generate an animated welcome image with GIF banner.
    Processes each frame of the GIF and composites avatar + text.
    """
    close_session = False
    if session is None:
        session = aiohttp.ClientSession()
        close_session = True

    try:
        print(f"[Animated GIF] Starting generation for {username}")

        # Download avatar
        avatar_data = await download_image(avatar_url, session)
        if not avatar_data:
            print("[Animated GIF] Failed to download avatar!")
            return None

        avatar_img = Image.open(io.BytesIO(avatar_data)).convert('RGBA')

        # Create shaped avatar once (reuse for all frames)
        shaped_avatar = create_shaped_avatar(avatar_img, avatar_size, avatar_shape,
                                             border_width=avatar_border_width,
                                             border_color=avatar_border_color,
                                             border_enabled=avatar_border_enabled)
        print(f"[Animated GIF] Avatar created: {shaped_avatar.size}")

        # Download Google Font if specified
        if google_font_family:
            await download_google_font(google_font_family, welcome_text_bold, welcome_text_italic)

        # Get fonts once with style support
        welcome_font = get_font(
            welcome_text_size,
            font_family=font_family,
            bold=welcome_text_bold,
            italic=welcome_text_italic,
            custom_font_path=custom_font_path,
            google_font_family=google_font_family
        )
        username_font = get_font(
            username_text_size,
            font_family=font_family,
            bold=username_text_bold,
            italic=username_text_italic,
            custom_font_path=custom_font_path,
            google_font_family=google_font_family
        )

        # Download banner GIF
        if not banner_url:
            print("[Animated GIF] No banner provided, cannot create animated GIF")
            return None

        print(f"[Animated GIF] Downloading banner GIF: {banner_url}")
        async with session.get(banner_url) as response:
            if response.status != 200:
                print(f"[Animated GIF] Failed to download banner: HTTP {response.status}")
                return None

            banner_data = await response.read()
            print(f"[Animated GIF] Banner downloaded: {len(banner_data)} bytes")

        # Open GIF and extract all frames
        gif_img = Image.open(io.BytesIO(banner_data))

        # Check if it's actually an animated GIF
        if gif_img.format != 'GIF':
            print(f"[Animated GIF] Banner is not a GIF, format: {gif_img.format}")
            # Fall back to static image
            return await generate_welcome_image(
                avatar_url, username, banner_url, welcome_text,
                profile_position, text_color, font_family,
                banner_offset_x, banner_offset_y,
                avatar_offset_x, avatar_offset_y,
                text_offset_x, text_offset_y,
                welcome_text_size, username_text_size, avatar_size, session,
                welcome_text_bold, welcome_text_italic, welcome_text_underline,
                username_text_bold, username_text_italic, username_text_underline,
                google_font_family, custom_font_path,
                avatar_shape
            )

        # Get all frames from GIF
        frames = []
        frame_durations = []

        # Try to get frame count
        try:
            frame_count = gif_img.n_frames
            print(f"[Animated GIF] Total frames: {frame_count}")
        except:
            frame_count = 1
            print("[Animated GIF] Could not determine frame count, will process until EOF")

        # Process each frame
        frame_index = 0
        while True:
            try:
                # Seek to frame
                gif_img.seek(frame_index)

                # Get frame duration
                duration = gif_img.info.get('duration', 100)

                # Convert frame to RGBA (for compositing)
                # Use the frame directly, then composite everything
                frame = gif_img.convert('RGBA')

                print(f"[Animated GIF] Processing frame {frame_index}, duration: {duration}ms, size: {frame.size}")

                # Resize to fit our dimensions while maintaining aspect ratio
                bg_ratio = frame.width / frame.height
                target_ratio = DEFAULT_IMAGE_SIZE[0] / DEFAULT_IMAGE_SIZE[1]

                if bg_ratio > target_ratio:
                    new_height = DEFAULT_IMAGE_SIZE[1]
                    new_width = int(new_height * bg_ratio)
                else:
                    new_width = DEFAULT_IMAGE_SIZE[0]
                    new_height = int(new_width / bg_ratio)

                frame = frame.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Center crop with offset (Canva-style positioning)
                left = (new_width - DEFAULT_IMAGE_SIZE[0]) // 2 + banner_offset_x
                top = (new_height - DEFAULT_IMAGE_SIZE[1]) // 2 + banner_offset_y

                # Clamp values
                left = max(0, min(left, new_width - DEFAULT_IMAGE_SIZE[0]))
                top = max(0, min(top, new_height - DEFAULT_IMAGE_SIZE[1]))

                background = frame.crop((left, top, left + DEFAULT_IMAGE_SIZE[0], top + DEFAULT_IMAGE_SIZE[1]))

                # Create a new image for compositing (start with background)
                final_frame = background.copy()

                # Get avatar position
                avatar_pos = get_avatar_position(final_frame.size, avatar_size, profile_position,
                                                  avatar_offset_x, avatar_offset_y)

                # Paste avatar with alpha channel
                final_frame.paste(shaped_avatar, avatar_pos, shaped_avatar)

                # Draw text
                draw = ImageDraw.Draw(final_frame)

                # Calculate text positions
                width, height = final_frame.size
                welcome_bbox = draw.textbbox((0, 0), welcome_text.upper(), font=welcome_font)
                welcome_width = welcome_bbox[2] - welcome_bbox[0]

                username_bbox = draw.textbbox((0, 0), username.upper(), font=username_font)
                username_width = username_bbox[2] - username_bbox[0]

                BASE_TEXT_Y = 120
                BASE_TEXT_X = width // 2

                text_y = BASE_TEXT_Y + text_offset_y
                text_x = BASE_TEXT_X + text_offset_x

                welcome_x = text_x - welcome_width // 2
                username_x = text_x - username_width // 2

                print(f"[Animated GIF] Frame {frame_index} - Drawing text at ({welcome_x}, {text_y})")

                # Draw welcome text with shadow
                draw_text_with_shadow(
                    draw, welcome_text.upper(),
                    (welcome_x, text_y),
                    welcome_font,
                    fill_color=text_color,
                    shadow_color="#000000",
                    shadow_offset=3,
                    underline=welcome_text_underline
                )

                # Draw username with shadow
                draw_text_with_shadow(
                    draw, username.upper(),
                    (username_x, text_y + welcome_text_size + 10),
                    username_font,
                    fill_color="#FFFFFF",
                    shadow_color="#000000",
                    shadow_offset=2,
                    underline=username_text_underline
                )

                # Convert to RGB for GIF (Pillow handles this)
                final_frame_rgb = final_frame.convert('RGB')
                frames.append(final_frame_rgb)
                frame_durations.append(duration)

                frame_index += 1

            except EOFError:
                # End of GIF
                print(f"[Animated GIF] Reached end of GIF at frame {frame_index}")
                break
            except Exception as e:
                print(f"[Animated GIF] Error processing frame {frame_index}: {e}")
                import traceback
                traceback.print_exc()
                break

        if not frames:
            print("[Animated GIF] No frames extracted from GIF")
            return None

        print(f"[Animated GIF] Successfully processed {len(frames)} frames")

        # Check if too many frames - limit to avoid huge file sizes
        MAX_FRAMES = 30  # Discord has file size limits
        if len(frames) > MAX_FRAMES:
            print(f"[Animated GIF] Too many frames ({len(frames)}), limiting to {MAX_FRAMES}")
            # Sample frames evenly
            step = len(frames) / MAX_FRAMES
            sampled_indices = [int(i * step) for i in range(MAX_FRAMES)]
            frames = [frames[i] for i in sampled_indices]
            frame_durations = [frame_durations[i] for i in sampled_indices]

        # Save as animated GIF with optimized settings
        output = io.BytesIO()

        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:] if len(frames) > 1 else [],
            duration=frame_durations,
            loop=0,  # Infinite loop
            disposal=2,  # Restore to background
            optimize=True,  # Enable optimization to reduce file size
            colors=64  # Reduce colors for smaller file size
        )

        output.seek(0)
        result = output.getvalue()
        size_mb = len(result) / (1024 * 1024)
        print(f"[Animated GIF] Generated animated GIF: {len(result)} bytes ({size_mb:.2f} MB)")

        # Check if file is too large for Discord (25MB limit)
        if len(result) > 25 * 1024 * 1024:
            print(f"[Animated GIF] File too large ({size_mb:.2f} MB), falling back to static image")
            return await generate_welcome_image(
                avatar_url, username, banner_url, welcome_text,
                profile_position, text_color, font_family,
                banner_offset_x, banner_offset_y,
                avatar_offset_x, avatar_offset_y,
                text_offset_x, text_offset_y,
                welcome_text_size, username_text_size, avatar_size, session,
                welcome_text_bold, welcome_text_italic, welcome_text_underline,
                username_text_bold, username_text_italic, username_text_underline,
                google_font_family, custom_font_path,
                avatar_shape
            )

        return result

    except Exception as e:
        print(f"Error generating animated welcome image: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        if close_session:
            await session.close()


async def generate_goodbye_image(
    avatar_url: str,
    username: str,
    banner_url: Optional[str] = None,
    goodbye_text: str = DEFAULT_GOODBYE_TEXT,
    profile_position: str = DEFAULT_PROFILE_POSITION,
    text_color: str = "#FF6B6B",  # Red-ish for goodbye
    font_family: str = 'arial',
    banner_offset_x: int = 0,
    banner_offset_y: int = 0,
    avatar_offset_x: int = 0,
    avatar_offset_y: int = 0,
    text_offset_x: int = 0,
    text_offset_y: int = 0,
    welcome_text_size: int = 56,
    username_text_size: int = 32,
    avatar_size: int = DEFAULT_AVATAR_SIZE,
    session: Optional[aiohttp.ClientSession] = None,
    # Text style parameters
    goodbye_text_bold: bool = False,
    goodbye_text_italic: bool = False,
    goodbye_text_underline: bool = False,
    goodbye_username_text_bold: bool = False,
    goodbye_username_text_italic: bool = False,
    goodbye_username_text_underline: bool = False,
    # Font source parameters
    google_font_family: Optional[str] = None,
    custom_font_path: Optional[str] = None,
    # Avatar shape parameter
    avatar_shape: str = 'circle',
    # Avatar border parameters
    avatar_border_enabled: bool = True,
    avatar_border_width: int = 6,
    avatar_border_color: str = '#FFFFFF'
) -> Optional[bytes]:
    """Generate a goodbye image."""
    return await generate_welcome_image(
        avatar_url=avatar_url,
        username=username,
        banner_url=banner_url,
        welcome_text=goodbye_text,
        profile_position=profile_position,
        text_color=text_color,
        font_family=font_family,
        banner_offset_x=banner_offset_x,
        banner_offset_y=banner_offset_y,
        avatar_offset_x=avatar_offset_x,
        avatar_offset_y=avatar_offset_y,
        text_offset_x=text_offset_x,
        text_offset_y=text_offset_y,
        welcome_text_size=welcome_text_size,
        username_text_size=username_text_size,
        avatar_size=avatar_size,
        session=session,
        # Map goodbye text styles to welcome text styles
        welcome_text_bold=goodbye_text_bold,
        welcome_text_italic=goodbye_text_italic,
        welcome_text_underline=goodbye_text_underline,
        username_text_bold=goodbye_username_text_bold,
        username_text_italic=goodbye_username_text_italic,
        username_text_underline=goodbye_username_text_underline,
        google_font_family=google_font_family,
        custom_font_path=custom_font_path,
        avatar_shape=avatar_shape,
        avatar_border_enabled=avatar_border_enabled,
        avatar_border_width=avatar_border_width,
        avatar_border_color=avatar_border_color
    )


# Test function
async def _test():
    """Test the image generator."""
    # Test with a Discord avatar URL
    test_avatar = "https://cdn.discordapp.com/embed/avatars/0.png"
    test_username = "TestUser"
    
    result = await generate_welcome_image(
        avatar_url=test_avatar,
        username=test_username,
        welcome_text="WELCOME",
        profile_position="center",
        text_color="#FFD700"
    )
    
    if result:
        with open("test_welcome.png", "wb") as f:
            f.write(result)
        print("Test image saved to test_welcome.png")
    else:
        print("Failed to generate test image")


if __name__ == "__main__":
    asyncio.run(_test())
