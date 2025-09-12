import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()


class EmailService:
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST')
        self.email_port = int(os.getenv('EMAIL_PORT', 587))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')

    def send(self, subject: str, to_email: str, html_content: str):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_user
        msg['To'] = to_email
        part = MIMEText(html_content, 'html')
        msg.attach(part)

        with smtplib.SMTP(self.email_host, self.email_port) as server:
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

class EmailService:
    def __init__(self):
        self.email_host = os.getenv('EMAIL_HOST')
        self.email_port = int(os.getenv('EMAIL_PORT', 587))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')

    def send(self, subject: str, to_email: str, html_content: str):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.email_user
        msg['To'] = to_email
        part = MIMEText(html_content, 'html')
        msg.attach(part)

        with smtplib.SMTP(self.email_host, self.email_port) as server:
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
