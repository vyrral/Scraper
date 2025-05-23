
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

class BaseScraper(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def get_job_listing_urls(self) -> List[str]:
        """Get list of job URLs to scrape"""
        pass
    
    @abstractmethod
    def extract_job_data(self, url: str) -> Dict[str, Any]:
        """Extract job data from a single URL"""
        pass
    
    @abstractmethod
    def is_target_region_job(self, job_data: Dict[str, Any]) -> bool:
        """Check if job is from target regions"""
        pass
