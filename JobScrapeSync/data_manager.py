import json
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils import generate_job_hash
from config import JOBS_DATABASE_FILE, PROCESSED_JOBS_FILE

logger = logging.getLogger(__name__)

class DataManager:
    """Manages job data storage and retrieval."""
    
    def __init__(self):
        self.jobs_db_file = JOBS_DATABASE_FILE
        self.processed_jobs_file = PROCESSED_JOBS_FILE
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure data files exist."""
        for file_path in [self.jobs_db_file, self.processed_jobs_file]:
            if not os.path.exists(file_path):
                with open(file_path, 'w') as f:
                    json.dump([], f)
                logger.info(f"Created data file: {file_path}")
    
    def load_jobs_database(self) -> List[Dict[str, Any]]:
        """Load all jobs from the database."""
        try:
            with open(self.jobs_db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading jobs database: {e}")
            return []
    
    def save_jobs_database(self, jobs: List[Dict[str, Any]]):
        """Save jobs to the database."""
        try:
            with open(self.jobs_db_file, 'w', encoding='utf-8') as f:
                json.dump(jobs, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(jobs)} jobs to database")
        except Exception as e:
            logger.error(f"Error saving jobs database: {e}")
    
    def load_processed_jobs(self) -> List[str]:
        """Load list of processed job hashes."""
        try:
            with open(self.processed_jobs_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading processed jobs: {e}")
            return []
    
    def save_processed_jobs(self, processed_hashes: List[str]):
        """Save list of processed job hashes."""
        try:
            with open(self.processed_jobs_file, 'w') as f:
                json.dump(processed_hashes, f, indent=2)
            logger.info(f"Saved {len(processed_hashes)} processed job hashes")
        except Exception as e:
            logger.error(f"Error saving processed jobs: {e}")
    
    def add_job(self, job_data: Dict[str, Any]) -> bool:
        """Add a new job to the database if it doesn't exist."""
        job_hash = generate_job_hash(job_data)
        
        # Add metadata
        job_data['hash'] = job_hash
        job_data['scraped_at'] = datetime.now().isoformat()
        job_data['posted_to_wizadmissions'] = False
        
        jobs = self.load_jobs_database()
        
        # Check if job already exists
        for existing_job in jobs:
            if existing_job.get('hash') == job_hash:
                logger.info(f"Job already exists: {job_data.get('title', 'Unknown')}")
                return False
        
        # Add new job
        jobs.append(job_data)
        self.save_jobs_database(jobs)
        logger.info(f"Added new job: {job_data.get('title', 'Unknown')}")
        return True
    
    def get_unposted_jobs(self) -> List[Dict[str, Any]]:
        """Get jobs that haven't been posted to wizadmissions yet."""
        jobs = self.load_jobs_database()
        return [job for job in jobs if not job.get('posted_to_wizadmissions', False)]
    
    def mark_job_as_posted(self, job_hash: str) -> bool:
        """Mark a job as posted to wizadmissions."""
        jobs = self.load_jobs_database()
        
        for job in jobs:
            if job.get('hash') == job_hash:
                job['posted_to_wizadmissions'] = True
                job['posted_at'] = datetime.now().isoformat()
                self.save_jobs_database(jobs)
                
                # Also add to processed jobs list
                processed = self.load_processed_jobs()
                if job_hash not in processed:
                    processed.append(job_hash)
                    self.save_processed_jobs(processed)
                
                logger.info(f"Marked job as posted: {job.get('title', 'Unknown')}")
                return True
        
        logger.warning(f"Job not found for marking as posted: {job_hash}")
        return False
    
    def is_job_processed(self, job_hash: str) -> bool:
        """Check if a job has been processed."""
        processed = self.load_processed_jobs()
        return job_hash in processed
    
    def get_job_stats(self) -> Dict[str, int]:
        """Get statistics about jobs in the database."""
        jobs = self.load_jobs_database()
        
        total_jobs = len(jobs)
        posted_jobs = len([job for job in jobs if job.get('posted_to_wizadmissions', False)])
        pending_jobs = total_jobs - posted_jobs
        
        return {
            'total_jobs': total_jobs,
            'posted_jobs': posted_jobs,
            'pending_jobs': pending_jobs
        }
    
    def cleanup_old_jobs(self, days: int = 30):
        """Remove jobs older than specified days."""
        jobs = self.load_jobs_database()
        cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        filtered_jobs = []
        removed_count = 0
        
        for job in jobs:
            scraped_at = job.get('scraped_at')
            if scraped_at:
                try:
                    job_date = datetime.fromisoformat(scraped_at).timestamp()
                    if job_date >= cutoff_date:
                        filtered_jobs.append(job)
                    else:
                        removed_count += 1
                except ValueError:
                    # Keep jobs with invalid dates
                    filtered_jobs.append(job)
            else:
                # Keep jobs without dates
                filtered_jobs.append(job)
        
        if removed_count > 0:
            self.save_jobs_database(filtered_jobs)
            logger.info(f"Cleaned up {removed_count} old jobs")
        
        return removed_count
