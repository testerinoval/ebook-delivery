from email_sender import send_email

# Send a test mail to yourself
send_email(
    to_email="Labriny04@gmail.com",
    subject="📚 E-Book Delivery Test",
    body="If you see this, your Gmail SMTP integration works!"
)
