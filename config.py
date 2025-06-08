import os

# Whitelisted emails
WHITELIST = {
    "labriny04@gmail.com",
    "client2@example.com",
    "client3@example.com",
    # … add your actual client emails here …
}

# Telegram (Telethon) settings
TELETHON_API_ID    = 25524348
TELETHON_API_HASH  = '8080c7f968006910f27df5d6f3fb401e'
TELETHON_PHONE     = '+212665492739'  # your number with country code
BOOK_BOT_USERNAME  = 'dasjda7bot'     # the bot you fetch from

# Google Drive (OAuth2)
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'service-account.json')
GOOGLE_DRIVE_FOLDER_ID = '1A6r8EItKZLyh9G2cjqP7kq0WUpQxOtMX'
# Gmail SMTP Settings
EMAIL_ADDRESS  = 'labthekidd@gmail.com'
EMAIL_PASSWORD = 'miqigdmwkatnkqyg'   # your 16-char app password, no spaces

# Admin email for “missing book” alerts
ADMIN_EMAIL    = 'labthekidd@gmail.com'

# Flask secret key
SECRET_KEY     = os.urandom(24)