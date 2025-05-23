import hashlib
import re
import time
import random
from typing import Dict, Any, Optional
import logging
from config import USER_AGENTS, REQUEST_DELAY

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text content."""
    if not text:
        return ""
    
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    return text

def generate_job_hash(job_data: Dict[str, Any]) -> str:
    """Generate a unique hash for a job posting to detect duplicates."""
    # Create a string from key job attributes
    hash_string = f"{job_data.get('title', '')}{job_data.get('company', '')}{job_data.get('location', '')}"
    hash_string = clean_text(hash_string).lower()
    
    # Generate MD5 hash
    return hashlib.md5(hash_string.encode()).hexdigest()

def validate_job_data(job_data: Dict[str, Any]) -> bool:
    """Validate that job data contains required fields."""
    required_fields = ['title', 'company', 'location']
    
    for field in required_fields:
        if not job_data.get(field):
            logger.warning(f"Job missing required field: {field}")
            return False
    
    return True

def sanitize_job_data(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize and clean job data."""
    sanitized = {}
    
    for key, value in job_data.items():
        if isinstance(value, str):
            sanitized[key] = clean_text(value)
        else:
            sanitized[key] = value
    
    # Truncate description if too long
    if 'description' in sanitized and len(sanitized['description']) > 5000:
        sanitized['description'] = sanitized['description'][:4997] + "..."
    
    return sanitized

def get_random_user_agent() -> str:
    """Get a random user agent for web requests."""
    return random.choice(USER_AGENTS)

def safe_sleep(duration: float = None) -> None:
    """Sleep for a random duration within a range to avoid detection."""
    if duration is None:
        duration = REQUEST_DELAY
    
    # Add some randomness to the delay
    random_delay = duration + random.uniform(0, 1)
    time.sleep(random_delay)

def extract_salary_info(text: str) -> Optional[str]:
    """Extract salary information from text."""
    if not text:
        return None
    
    # Common salary patterns
    salary_patterns = [
        r'\$[\d,]+(?:\.\d{2})?\s*-?\s*\$?[\d,]*(?:\.\d{2})?\s*(?:per\s+hour|\/hr|hourly|annually|per\s+year|\/year)?',
        r'[\d,]+\s*-\s*[\d,]+\s*(?:CAD|USD|\$)',
        r'(?:salary|pay|compensation):\s*\$?[\d,]+(?:\.\d{2})?(?:\s*-\s*\$?[\d,]+(?:\.\d{2})?)?'
    ]
    
    for pattern in salary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return None

def format_location(location: str) -> str:
    """Format and standardize location strings."""
    if not location:
        return ""
    
    location = clean_text(location)
    
    # Add Canada if not present
    if "canada" not in location.lower() and "ca" not in location.lower():
        location += ", Canada"
    
    return location

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None
