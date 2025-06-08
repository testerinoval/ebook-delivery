# tasks.py
"""
Background job executed by the RQ worker.

Flow:
1) Log request → status = processing
2) Ask Telegram bot for the book
   • If the bot returns a list, send the first /book… command
3) Download the file
4) Upload to Google Drive
5) Email the client
6) Update DB status (sent / missing)
"""

import os
import time
from pathlib import Path

from models import db, RequestLog
import config

from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email

# -- bring in the Flask app for application-context handling --------------
from app import app as flask_app


# ------------------------------------------------------------------------
def sanitize_filename(title: str, author: str, ext: str) -> str:
    """Create a safe, short filename and append your signature."""
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_YourName.{ext}"


# ------------------------------------------------------------------------
def process_book_request(email, title, author, file_format=None):
    # -- 1 ▸ mark request as “processing” ---------------------------------
    with flask_app.app_context():
        req = RequestLog(
            email=email,
            book_title=title,
            author_name=author,
            status="processing",
        )
        db.session.add(req)
        db.session.commit()

    # -- 2 ▸ ask the Telegram bot ----------------------------------------
    query_text = f"{title} - {author}"
    tg.loop.run_until_complete(
        tg.send_message(config.BOOK_BOT_USERNAME, query_text)
    )

    # wait for bot’s first reply (list or file)
    file_msg = None
    start = time.time()
    while time.time() - start < 30:
        msgs = tg.loop.run_until_complete(
            tg.get_messages(config.BOOK_BOT_USERNAME, limit=5)
        )
        for m in msgs:
            if m.file or "/book" in m.raw_text:
                file_msg = m
                break
        if file_msg:
            break
        time.sleep(2)

    # -- 2b ▸ if we got a list, request the first file -------------------
    if file_msg and not file_msg.file:
        first_cmd = None
        for tok in file_msg.raw_text.split():
            if tok.startswith("/book"):
                first_cmd = tok.strip()
                break

        if first_cmd:
            tg.loop.run_until_complete(
                tg.send_message(config.BOOK_BOT_USERNAME, first_cmd)
            )
            # wait for the actual file
            start = time.time()
            while time.time() - start < 30:
                msgs = tg.loop.run_until_complete(
                    tg.get_messages(config.BOOK_BOT_USERNAME, limit=3)
                )
                for m in msgs:
                    if m.file:
                        file_msg = m
                        break
                if file_msg and file_msg.file:
                    break
                time.sleep(2)

    # -- 3 ▸ if still no file, mark missing ------------------------------
    if not (file_msg and file_msg.file):
        send_email(
            config.ADMIN_EMAIL,
            f"Missing book: {title}",
            f"{email} requested “{title}” by {author} — not found automatically.",
        )
        send_email(
            email,
            f"We’re still searching: {title}",
            "Hi,\nWe couldn’t locate your book automatically; "
            "we’ll email you as soon as it’s available.",
        )
        with flask_app.app_context():
            req.status = "missing"
            db.session.commit()
        return

    # -- 4 ▸ download the file -------------------------------------------
    ext = file_msg.file.ext or (file_format or "pdf")
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    local_path = temp_dir / f"{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local_path))

    # -- 5 ▸ rename, upload, share ---------------------------------------
    clean_name = sanitize_filename(title, author, ext)
    drive_link = upload_and_share(
        local_path,
        clean_name,
        config.GOOGLE_DRIVE_FOLDER_ID
    )

    # -- 6 ▸ email the client -------------------------------------------
    send_email(
        email,
        f"Your eBook is ready: {title}",
        f"Hello,\n\nHere is your book:\n{drive_link}\n\nEnjoy!",
    )

    # -- 7 ▸ mark as sent & cleanup --------------------------------------
    with flask_app.app_context():
        req.status = "sent"
        db.session.commit()

    try:
        local_path.unlink(missing_ok=True)
    except Exception:
        pass
