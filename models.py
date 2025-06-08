from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Client(db.Model):
    email = db.Column(db.String, primary_key=True)

class RequestLog(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    email       = db.Column(db.String)
    book_title  = db.Column(db.String)
    author_name = db.Column(db.String)
    status      = db.Column(db.String)   # pending, processing, sent, missing
