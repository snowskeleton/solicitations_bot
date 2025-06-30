import smtplib

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from Solicitation import Solicitations

from env import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_ADDRESS
from exceptions import MailError


def send_summary_email(to_address: str, solicitations: Solicitations):
    body = solicitations.to_html()

    today = datetime.now().strftime("%Y-%m-%d")

    send_email(to_address, f"Solicitation Summary for {today}", body)


def send_email(to_address: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = FROM_ADDRESS
        msg["To"] = to_address
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(FROM_ADDRESS, to_address, msg.as_string())
    except Exception as e:
        raise MailError(f"Failed to send email: {e}") from e
