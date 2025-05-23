import requests
import logging
import time
from typing import Dict, Any, Optional, List
from utils import get_random_user_agent, safe_sleep
from config import (
    WIZADMISSIONS_BASE_URL, 
    WIZADMISSIONS_API_KEY, 
    WIZADMISSIONS_USERNAME, 
    WIZADMISSIONS_PASSWORD,
    TIMEOUT,
    MAX_RETRIES
)

logger = logging.getLogger(__name__)

class WizAdmissionsPoster:
    """Posts job data to wizadmissions.info"""
    
    def __init__(self):
        self.base_url = WIZADMISSIONS_BASE_URL
        self.api_key = WIZADMISSIONS_API_KEY
        self.username = WIZADMISSIONS_USERNAME
        self.password = WIZADMISSIONS_PASSWORD
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': get_random_user_agent(),
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """Authenticate with wizadmissions.info"""
        if self.authenticated:
            return True
        
        # Try API key authentication first
        if self.api_key:
            self.session.headers['Authorization'] = f'Bearer {self.api_key}'
            if self._test_authentication():
                self.authenticated = True
                logger.info("Authenticated with API key")
                return True
        
        # Try username/password authentication
        if self.username and self.password:
            auth_data = {
                'username': self.username,
                'password': self.password
            }
            
            # Try common authentication endpoints
            auth_endpoints = [
                '/api/auth/login',
                '/auth/login',
                '/login',
                '/api/login'
            ]
            
            for endpoint in auth_endpoints:
                try:
                    url = self.base_url.rstrip('/') + endpoint
                    response = self.session.post(url, json=auth_data, timeout=TIMEOUT)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Look for token in response
                        token = data.get('token') or data.get('access_token') or data.get('auth_token')
                        if token:
                            self.session.headers['Authorization'] = f'Bearer {token}'
                            self.authenticated = True
                            logger.info("Authenticated with username/password")
                            return True
                        
                except Exception as e:
                    logger.debug(f"Auth attempt failed for {endpoint}: {e}")
                    continue
        
        logger.warning("Authentication failed - continuing without authentication")
        return False
    
    def _test_authentication(self) -> bool:
        """Test if current authentication is valid"""
        test_endpoints = [
            '/api/user/profile',
            '/api/jobs',
            '/api/test'
        ]
        
        for endpoint in test_endpoints:
            try:
                url = self.base_url.rstrip('/') + endpoint
                response = self.session.get(url, timeout=TIMEOUT)
                if response.status_code in [200, 401]:  # 401 means auth is being checked
                    return response.status_code == 200
            except:
                continue
        
        return False
    
    def discover_job_posting_endpoint(self) -> Optional[str]:
        """Discover the correct endpoint for posting jobs"""
        # Common job posting endpoints
        endpoints = [
            '/api/jobs',
            '/api/job/create',
            '/api/jobs/create',
            '/jobs/create',
            '/post-job',
            '/api/post-job',
            '/submit-job'
        ]
        
        for endpoint in endpoints:
            try:
                url = self.base_url.rstrip('/') + endpoint
                
                # Try a HEAD request first
                response = self.session.head(url, timeout=TIMEOUT)
                if response.status_code in [200, 405]:  # 405 means method not allowed but endpoint exists
                    logger.info(f"Found potential job posting endpoint: {endpoint}")
                    return endpoint
                
            except Exception as e:
                logger.debug(f"Endpoint discovery failed for {endpoint}: {e}")
                continue
        
        logger.warning("Could not discover job posting endpoint")
        return None
    
    def format_job_for_posting(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format job data for posting to wizadmissions.info"""
        formatted_job = {
            'title': job_data.get('title', ''),
            'company': job_data.get('company', ''),
            'location': job_data.get('location', ''),
            'description': job_data.get('description', ''),
            'job_type': job_data.get('job_type', 'Full-time'),
            'salary': job_data.get('salary', ''),
            'requirements': job_data.get('requirements', ''),
            'benefits': job_data.get('benefits', ''),
            'source_url': job_data.get('source_url', ''),
            'posted_by': 'Job Scraping Bot',
            'category': 'General',
            'status': 'active'
        }
        
        # Remove empty fields
        formatted_job = {k: v for k, v in formatted_job.items() if v}
        
        return formatted_job
    
    def post_job(self, job_data: Dict[str, Any]) -> bool:
        """Post a single job to wizadmissions.info"""
        if not self.authenticated:
            self.authenticate()
        
        # Format job data
        formatted_job = self.format_job_for_posting(job_data)
        
        # Discover posting endpoint if not known
        endpoint = self.discover_job_posting_endpoint()
        if not endpoint:
            endpoint = '/api/jobs'  # Default fallback
        
        url = self.base_url.rstrip('/') + endpoint
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Posting job: {formatted_job.get('title', 'Unknown')} (attempt {attempt + 1})")
                
                response = self.session.post(url, json=formatted_job, timeout=TIMEOUT)
                
                if response.status_code in [200, 201]:
                    logger.info(f"Successfully posted job: {formatted_job.get('title', 'Unknown')}")
                    return True
                elif response.status_code == 401:
                    logger.warning("Authentication failed, attempting to re-authenticate")
                    self.authenticated = False
                    if attempt == 0:  # Only retry authentication once
                        self.authenticate()
                        continue
                elif response.status_code == 409:
                    logger.info(f"Job already exists: {formatted_job.get('title', 'Unknown')}")
                    return True  # Consider as success since job is already there
                else:
                    logger.warning(f"Failed to post job (HTTP {response.status_code}): {response.text}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < MAX_RETRIES - 1:
                    safe_sleep(2 ** attempt)
                
        logger.error(f"Failed to post job after {MAX_RETRIES} attempts: {formatted_job.get('title', 'Unknown')}")
        return False
    
    def post_jobs_batch(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Post multiple jobs in batch"""
        results = {
            'success': 0,
            'failed': 0,
            'total': len(jobs)
        }
        
        logger.info(f"Starting batch posting of {len(jobs)} jobs")
        
        for i, job in enumerate(jobs):
            try:
                logger.info(f"Posting job {i+1}/{len(jobs)}")
                
                if self.post_job(job):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                # Add delay between posts
                safe_sleep(1)
                
            except Exception as e:
                logger.error(f"Error posting job {i+1}: {e}")
                results['failed'] += 1
        
        logger.info(f"Batch posting completed: {results['success']} success, {results['failed']} failed")
        return results
    
    def test_connection(self) -> bool:
        """Test connection to wizadmissions.info"""
        try:
            response = self.session.get(self.base_url, timeout=TIMEOUT)
            if response.status_code == 200:
                logger.info("Successfully connected to wizadmissions.info")
                return True
            else:
                logger.warning(f"Connection test failed (HTTP {response.status_code})")
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

def test_poster():
    """Test the poster functionality"""
    poster = WizAdmissionsPoster()
    
    # Test connection
    if not poster.test_connection():
        print("Failed to connect to wizadmissions.info")
        return
    
    # Test authentication
    poster.authenticate()
    
    # Test job posting with sample data
    sample_job = {
        'title': 'Test Software Developer Position',
        'company': 'Test Company Inc.',
        'location': 'Toronto, ON, Canada',
        'description': 'This is a test job posting created by the scraping bot.',
        'job_type': 'Full-time',
        'salary': '$70,000 - $90,000 CAD',
        'source_url': 'https://example.com/test-job'
    }
    
    result = poster.post_job(sample_job)
    print(f"Test posting result: {'Success' if result else 'Failed'}")

if __name__ == "__main__":
    test_poster()
