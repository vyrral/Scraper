import schedule
import time
import logging
from datetime import datetime
from threading import Thread
from scraper import JobServiceHubScraper
from wordpress_poster import WordPressPoster
from email_notifier import EmailNotifier
from data_manager import DataManager
from utils import validate_job_data, sanitize_job_data
from config import SCRAPE_INTERVAL_MINUTES, BATCH_SIZE, WIZADMISSIONS_BASE_URL, WIZADMISSIONS_USERNAME, WIZADMISSIONS_PASSWORD

logger = logging.getLogger(__name__)

class JobBot:
    """Main job scraping and posting bot"""

    def __init__(self):
        self.scraper = JobServiceHubScraper()
        self.wordpress_poster = WordPressPoster(WIZADMISSIONS_BASE_URL, WIZADMISSIONS_USERNAME, WIZADMISSIONS_PASSWORD)
        self.email_notifier = EmailNotifier()
        self.data_manager = DataManager()
        self.running = False

    def scrape_and_store_jobs(self):
        """Scrape jobs and store them in the database"""
        logger.info("Starting job scraping process")

        try:
            # Scrape jobs from JobServiceHub
            scraped_jobs = self.scraper.scrape_jobs()

            if not scraped_jobs:
                logger.warning("No jobs scraped")
                return 0

            # Process and store each job
            new_jobs_count = 0
            for job_data in scraped_jobs:
                try:
                    # Validate and sanitize job data
                    if not validate_job_data(job_data):
                        continue

                    sanitized_job = sanitize_job_data(job_data)

                    # Add to database
                    if self.data_manager.add_job(sanitized_job):
                        new_jobs_count += 1

                except Exception as e:
                    logger.error(f"Error processing job: {e}")
                    continue

            logger.info(f"Scraping completed: {new_jobs_count} new jobs added")
            return new_jobs_count

        except Exception as e:
            logger.error(f"Error during scraping process: {e}")
            return 0

    def post_pending_jobs(self):
        """Post jobs that haven't been posted to wizadmissions yet"""
        logger.info("Starting job posting process")

        jobs_posted = []
        jobs_failed = []

        try:
            # Get unposted jobs
            pending_jobs = self.data_manager.get_unposted_jobs()

            if not pending_jobs:
                logger.info("No pending jobs to post")
                return jobs_posted, jobs_failed

            logger.info(f"Found {len(pending_jobs)} pending jobs")

            # Post jobs in batches
            for i in range(0, len(pending_jobs), BATCH_SIZE):
                batch = pending_jobs[i:i + BATCH_SIZE]
                logger.info(f"Processing batch {i//BATCH_SIZE + 1}: {len(batch)} jobs")

                for job in batch:
                    try:
                        if self.wordpress_poster.post_job(job):
                            self.data_manager.mark_job_as_posted(job['hash'])
                            jobs_posted.append(job)
                            logger.info(f"Successfully posted: {job.get('title', 'Unknown')}")
                        else:
                            job['error_message'] = "WordPress posting failed"
                            jobs_failed.append(job)
                            logger.error(f"Failed to post: {job.get('title', 'Unknown')}")

                    except Exception as e:
                        error_msg = f"Error posting job {job.get('title', 'Unknown')}: {e}"
                        logger.error(error_msg)
                        job['error_message'] = str(e)
                        jobs_failed.append(job)

                # Small delay between batches
                if i + BATCH_SIZE < len(pending_jobs):
                    time.sleep(5)

            logger.info(f"Posting completed: {len(jobs_posted)} posted, {len(jobs_failed)} failed")
            return jobs_posted, jobs_failed

        except Exception as e:
            logger.error(f"Error during posting process: {e}")
            return jobs_posted, jobs_failed

    def run_bot_cycle(self):
        """Run one complete bot cycle: scrape and post"""
        logger.info("=" * 50)
        logger.info(f"Starting bot cycle at {datetime.now()}")

        total_scraped = 0
        jobs_posted = []
        jobs_failed = []

        try:
            # Step 1: Scrape new jobs
            scraped_count = self.scrape_and_store_jobs()
            total_scraped = scraped_count or 0

            # Step 2: Post pending jobs
            jobs_posted, jobs_failed = self.post_pending_jobs()

            # Step 3: Send email notification if jobs were posted
            if jobs_posted or jobs_failed:
                try:
                    self.email_notifier.send_notification(jobs_posted, jobs_failed, total_scraped)
                    logger.info("Email notification sent successfully")
                except Exception as e:
                    logger.error(f"Failed to send email notification: {e}")

            # Step 4: Cleanup old jobs (optional)
            removed_count = self.data_manager.cleanup_old_jobs(days=30)
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} old jobs")

            # Step 5: Log statistics
            stats = self.data_manager.get_job_stats()
            logger.info(f"Bot statistics: {stats}")
            logger.info(f"This cycle: {len(jobs_posted)} posted, {len(jobs_failed)} failed")

        except Exception as e:
            logger.error(f"Error in bot cycle: {e}")
            # Send error alert email
            try:
                self.email_notifier.send_error_alert(str(e))
            except:
                pass

        logger.info(f"Bot cycle completed at {datetime.now()}")
        logger.info("=" * 50)

    def start_scheduler(self):
        """Start the scheduled bot runs"""
        logger.info(f"Starting job scheduler (interval: {SCRAPE_INTERVAL_MINUTES} minutes)")

        # Schedule the bot to run every 30 minutes
        schedule.every(SCRAPE_INTERVAL_MINUTES).minutes.do(self.run_bot_cycle)

        # Also schedule a daily cleanup
        schedule.every().day.at("02:00").do(self.data_manager.cleanup_old_jobs)

        # Run immediately on start
        self.run_bot_cycle()

        self.running = True

        # Main scheduler loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping bot")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)

    def start_background(self):
        """Start the bot in a background thread"""
        thread = Thread(target=self.start_scheduler, daemon=True)
        thread.start()
        logger.info("Bot started in background")
        return thread

    def stop(self):
        """Stop the bot"""
        self.running = False
        logger.info("Bot stopped")

    def manual_run(self):
        """Run a single scraping cycle"""
        logger.info("Starting manual scraping cycle")
        all_jobs = []
        for scraper in self.scrapers:
            logger.info(f"Running scraper: {scraper.__class__.__name__}")
            jobs = scraper.scrape_jobs()
            all_jobs.extend(jobs)

    def get_status(self) -> dict:
        """Get current bot status"""
        stats = self.data_manager.get_job_stats()

        return {
            'running': self.running,
            'last_run': datetime.now().isoformat(),
            'next_run': schedule.next_run().isoformat() if schedule.jobs else None,
            'job_stats': stats
        }

def main():
    """Main entry point for the bot"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )

    # Create and start the bot
    bot = JobBot()

    try:
        bot.start_scheduler()
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        bot.stop()

if __name__ == "__main__":
    main()