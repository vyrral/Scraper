#!/usr/bin/env python3
"""
Job Scraping Bot - Main Entry Point

This bot scrapes job postings from jobservicehub.com and posts them to wizadmissions.info.
It provides both command-line interface and web interface for operation.
"""

import argparse
import logging
import sys
import os
from scheduler import JobBot
from web_interface import app
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE

def setup_logging():
    """Set up logging configuration"""
    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_web_interface():
    """Run the web interface"""
    print("Starting Job Scraping Bot Web Interface...")
    print("Access the dashboard at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)

def run_cli_bot():
    """Run the bot in CLI mode"""
    print("Starting Job Scraping Bot in CLI mode...")
    bot = JobBot()
    
    try:
        bot.start_scheduler()
    except KeyboardInterrupt:
        print("\nBot interrupted by user")
        bot.stop()
    except Exception as e:
        print(f"Unexpected error: {e}")
        bot.stop()

def run_single_cycle():
    """Run a single bot cycle"""
    print("Running single bot cycle...")
    bot = JobBot()
    bot.manual_run()
    print("Single cycle completed")

def main():
    """Main entry point"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='Job Scraping Bot')
    parser.add_argument(
        '--mode', 
        choices=['web', 'cli', 'single'], 
        default='web',
        help='Run mode: web interface, CLI daemon, or single cycle (default: web)'
    )
    parser.add_argument(
        '--test-scraper',
        action='store_true',
        help='Test the scraper functionality'
    )
    parser.add_argument(
        '--test-poster',
        action='store_true',
        help='Test the poster functionality'
    )
    parser.add_argument(
        '--test-connections',
        action='store_true',
        help='Test connections to both websites'
    )
    
    args = parser.parse_args()
    
    # Handle test modes
    if args.test_scraper:
        print("Testing scraper...")
        from scraper import test_scraper
        test_scraper()
        return
    
    if args.test_poster:
        print("Testing poster...")
        from poster import test_poster
        test_poster()
        return
    
    if args.test_connections:
        print("Testing connections...")
        from scraper import JobServiceHubScraper
        from poster import WizAdmissionsPoster
        
        scraper = JobServiceHubScraper()
        poster = WizAdmissionsPoster()
        
        scraper_test = scraper.fetch_page(scraper.base_url) is not None
        poster_test = poster.test_connection()
        
        print(f"JobServiceHub connection: {'✓' if scraper_test else '✗'}")
        print(f"WizAdmissions connection: {'✓' if poster_test else '✗'}")
        return
    
    # Handle run modes
    if args.mode == 'web':
        run_web_interface()
    elif args.mode == 'cli':
        run_cli_bot()
    elif args.mode == 'single':
        run_single_cycle()

if __name__ == "__main__":
    main()
