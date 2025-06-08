import smtplib
from email.message import EmailMessage
import config

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg['From'] = config.EMAIL_ADDRESS
    msg['To']   = to_email
    msg['Subject'] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
        smtp.send_message(msg)
    print(f"✅ Email sent to {to_email}")
