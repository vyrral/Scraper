import os
import logging

# Configuration settings for the job scraping bot

# URLs
JOBSERVICEHUB_BASE_URL = "https://www.jobservicehub.com/"
WIZADMISSIONS_BASE_URL = "https://wizadmissions.info"

# WordPress credentials for wizadmissions.info
WIZADMISSIONS_USERNAME = "wizadmissions"
WIZADMISSIONS_PASSWORD = "xEPq LxNJ pvz2 l6IM lwfm eExd"
WIZADMISSIONS_API_KEY = "wp_job_manager_api_key"  # Add your API key here

# Target regions for job scraping
TARGET_REGIONS = [
    "south africa", "south african", "cape town", "johannesburg", "durban",
    "dubai", "uae", "united arab emirates", "abu dhabi",
    "uk", "united kingdom", "london", "manchester", "birmingham", "glasgow", "edinburgh"
]

# Email notification settings
EMAIL_RECIPIENT = "vyrralblog@gmail.com"

# Scraping settings
REQUEST_DELAY = 2  # Delay between requests in seconds
MAX_RETRIES = 3
TIMEOUT = 30

# Data storage
JOBS_DATABASE_FILE = "jobs_database.json"
PROCESSED_JOBS_FILE = "processed_jobs.json"

# Logging configuration
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = "bot.log"

# Scheduling
SCRAPE_INTERVAL_MINUTES = 30  # How often to run the scraper (in minutes)

# Job posting settings
BATCH_SIZE = 10  # Number of jobs to process in one batch
MAX_DESCRIPTION_LENGTH = 5000  # Maximum length for job descriptions

# User agents for web scraping
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]
