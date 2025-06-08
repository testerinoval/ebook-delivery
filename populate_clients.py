# populate_clients.py
from app import app, db
from models import Client
import config

with app.app_context():
    for e in config.WHITELIST:
        if not Client.query.get(e):
            db.session.add(Client(email=e))
    db.session.commit()
    print("✅ Whitelist entries added to the Client table!")
