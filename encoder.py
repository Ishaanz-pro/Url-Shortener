import random
import string
from typing import Optional

class Base62Encoder:
    """Base62 encoding/decoding for URL shortening"""
    
    ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
    BASE = len(ALPHABET)
    
    @staticmethod
    def encode(num: int) -> str:
        """Encode integer to Base62 string"""
        if num == 0:
            return Base62Encoder.ALPHABET[0]
        
        arr = []
        while num:
            arr.append(Base62Encoder.ALPHABET[num % Base62Encoder.BASE])
            num //= Base62Encoder.BASE
        
        arr.reverse()
        return ''.join(arr)
    
    @staticmethod
    def decode(s: str) -> int:
        """Decode Base62 string to integer"""
        result = 0
        for char in s:
            result = result * Base62Encoder.BASE + Base62Encoder.ALPHABET.index(char)
        return result
    
    @staticmethod
    def generate_short_code(length: int = 6) -> str:
        """Generate random short code"""
        return ''.join(random.choices(Base62Encoder.ALPHABET, k=length))


class URLValidator:
    """Validate URLs"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Basic URL validation"""
        try:
            # Basic checks
            if not url or len(url) > 2048:
                return False
            
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            
            # Check for valid URL format
            from urllib.parse import urlparse
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL by adding scheme if missing"""
        if not url.startswith(("http://", "https://")):
            return f"https://{url}"
        return url
