import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class EmailNotifier:
    """Sends email notifications about job posting activities"""
    
    def __init__(self):
        # Email configuration - will be set from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.sender_email = os.getenv('SENDER_EMAIL', '')
        self.sender_password = os.getenv('SENDER_PASSWORD', '')
        self.recipient_email = 'vyrralblog@gmail.com'
        
    def create_job_summary_email(self, jobs_posted: List[Dict[str, Any]], 
                                jobs_failed: List[Dict[str, Any]], 
                                total_scraped: int) -> str:
        """Create HTML email content with job posting summary"""
        
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #f4f4f4; padding: 15px; margin: 20px 0; }}
                .success {{ color: #4CAF50; }}
                .error {{ color: #f44336; }}
                .job-list {{ margin: 10px 0; }}
                .job-item {{ background-color: #fff; border: 1px solid #ddd; padding: 10px; margin: 5px 0; }}
                .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 Job Scraping Bot Report</h1>
                <p>Automated Job Posting Summary</p>
            </div>
            
            <div class="summary">
                <h2>📊 Summary</h2>
                <p><strong>Report Generated:</strong> {current_time}</p>
                <p><strong>Total Jobs Scraped:</strong> {total_scraped}</p>
                <p><strong class="success">Successfully Posted:</strong> {len(jobs_posted)}</p>
                <p><strong class="error">Failed to Post:</strong> {len(jobs_failed)}</p>
            </div>
        """
        
        # Add successfully posted jobs
        if jobs_posted:
            html_content += """
            <div class="job-list">
                <h2 class="success">✅ Successfully Posted Jobs</h2>
            """
            for job in jobs_posted[:10]:  # Limit to first 10 for email size
                html_content += f"""
                <div class="job-item">
                    <h3>{job.get('title', 'Unknown Title')}</h3>
                    <p><strong>Company:</strong> {job.get('company', 'Unknown Company')}</p>
                    <p><strong>Location:</strong> {job.get('location', 'Unknown Location')}</p>
                    <p><strong>Source:</strong> <a href="{job.get('source_url', '#')}">View Original</a></p>
                </div>
                """
            
            if len(jobs_posted) > 10:
                html_content += f"<p><em>... and {len(jobs_posted) - 10} more jobs</em></p>"
            
            html_content += "</div>"
        
        # Add failed jobs if any
        if jobs_failed:
            html_content += """
            <div class="job-list">
                <h2 class="error">❌ Failed to Post</h2>
            """
            for job in jobs_failed[:5]:  # Limit to first 5 failed jobs
                html_content += f"""
                <div class="job-item">
                    <h3>{job.get('title', 'Unknown Title')}</h3>
                    <p><strong>Company:</strong> {job.get('company', 'Unknown Company')}</p>
                    <p><strong>Error:</strong> {job.get('error_message', 'Unknown error')}</p>
                </div>
                """
            html_content += "</div>"
        
        # Add footer
        html_content += f"""
            <div class="footer">
                <p>This is an automated report from your Job Scraping Bot.</p>
                <p>Bot is configured to run every 30 minutes, targeting jobs from South Africa, Dubai, UAE, and UK.</p>
                <p>Source: JobServiceHub.com → Destination: WizAdmissions.info</p>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_notification(self, jobs_posted: List[Dict[str, Any]], 
                         jobs_failed: List[Dict[str, Any]], 
                         total_scraped: int) -> bool:
        """Send email notification about job posting results"""
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured. Skipping email notification.")
            return False
        
        try:
            # Create the email content
            subject = f"Job Bot Report: {len(jobs_posted)} Jobs Posted Successfully"
            
            if jobs_failed:
                subject += f" ({len(jobs_failed)} Failed)"
            
            html_content = self.create_job_summary_email(jobs_posted, jobs_failed, total_scraped)
            
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            
            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send the email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Enable encryption
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            
            logger.info(f"Email notification sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def send_error_alert(self, error_message: str) -> bool:
        """Send a quick error alert email"""
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not configured. Skipping error alert.")
            return False
        
        try:
            subject = "🚨 Job Bot Error Alert"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <div style="background-color: #f44336; color: white; padding: 20px; text-align: center;">
                    <h1>⚠️ Job Bot Error</h1>
                </div>
                
                <div style="padding: 20px;">
                    <p><strong>Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p><strong>Error:</strong></p>
                    <pre style="background-color: #f4f4f4; padding: 10px; border-radius: 5px;">{error_message}</pre>
                </div>
                
                <div style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>Please check the bot logs for more details.</p>
                </div>
            </body>
            </html>
            """
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            
            logger.info("Error alert email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send error alert email: {e}")
            return False
    
    def test_email_setup(self) -> bool:
        """Test email configuration by sending a test email"""
        
        if not self.sender_email or not self.sender_password:
            logger.error("Email credentials not configured for testing")
            return False
        
        try:
            subject = "✅ Job Bot Email Test"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px;">
                <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center;">
                    <h1>🧪 Email Test Successful</h1>
                </div>
                
                <div style="padding: 20px;">
                    <p>This is a test email from your Job Scraping Bot.</p>
                    <p><strong>Test Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    <p>If you're receiving this, email notifications are working correctly!</p>
                </div>
                
                <div style="margin-top: 20px; font-size: 12px; color: #666;">
                    <p>Your bot is ready to send job posting notifications.</p>
                </div>
            </body>
            </html>
            """
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            
            logger.info("Test email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Email test failed: {e}")
            return False

def test_email_notifier():
    """Test the email notifier functionality"""
    notifier = EmailNotifier()
    
    # Test with sample data
    sample_jobs_posted = [
        {
            'title': 'Software Developer - Dubai',
            'company': 'Tech Solutions UAE',
            'location': 'Dubai, UAE',
            'source_url': 'https://example.com/job1'
        },
        {
            'title': 'Marketing Manager - London',
            'company': 'UK Marketing Ltd',
            'location': 'London, UK',
            'source_url': 'https://example.com/job2'
        }
    ]
    
    sample_jobs_failed = [
        {
            'title': 'Data Analyst - Cape Town',
            'company': 'SA Analytics',
            'error_message': 'Connection timeout'
        }
    ]
    
    return notifier.send_notification(sample_jobs_posted, sample_jobs_failed, 25)

if __name__ == "__main__":
    test_email_notifier()