# tasks.py  – first English file, any format
import os, time
from pathlib import Path
from models import db, RequestLog
import config

from telegram_client import client as tg
from google_drive import upload_and_share
from email_sender import send_email

TMP_DIR = Path("temp"); TMP_DIR.mkdir(exist_ok=True)

def sanitize(title, author, ext):
    base = f"{title}_{author}".replace(" ", "_")
    safe = "".join(c for c in base if c.isalnum() or c == "_")[:50]
    return f"{safe}_YourName.{ext}"

def _ctx():            # lazy import to avoid circular refs
    from app import app as flask_app
    return flask_app
def _in_app(fn):       # decorator: run inside Flask app-context
    def wrapper(*a, **kw):
        with _ctx().app_context():
            return fn(*a, **kw)
    return wrapper
@_in_app
def _status(req, s):
    req.status = s; db.session.commit()

# ───────────────────────────────────────────────────────────
def process_book_request(email, title, author, *_):
    from app import db               # local to dodge circulars
    with _ctx().app_context():
        req = RequestLog(email=email, book_title=title,
                         author_name=author, status="processing")
        db.session.add(req); db.session.commit()

    # 1 ▸ ask for “english”
    qtxt = f"{title} - {author} english"
    tg.loop.run_until_complete(
        tg.send_message(config.BOOK_BOT_USERNAME, qtxt))

    # 2 ▸ wait ≤60 s for first file
    file_msg = None
    start = time.time()
    while time.time() - start < 60:
        msgs = tg.loop.run_until_complete(
            tg.get_messages(config.BOOK_BOT_USERNAME, limit=8))
        for m in msgs:
            if m.file: file_msg = m; break
        if file_msg: break
        time.sleep(2)

    if not file_msg:                       # still nothing
        send_email(config.ADMIN_EMAIL,
                   f"Missing book: {title}",
                   f"{email} requested “{title}” – bot returned no file.")
        _status(req, "missing"); return

    # 3 ▸ download
    ext   = (file_msg.file.ext or "").lstrip(".") or "bin"
    local = TMP_DIR / f"{req.id}.{ext}"
    tg.loop.run_until_complete(file_msg.download(media=local))

    # 4 ▸ upload
    drive_name = sanitize(title, author, ext)
    link       = upload_and_share(local, drive_name,
                                  config.GOOGLE_DRIVE_FOLDER_ID)

    # 5 ▸ mail user
    send_email(email,
               f"Your eBook is ready: {title}",
               f"Hello,\n\nHere is your book ({ext.upper()}):\n{link}\n\nEnjoy!")

    _status(req, "sent")
    try: local.unlink(missing_ok=True)
    except Exception: pass
