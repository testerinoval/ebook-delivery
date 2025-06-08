import os, time
from models import db, RequestLog
import config
from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email

def sanitize_filename(title, author, ext):
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_Labri.{ext}"

def process_book_request(email, title, author, file_format=None):
    # mark processing
    req = RequestLog(email=email, book_title=title,
                     author_name=author, status="processing")
    db.session.add(req); db.session.commit()

    # 1) Ask Telegram bot
    tg.loop.run_until_complete(
        tg.send_message(config.BOOK_BOT_USERNAME, f"{title} - {author}")
    )

    # 2) Wait max 30 s for reply
    file_msg = None; start = time.time()
    while time.time() - start < 30:
        msgs = tg.loop.run_until_complete(
            tg.get_messages(config.BOOK_BOT_USERNAME, limit=5)
        )
        for m in msgs:
            if m.file:
                file_msg = m; break
        if file_msg: break
        time.sleep(2)

    if not file_msg:  # book missing
        send_email(config.ADMIN_EMAIL,
                   f"Missing book: {title}",
                   f"{email} requested “{title}” by {author} — not found.")
        send_email(email,
                   f"Request received: {title}",
                   "Hi,\nWe got your request and will send the book ASAP.")
        req.status = "missing"; db.session.commit(); return

    # 3) Download
    ext   = file_msg.file.ext or (file_format or "pdf")
    temp  = f"temp/{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=temp))

    # 4) Rename clean
    clean = sanitize_filename(title, author, ext)
    os.rename(temp, clean)

    # 5) Upload → Drive
    link = upload_and_share(clean, clean, config.GOOGLE_DRIVE_FOLDER_ID)

    # 6) Email client
    send_email(email,
               f"Your eBook: {title}",
               f"Hello,\n\nHere is your book link:\n{link}\n\nEnjoy!")

    # 7) finish
    req.status = "sent"; db.session.commit()
    os.remove(clean)
