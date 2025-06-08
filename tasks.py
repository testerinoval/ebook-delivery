# tasks.py
"""
Background job executed by the RQ worker.

Steps
1.  Log request as “processing”.
2.  Ask Telegram bot for the book.
3.  Download   → rename → upload to Google Drive.
4.  Email client (or admin if missing).
5.  Update DB status.
"""

import os
import time
from pathlib import Path

from models import db, RequestLog
import config

from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email


# ──────────────────────────────────────────
def sanitize_filename(title: str, author: str, ext: str) -> str:
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_YourName.{ext}"


def process_book_request(email, title, author, file_format=None):
    """
    The function RQ enqueues; runs inside the worker process.
    A *lazy import* of `app` is done inside the function to avoid
    circular-import problems when the web app imports tasks.py.
    """
    # Lazy import to obtain the Flask app *only when the job runs*
    from app import app as flask_app

    # ── 1 ▸ mark “processing” ───────────────────────────────────────────
    with flask_app.app_context():
        req = RequestLog(
            email=email,
            book_title=title,
            author_name=author,
            status="processing",
        )
        db.session.add(req)
        db.session.commit()

    # ── 2 ▸ ask Telegram bot ────────────────────────────────────────────
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
            if m.file:
                file_msg = m
                break
        if file_msg:
            break
        time.sleep(2)

    # ── 3 ▸ not found → notify & exit ───────────────────────────────────
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

    # ── 4 ▸ download the file ───────────────────────────────────────────
    ext = file_msg.file.ext or (file_format or "pdf")
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)
    local_path = temp_dir / f"{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local_path))

    # ── 5 ▸ rename, upload, share ───────────────────────────────────────
    clean_name  = sanitize_filename(title, author, ext)
    public_link = upload_and_share(local_path, clean_name, config.GOOGLE_DRIVE_FOLDER_ID)

    # ── 6 ▸ email the client ────────────────────────────────────────────
    send_email(
        email,
        f"Your eBook is ready: {title}",
        f"Hello,\n\nHere is your book:\n{public_link}\n\nEnjoy!",
    )

    # ── 7 ▸ mark “sent” & cleanup ───────────────────────────────────────
    with flask_app.app_context():
        req.status = "sent"
        db.session.commit()

    try:
        local_path.unlink(missing_ok=True)
    except Exception:
        pass
