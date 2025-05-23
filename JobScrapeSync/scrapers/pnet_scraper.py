import requests
from bs4 import BeautifulSoup
import trafilatura
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from utils import get_random_user_agent, safe_sleep, clean_text, extract_salary_info, format_location
from config import TIMEOUT, MAX_RETRIES, TARGET_REGIONS

logger = logging.getLogger(__name__)

class PNetScraper:
    """Scraper for pnet.co.za job postings (South Africa)"""
    
    def __init__(self):
        self.base_url = "https://www.pnet.co.za"
        self.jobs_url = "https://www.pnet.co.za/jobs/in-johannesburg"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def is_target_region_job(self, job_data: Dict[str, Any]) -> bool:
        """Check if job is from target regions"""
        job_text = f"{job_data.get('title', '')} {job_data.get('location', '')} {job_data.get('description', '')}".lower()
        
        for region in TARGET_REGIONS:
            if region.lower() in job_text:
                return True
        return False
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling and retries."""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching PNet: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"PNet request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    safe_sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        
        return None
    
    def get_job_listing_urls(self) -> List[str]:
        """Get URLs of job listing pages from PNet"""
        job_urls = []
        
        html = self.fetch_page(self.jobs_url)
        if not html:
            return job_urls
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for job links - PNet specific selectors
        job_link_selectors = [
            'a[href*="/job/"]',
            'a[href*="/jobs/"]',
            '.job-title a',
            '.job-link a',
            'h3 a',
            'h2 a',
            '.result-title a'
        ]
        
        for selector in job_link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    if href.startswith('/'):
                        full_url = urljoin(self.base_url, href)
                    else:
                        full_url = href
                    
                    if full_url not in job_urls and 'pnet.co.za' in full_url:
                        job_urls.append(full_url)
        
        logger.info(f"Found {len(job_urls)} PNet job URLs")
        return job_urls[:20]  # Limit to first 20 jobs
    
    def extract_job_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from a PNet job posting page"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Use trafilatura to get clean text content
        clean_text_content = trafilatura.extract(html)
        
        job_data = {
            'source_url': url,
            'title': '',
            'company': '',
            'location': 'South Africa',  # Default for PNet
            'description': '',
            'salary': '',
            'job_type': '',
            'posted_date': '',
            'requirements': '',
            'benefits': '',
            'source': 'PNet'
        }
        
        # Extract title
        title_selectors = [
            'h1.job-title',
            'h1',
            '.job-title',
            '.title',
            '[class*="title"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                job_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Extract company
        company_selectors = [
            '.company-name',
            '.company',
            '.employer',
            '[class*="company"]',
            '.job-company'
        ]
        
        for selector in company_selectors:
            company_elem = soup.select_one(selector)
            if company_elem:
                job_data['company'] = clean_text(company_elem.get_text())
                break
        
        # Extract location (more specific than default)
        location_selectors = [
            '.job-location',
            '.location',
            '[class*="location"]',
            '.address'
        ]
        
        for selector in location_selectors:
            location_elem = soup.select_one(selector)
            if location_elem:
                job_data['location'] = format_location(clean_text(location_elem.get_text()))
                if not job_data['location']:
                    job_data['location'] = 'South Africa'
                break
        
        # Extract description
        if clean_text_content:
            job_data['description'] = clean_text(clean_text_content)
        else:
            desc_selectors = [
                '.job-description',
                '.description',
                '.content',
                '[class*="description"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    job_data['description'] = clean_text(desc_elem.get_text())
                    break
        
        # Extract salary information
        salary_text = f"{job_data['title']} {job_data['description']}"
        salary = extract_salary_info(salary_text)
        if salary:
            job_data['salary'] = salary
        
        # Basic validation
        if not job_data['title']:
            logger.warning(f"Could not extract job title from {url}")
            return None
        
        # Fill in missing fields
        if not job_data['title']:
            job_data['title'] = "Job Opening"
        if not job_data['company']:
            job_data['company'] = "Company"
        
        # Always include South Africa jobs since this is a SA site
        logger.info(f"Extracted PNet job: {job_data['title']} at {job_data['company']} - {job_data['location']}")
        return job_data
    
    def scrape_jobs(self) -> List[Dict[str, Any]]:
        """Scrape all available jobs from PNet"""
        logger.info("Starting PNet job scraping process")
        
        job_urls = self.get_job_listing_urls()
        
        if not job_urls:
            logger.warning("No PNet job URLs found")
            return []
        
        jobs = []
        
        for i, url in enumerate(job_urls):
            try:
                logger.info(f"Scraping PNet job {i+1}/{len(job_urls)}: {url}")
                
                job_data = self.extract_job_data(url)
                if job_data:
                    jobs.append(job_data)
                
                safe_sleep()
                
            except Exception as e:
                logger.error(f"Error scraping PNet job {url}: {e}")
                continue
        
        logger.info(f"PNet scraping completed. Found {len(jobs)} jobs")
        return jobs