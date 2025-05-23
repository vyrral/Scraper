import requests
from bs4 import BeautifulSoup
import trafilatura
import logging
import time
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from utils import get_random_user_agent, safe_sleep, clean_text, extract_salary_info, format_location
from config import JOBSERVICEHUB_BASE_URL, TIMEOUT, MAX_RETRIES, TARGET_REGIONS

logger = logging.getLogger(__name__)

from scrapers.pnet_scraper import PNetScraper
from scrapers.jobin_scraper import JobInScraper
from scrapers.careers247_scraper import Careers247Scraper

class JobServiceHubScraper:
    """Scraper for jobservicehub.com job postings."""
    
    def __init__(self):
        self.base_url = JOBSERVICEHUB_BASE_URL
        # Initialize all scrapers for multiple job sources
        self.scrapers = [
            PNetScraper(),
            JobInScraper(),
            Careers247Scraper()
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def is_target_region_job(self, job_data: Dict[str, Any]) -> bool:
        """Check if job is from target regions (South Africa, Dubai, UAE, UK)"""
        job_text = f"{job_data.get('title', '')} {job_data.get('location', '')} {job_data.get('description', '')}".lower()
        
        for region in TARGET_REGIONS:
            if region.lower() in job_text:
                return True
        return False
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling and retries."""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    safe_sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        
        return None
    
    def get_job_listing_urls(self) -> List[str]:
        """Get URLs of job listing pages."""
        job_urls = []
        
        # Start with the main jobs page
        html = self.fetch_page(self.base_url)
        if not html:
            return job_urls
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for job links - this may need adjustment based on actual site structure
        job_link_selectors = [
            'a[href*="/job/"]',
            'a[href*="/jobs/"]',
            'a[href*="/posting/"]',
            '.job-title a',
            '.job-link',
            'h3 a',
            'h2 a'
        ]
        
        for selector in job_link_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in job_urls:
                        job_urls.append(full_url)
        
        # Look for pagination and additional pages
        pagination_links = soup.select('a[href*="page="], .pagination a, .next a')
        page_urls = set()
        
        for link in pagination_links:
            href = link.get('href')
            if href:
                page_url = urljoin(self.base_url, href)
                page_urls.add(page_url)
        
        # Scrape additional pages (limit to prevent infinite loops)
        max_pages = 10
        scraped_pages = 0
        
        for page_url in list(page_urls):
            if scraped_pages >= max_pages:
                break
            
            safe_sleep()
            page_html = self.fetch_page(page_url)
            if page_html:
                page_soup = BeautifulSoup(page_html, 'html.parser')
                
                for selector in job_link_selectors:
                    links = page_soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            if full_url not in job_urls:
                                job_urls.append(full_url)
                
                scraped_pages += 1
        
        logger.info(f"Found {len(job_urls)} job URLs")
        return job_urls
    
    def extract_job_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from a job posting page."""
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
            'location': '',
            'description': '',
            'salary': '',
            'job_type': '',
            'posted_date': '',
            'requirements': '',
            'benefits': ''
        }
        
        # Extract title
        title_selectors = [
            'h1',
            '.job-title',
            '.title',
            '[class*="title"]',
            '[id*="title"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                job_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Extract company
        company_selectors = [
            '.company',
            '.employer',
            '[class*="company"]',
            '[class*="employer"]',
            '.job-company'
        ]
        
        for selector in company_selectors:
            company_elem = soup.select_one(selector)
            if company_elem:
                job_data['company'] = clean_text(company_elem.get_text())
                break
        
        # Extract location
        location_selectors = [
            '.location',
            '.job-location',
            '[class*="location"]',
            '.address'
        ]
        
        for selector in location_selectors:
            location_elem = soup.select_one(selector)
            if location_elem:
                job_data['location'] = format_location(clean_text(location_elem.get_text()))
                break
        
        # Extract description - prefer clean text from trafilatura
        if clean_text_content:
            job_data['description'] = clean_text(clean_text_content)
        else:
            # Fallback to HTML extraction
            desc_selectors = [
                '.description',
                '.job-description',
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
        
        # Extract job type
        job_type_keywords = ['full-time', 'part-time', 'contract', 'temporary', 'freelance', 'remote']
        full_text = f"{job_data['title']} {job_data['description']}".lower()
        
        for keyword in job_type_keywords:
            if keyword in full_text:
                job_data['job_type'] = keyword.title()
                break
        
        # Try to extract more specific information if present
        # This would need to be customized based on the actual site structure
        
        # Basic validation
        if not job_data['title'] and not job_data['company']:
            logger.warning(f"Could not extract basic job info from {url}")
            return None
        
        # Fill in missing required fields with defaults
        if not job_data['title']:
            job_data['title'] = "Job Opening"
        if not job_data['company']:
            job_data['company'] = "Company"
        if not job_data['location']:
            job_data['location'] = "Unknown Location"
        
        # Filter jobs by target regions
        if not self.is_target_region_job(job_data):
            logger.info(f"Skipping job not in target regions: {job_data['title']}")
            return None
        
        logger.info(f"Extracted target region job: {job_data['title']} at {job_data['company']} - {job_data['location']}")
        return job_data
    
    def scrape_jobs(self) -> List[Dict[str, Any]]:
        """Scrape jobs from multiple sources including South African job sites"""
        logger.info("Starting multi-source job scraping process")
        
        all_jobs = []
        
        # Scrape from each source
        for scraper in self.scrapers:
            try:
                source_name = scraper.__class__.__name__
                logger.info(f"Scraping from {source_name}")
                source_jobs = scraper.scrape_jobs()
                all_jobs.extend(source_jobs)
                logger.info(f"{source_name} contributed {len(source_jobs)} jobs")
                
                # Small delay between sources
                safe_sleep(3)
                
            except Exception as e:
                logger.error(f"Error scraping from {scraper.__class__.__name__}: {e}")
                continue
        
        # Also scrape from original JobServiceHub
        try:
            logger.info("Scraping from JobServiceHub")
            job_urls = self.get_job_listing_urls()
            
            for i, url in enumerate(job_urls[:10]):  # Limit to 10 from original source
                try:
                    job_data = self.extract_job_data(url)
                    if job_data:
                        all_jobs.append(job_data)
                    safe_sleep()
                except Exception as e:
                    logger.error(f"Error scraping job {url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping JobServiceHub: {e}")
        
        logger.info(f"Multi-source scraping completed. Found {len(all_jobs)} total jobs")
        return all_jobs

def test_scraper():
    """Test the scraper functionality."""
    scraper = JobServiceHubScraper()
    jobs = scraper.scrape_jobs()
    
    print(f"Scraped {len(jobs)} jobs")
    for job in jobs[:3]:  # Show first 3 jobs
        print(f"Title: {job['title']}")
        print(f"Company: {job['company']}")
        print(f"Location: {job['location']}")
        print(f"Description: {job['description'][:200]}...")
        print("-" * 50)

if __name__ == "__main__":
    test_scraper()
