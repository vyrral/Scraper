from flask import Flask, render_template, jsonify, request
import logging
from datetime import datetime
from scheduler import JobBot
from data_manager import DataManager
import threading
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = None
bot_thread = None
data_manager = DataManager()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get bot status and statistics"""
    try:
        stats = data_manager.get_job_stats()
        
        status = {
            'bot_running': bot.running if bot else False,
            'job_stats': stats,
            'last_update': datetime.now().isoformat()
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/jobs')
def get_jobs():
    """Get list of jobs"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status_filter = request.args.get('status', 'all')
        
        all_jobs = data_manager.load_jobs_database()
        
        # Filter jobs based on status
        if status_filter == 'posted':
            filtered_jobs = [job for job in all_jobs if job.get('posted_to_wizadmissions', False)]
        elif status_filter == 'pending':
            filtered_jobs = [job for job in all_jobs if not job.get('posted_to_wizadmissions', False)]
        else:
            filtered_jobs = all_jobs
        
        # Sort by scraped date (most recent first)
        filtered_jobs.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
        
        # Pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_jobs = filtered_jobs[start:end]
        
        return jsonify({
            'jobs': paginated_jobs,
            'total': len(filtered_jobs),
            'page': page,
            'per_page': per_page,
            'total_pages': (len(filtered_jobs) + per_page - 1) // per_page
        })
        
    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_bot():
    """Start the bot"""
    global bot, bot_thread
    
    try:
        if bot and bot.running:
            return jsonify({'message': 'Bot is already running'}), 400
        
        bot = JobBot()
        bot_thread = bot.start_background()
        
        logger.info("Bot started via web interface")
        return jsonify({'message': 'Bot started successfully'})
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_bot():
    """Stop the bot"""
    global bot
    
    try:
        if bot:
            bot.stop()
            logger.info("Bot stopped via web interface")
            return jsonify({'message': 'Bot stopped successfully'})
        else:
            return jsonify({'message': 'Bot is not running'}), 400
            
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-manual', methods=['POST'])
def run_manual():
    """Manually run one bot cycle"""
    global bot
    
    try:
        if not bot:
            bot = JobBot()
        
        # Run in a separate thread to avoid blocking the web interface
        thread = threading.Thread(target=bot.manual_run)
        thread.daemon = True
        thread.start()
        
        logger.info("Manual bot run started via web interface")
        return jsonify({'message': 'Manual run started'})
        
    except Exception as e:
        logger.error(f"Error running manual cycle: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    """Get recent log entries"""
    try:
        lines = request.args.get('lines', 100, type=int)
        
        try:
            with open('bot.log', 'r') as f:
                log_lines = f.readlines()
                recent_logs = log_lines[-lines:]
                return jsonify({'logs': ''.join(recent_logs)})
        except FileNotFoundError:
            return jsonify({'logs': 'No log file found'})
            
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-connection', methods=['POST'])
def test_connection():
    """Test connections to source and target sites"""
    try:
        from scraper import JobServiceHubScraper
        from poster import WizAdmissionsPoster
        
        scraper = JobServiceHubScraper()
        poster = WizAdmissionsPoster()
        
        # Test scraper connection
        scraper_test = scraper.fetch_page(scraper.base_url) is not None
        
        # Test poster connection
        poster_test = poster.test_connection()
        
        return jsonify({
            'scraper_connection': scraper_test,
            'poster_connection': poster_test
        })
        
    except Exception as e:
        logger.error(f"Error testing connections: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
