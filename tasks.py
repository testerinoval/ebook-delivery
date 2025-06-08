# tasks.py  (detached-instance bug fixed)

import os, time
from pathlib import Path

from models import db, RequestLog
import config
from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email
from app import app as flask_app


def sanitize_filename(title, author, ext):
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_YourName.{ext}"


def process_book_request(email, title, author, file_format=None):
    # 1) create row, capture id
    with flask_app.app_context():
        req = RequestLog(email=email, book_title=title,
                         author_name=author, status="processing")
        db.session.add(req); db.session.commit()
        req_id = req.id

    # 2) ask Telegram bot
    tg.loop.run_until_complete(
        tg.send_message(config.BOOK_BOT_USERNAME, f"{title} - {author}")
    )
    file_msg = None
    start = time.time()
    while time.time() - start < 30:
        msgs = tg.loop.run_until_complete(
            tg.get_messages(config.BOOK_BOT_USERNAME, limit=5)
        )
        for m in msgs:
            if m.file or "/book" in m.raw_text:
                file_msg = m; break
        if file_msg: break
        time.sleep(2)

    # 2b) if list, send first /book…
    if file_msg and not file_msg.file:
        cmd = next((t for t in file_msg.raw_text.split() if t.startswith("/book")), None)
        if cmd:
            tg.loop.run_until_complete(
                tg.send_message(config.BOOK_BOT_USERNAME, cmd)
            )
            start = time.time()
            while time.time() - start < 30 and not (file_msg and file_msg.file):
                msgs = tg.loop.run_until_complete(
                    tg.get_messages(config.BOOK_BOT_USERNAME, limit=3)
                )
                for m in msgs:
                    if m.file:
                        file_msg = m; break
                if file_msg and file_msg.file: break
                time.sleep(2)

    # 3) missing?
    if not (file_msg and file_msg.file):
        send_email(config.ADMIN_EMAIL,
                   f"Missing book: {title}",
                   f"{email} requested “{title}” by {author} — not found.")
        send_email(email,
                   f"We’re still searching: {title}",
                   "We’ll email you once we locate your book.")
        with flask_app.app_context():
            RequestLog.query.get(req_id).status = "missing"
            db.session.commit()
        return

    # 4) download
    ext = file_msg.file.ext or (file_format or "pdf")
    temp = Path("temp"); temp.mkdir(exist_ok=True)
    local = temp / f"{req_id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local))

    # 5) upload
    clean = sanitize_filename(title, author, ext)
    link  = upload_and_share(local, clean, config.GOOGLE_DRIVE_FOLDER_ID)

    # 6) email client
    send_email(email,
               f"Your eBook is ready: {title}",
               f"Hello,\n\nHere is your book:\n{link}\n\nEnjoy!")

    # 7) mark sent & cleanup
    with flask_app.app_context():
        RequestLog.query.get(req_id).status = "sent"
        db.session.commit()
    try: local.unlink(missing_ok=True)
    except Exception: pass
