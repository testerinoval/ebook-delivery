from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Client(db.Model):
    email = db.Column(db.String(255), primary_key=True)

class RequestLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    email       = db.Column(db.String(255))
    book_title  = db.Column(db.String(255))
    author_name = db.Column(db.String(255))
    status      = db.Column(db.String(64))  # “pending”, “processing”, “sent”, “missing”
