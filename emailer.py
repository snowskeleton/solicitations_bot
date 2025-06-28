import smtplib

from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
from Solicitation import Solicitation

from email_secrets import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_ADDRESS
from exceptions import MailError


def send_summary_email(to_address: str, solicitations: List[Solicitation]):
    body = build_solicitation_email_body(solicitations)

    today = datetime.now().strftime("%Y-%m-%d")

    send_email(to_address, f"Solicitation Summary for {today}", body)


def build_solicitation_email_body(solicitations: List[Solicitation]) -> str:
    if not solicitations:
        return "No solicitations found."

    body_lines: List[str] = []
    body_lines.append("<h2>Solicitations Summary:</h2><ul>")
    for s in solicitations:
        job_link = f"https://evp.nc.gov/solicitations/details/?id={s.Id}"
        body_lines.append("<li>")
        body_lines.append(f'<strong>Name:</strong> <a href="{job_link}">{s.evp_name}</a><br>')
        body_lines.append(f"<strong>Business Unit:</strong> {s.owningbusinessunit}<br>")
        body_lines.append(f"<strong>Number:</strong> {s.evp_solicitationnbr}<br>")
        body_lines.append(f"<strong>Status:</strong> {s.statuscode}<br>")
        body_lines.append(f"<strong>Open Date:</strong> {s.evp_opendate}<br>")
        body_lines.append(f"<strong>Description:</strong> {s.evp_description}<br>")
        body_lines.append("</li>")
    body_lines.append("</ul>")
    return "\n".join(body_lines)


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
