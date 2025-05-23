import requests
import logging
import json
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import base64
from utils import clean_text

logger = logging.getLogger(__name__)

class WordPressPoster:
    """Posts job data to WordPress site using WP Job Manager"""

    def __init__(self, site_url: str, username: str, password: str):
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.auth_token = None
        self.api_base = f"{self.site_url}/wp-json/wp/v2"

        # Set up authentication
        self._setup_authentication()

    def _setup_authentication(self):
        """Set up WordPress authentication"""
        try:
            # First try basic auth
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            self.session.headers.update({
                'Authorization': f'Basic {encoded_credentials}',
                'Content-Type': 'application/json',
                'User-Agent': 'Job-Scraping-Bot/1.0'
            })

            logger.info("WordPress authentication configured")

        except Exception as e:
            logger.error(f"Error setting up WordPress authentication: {e}")

    def test_connection(self) -> bool:
        """Test connection to WordPress site"""
        try:
            # Test basic connectivity
            response = self.session.get(f"{self.site_url}/wp-json/")
            if response.status_code == 200:
                logger.info("WordPress site is accessible")

                # Test authentication by getting user info
                auth_response = self.session.get(f"{self.api_base}/users/me")
                if auth_response.status_code == 200:
                    user_data = auth_response.json()
                    logger.info(f"Authenticated as: {user_data.get('name', 'Unknown')}")
                    return True
                else:
                    logger.warning(f"Authentication test failed: {auth_response.status_code}")
                    return False
            else:
                logger.error(f"Cannot access WordPress site: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error testing WordPress connection: {e}")
            return False

    def create_application_password(self) -> Optional[str]:
        """Create an application password for API access"""
        try:
            # This requires the user to manually create an application password
            # We'll provide instructions for this
            logger.info("To use the WordPress API, you need to create an application password:")
            logger.info("1. Log into your WordPress admin dashboard")
            logger.info("2. Go to Users > Profile")
            logger.info("3. Scroll down to 'Application Passwords'")
            logger.info("4. Enter 'Job Scraping Bot' as the name")
            logger.info("5. Click 'Add New Application Password'")
            logger.info("6. Copy the generated password and use it instead of your regular password")

            return None

        except Exception as e:
            logger.error(f"Error with application password: {e}")
            return None

    def get_job_categories(self) -> List[Dict[str, Any]]:
        """Get available job categories from WP Job Manager"""
        try:
            response = self.session.get(f"{self.api_base}/job_listing_category")
            if response.status_code == 200:
                categories = response.json()
                logger.info(f"Found {len(categories)} job categories")
                return categories
            else:
                logger.warning(f"Could not fetch job categories: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching job categories: {e}")
            return []

    def get_job_types(self) -> List[Dict[str, Any]]:
        """Get available job types from WP Job Manager"""
        try:
            response = self.session.get(f"{self.api_base}/job_listing_type")
            if response.status_code == 200:
                types = response.json()
                logger.info(f"Found {len(types)} job types")
                return types
            else:
                logger.warning(f"Could not fetch job types: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching job types: {e}")
            return []

    def format_job_for_wordpress(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format job data for WordPress WP Job Manager posting"""

        # Clean and prepare the description
        description = clean_text(job_data.get('description', ''))
        if len(description) > 5000:
            description = description[:5000] + "..."

        # Prepare the WordPress post data with April 2026 expiration
        wp_job_data = {
            'title': clean_text(job_data.get('title', 'Job Opening')),
            'content': description,
            'status': 'publish',
            'type': 'job_listing',
            'meta': {
                '_company_name': clean_text(job_data.get('company', 'Company')),
                '_job_location': clean_text(job_data.get('location', '')),
                '_job_expires': '2026-04-30',  # Set to April 2026 as requested
                '_filled': '0',
                '_featured': '0',
                '_remote_position': '0',
                '_application_method': 'external',
                '_job_applying_url': job_data.get('source_url', ''),
                '_company_website': '',
                '_company_tagline': '',
                '_company_description': '',
                '_company_logo': '',
            }
        }

        # Add salary if available
        if job_data.get('salary'):
            wp_job_data['meta']['_job_salary'] = clean_text(job_data['salary'])

        # Set remote position if indicated
        location_lower = job_data.get('location', '').lower()
        if 'remote' in location_lower or 'work from home' in description.lower():
            wp_job_data['meta']['_remote_position'] = '1'

        return wp_job_data

    def post_job(self, job_data: Dict[str, Any]) -> bool:
        """Post a single job to WordPress"""
        try:
            # Format job data for WordPress
            wp_job_data = self.format_job_for_wordpress(job_data)

            logger.info(f"Posting job: {wp_job_data['title']}")

            # Post to WordPress
            response = self.session.post(
                f"{self.api_base}/job-listings",
                json=wp_job_data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code in [200, 201]:
                post_data = response.json()
                job_id = post_data.get('id')
                logger.info(f"Successfully posted job: {wp_job_data['title']} (ID: {job_id})")
                return True
            else:
                logger.error(f"Failed to post job: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error posting job to WordPress: {e}")
            return False

    def post_jobs_batch(self, jobs: List[Dict[str, Any]]) -> Dict[str, int]:
        """Post multiple jobs in batch"""
        results = {'posted': 0, 'failed': 0}

        for job in jobs:
            try:
                if self.post_job(job):
                    results['posted'] += 1
                else:
                    results['failed'] += 1

                # Small delay between posts
                import time
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in batch posting: {e}")
                results['failed'] += 1

        logger.info(f"Batch posting completed: {results['posted']} posted, {results['failed']} failed")
        return results

    def check_job_exists(self, job_title: str, company: str) -> bool:
        """Check if a job already exists to avoid duplicates"""
        try:
            # Search for existing jobs with similar title and company
            search_params = {
                'search': f"{job_title} {company}",
                'type': 'job_listing',
                'status': 'publish'
            }

            response = self.session.get(f"{self.api_base}/job_listing", params=search_params)

            if response.status_code == 200:
                existing_jobs = response.json()
                return len(existing_jobs) > 0
            else:
                return False

        except Exception as e:
            logger.error(f"Error checking for duplicate jobs: {e}")
            return False

def test_wordpress_poster():
    """Test the WordPress poster functionality"""
    # This would use the credentials from config
    from config import WIZADMISSIONS_BASE_URL, WIZADMISSIONS_USERNAME, WIZADMISSIONS_PASSWORD

    poster = WordPressPoster(WIZADMISSIONS_BASE_URL, WIZADMISSIONS_USERNAME, WIZADMISSIONS_PASSWORD)

    # Test connection
    if poster.test_connection():
        print("✓ WordPress connection successful")

        # Get available categories and types
        categories = poster.get_job_categories()
        types = poster.get_job_types()

        print(f"Available categories: {len(categories)}")
        print(f"Available job types: {len(types)}")

    else:
        print("✗ WordPress connection failed")

if __name__ == "__main__":
    test_wordpress_poster()