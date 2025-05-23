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

class Careers247Scraper:
    """Scraper for 247careers.co.za and related sites"""
    
    def __init__(self):
        self.base_urls = [
            "https://www.247careers.co.za/",
            "https://247vacancies4fresherz.com/"
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling and retries."""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Fetching 247Careers: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
                
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"247Careers request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    safe_sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to fetch {url} after {MAX_RETRIES} attempts")
        
        return None
    
    def get_job_listing_urls(self) -> List[str]:
        """Get URLs of job listing pages from 247Careers sites"""
        job_urls = []
        
        for base_url in self.base_urls:
            try:
                html = self.fetch_page(base_url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for job links
                job_link_selectors = [
                    'a[href*="/job"]',
                    'a[href*="/vacancy"]',
                    'a[href*="/career"]',
                    '.job-title a',
                    '.job-link a',
                    'h3 a',
                    'h2 a',
                    '.post-title a'
                ]
                
                for selector in job_link_selectors:
                    links = soup.select(selector)
                    for link in links:
                        href = link.get('href')
                        if href and isinstance(href, str):
                            if href.startswith('/'):
                                full_url = urljoin(base_url, href)
                            else:
                                full_url = href
                            
                            # Check if it's from our target sites
                            if any(domain in full_url for domain in ['247careers.co.za', '247vacancies4fresherz.com']):
                                if full_url not in job_urls:
                                    job_urls.append(full_url)
                
            except Exception as e:
                logger.error(f"Error scraping {base_url}: {e}")
                continue
        
        logger.info(f"Found {len(job_urls)} 247Careers job URLs")
        return job_urls[:30]  # Limit to first 30 jobs total
    
    def extract_job_data(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract job data from a 247Careers job posting page"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Use trafilatura to get clean text content
        clean_text_content = trafilatura.extract(html)
        
        # Determine source based on URL
        source = "247Careers"
        if "247vacancies4fresherz.com" in url:
            source = "247Vacancies"
        
        job_data = {
            'source_url': url,
            'title': '',
            'company': '',
            'location': 'South Africa',  # Default for most 247careers
            'description': '',
            'salary': '',
            'job_type': '',
            'posted_date': '',
            'requirements': '',
            'benefits': '',
            'source': source
        }
        
        # Extract title
        title_selectors = [
            'h1.entry-title',
            'h1.post-title',
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
        
        # Extract company (often in the content)
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
        
        # Extract location - look for location keywords in content
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
                break
        
        # If no specific location found, check content for location keywords
        if not job_data['location'] or job_data['location'] == 'South Africa':
            content_text = clean_text_content or ''
            # Look for location keywords in the content
            for region in TARGET_REGIONS:
                if region.lower() in content_text.lower():
                    job_data['location'] = region.title()
                    break
        
        # Extract description
        if clean_text_content:
            job_data['description'] = clean_text(clean_text_content)
        else:
            desc_selectors = [
                '.entry-content',
                '.post-content',
                '.job-description',
                '.description',
                '.content'
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
        if not job_data['company']:
            job_data['company'] = "Company"
        
        logger.info(f"Extracted 247Careers job: {job_data['title']} - {job_data['location']}")
        return job_data
    
    def scrape_jobs(self) -> List[Dict[str, Any]]:
        """Scrape all available jobs from 247Careers sites"""
        logger.info("Starting 247Careers job scraping process")
        
        job_urls = self.get_job_listing_urls()
        
        if not job_urls:
            logger.warning("No 247Careers job URLs found")
            return []
        
        jobs = []
        
        for i, url in enumerate(job_urls):
            try:
                logger.info(f"Scraping 247Careers job {i+1}/{len(job_urls)}: {url}")
                
                job_data = self.extract_job_data(url)
                if job_data:
                    jobs.append(job_data)
                
                safe_sleep()
                
            except Exception as e:
                logger.error(f"Error scraping 247Careers job {url}: {e}")
                continue
        
        logger.info(f"247Careers scraping completed. Found {len(jobs)} jobs")
        return jobs