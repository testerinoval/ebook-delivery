import os, time
from models import db, RequestLog
import config
from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email

def sanitize_filename(title, author, ext):
    base = f"{title}_{author}".replace(' ', '_')
    safe = ''.join(c for c in base if c.isalnum() or c=='_')[:50]
    return f"{safe}_YourName.{ext}"

def process_book_request(email, title, author, file_format=None):
    # Log & mark processing
    req = RequestLog(email=email, book_title=title, author_name=author, status='processing')
    db.session.add(req); db.session.commit()

    # 1) Send request to book bot
    message = f"{title} - {author}"
    tg.loop.run_until_complete(
        tg.send_message(config.BOOK_BOT_USERNAME, message)
    )

    # 2) Wait up to 30s for reply with a file
    file_msg = None
    start = time.time()
    while time.time() - start < 30:
        msgs = tg.loop.run_until_complete(
            tg.get_messages(config.BOOK_BOT_USERNAME, limit=5)
        )
        for m in msgs:
            if m.file:
                file_msg = m
                break
        if file_msg:
            break
        time.sleep(2)

    if not file_msg:
        # missing
        send_email(
            config.ADMIN_EMAIL,
            f"Missing book: {title}",
            f"{email} requested “{title}” by {author} — not found."
        )
        send_email(
            email,
            f"Request received: {title}",
            f"Hi,\nWe got your request for “{title}.” We’ll email you once it’s available."
        )
        req.status = 'missing'
        db.session.commit()
        return

    # 3) Download
    ext = file_msg.file.ext or (file_format or 'pdf')
    local = f"temp/{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local))

    # 4) Rename
    clean = sanitize_filename(title, author, ext)
    os.rename(local, clean)

    # 5) Upload & share
    link = upload_and_share(clean, clean, config.GOOGLE_DRIVE_FOLDER_ID)

    # 6) Email client
    send_email(
        email,
        f"Your eBook is ready: {title}",
        f"Hello,\n\nHere is your book:\n{link}\n\nEnjoy!"
    )

    # 7) Mark sent & cleanup
    req.status = 'sent'
    db.session.commit()
    os.remove(clean)
