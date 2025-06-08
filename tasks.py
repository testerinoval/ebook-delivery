# tasks.py
"""
Background job that:
1. logs the request,
2. asks the Telegram bot for the book,
3. uploads it to Google Drive,
4. emails the client,
5. updates the DB.

All DB writes run inside `app.app_context()` so the worker
can use SQLAlchemy without “working outside application context”.
"""

import os
import time
from pathlib import Path

from models import db, RequestLog
import config

from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email

# 🔑 import the Flask app to obtain an application context
from app import app as flask_app


def sanitize_filename(title: str, author: str, ext: str) -> str:
    """Create a short safe filename with your signature."""
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_YourName.{ext}"


def process_book_request(email, title, author, file_format=None):
    """The function RQ executes in the worker."""
    # -- 1 ▸ mark the request as “processing” ------------------------------
    with flask_app.app_context():
        req = RequestLog(
            email=email,
            book_title=title,
            author_name=author,
            status="processing",
        )
        db.session.add(req)
        db.session.commit()

    # -- 2 ▸ ask the Telegram bot for the book -----------------------------
    message = f"{title} - {author}"
    tg.loop.run_until_complete(tg.send_message(config.BOOK_BOT_USERNAME, message))

    file_msg = None
    start = time.time()
    while time.time() - start < 30:  # wait max 30 s
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

    # -- 3 ▸ if not found, notify and exit ---------------------------------
    if not file_msg:
        send_email(
            config.ADMIN_EMAIL,
            f"Missing book: {title}",
            f"{email} requested “{title}” by {author} — not found.",
        )
        send_email(
            email,
            f"We’re still searching: {title}",
            "Hi,\nWe couldn’t find your book automatically; "
            "we’ll email you as soon as we locate it.",
        )
        with flask_app.app_context():
            req.status = "missing"
            db.session.commit()
        return

    # -- 4 ▸ download the file ---------------------------------------------
    ext = file_msg.file.ext or (file_format or "pdf")
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    local_path = temp_dir / f"{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local_path))

    # -- 5 ▸ rename, upload, make public -----------------------------------
    clean_name = sanitize_filename(title, author, ext)
    upload_link = upload_and_share(local_path, clean_name, config.GOOGLE_DRIVE_FOLDER_ID)

    # -- 6 ▸ email the client ----------------------------------------------
    send_email(
        email,
        f"Your eBook is ready: {title}",
        f"Hello,\n\nHere is your book:\n{upload_link}\n\nEnjoy!",
    )

    # -- 7 ▸ mark as sent & cleanup ----------------------------------------
    with flask_app.app_context():
        req.status = "sent"
        db.session.commit()

    try:
        local_path.unlink(missing_ok=True)
    except Exception:
        pass
