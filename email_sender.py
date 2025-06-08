import smtplib, ssl, os
from email.message import EmailMessage

EMAIL = os.getenv("EMAIL_ADDRESS", "labthekidd@gmail.com")
PW    = os.getenv("EMAIL_PASSWORD", "miqigdmwkatnkqyg")

def send_email(to, subject, body):
    msg = EmailMessage()
    msg["From"] = EMAIL
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as smtp:
        smtp.login(EMAIL, PW)
        smtp.send_message(msg)
