# app.py
from flask import Flask, request, render_template_string
from models import db, Client, RequestLog
import config
from redis import Redis
from rq import Queue
from tasks import process_book_request

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///requests.db'
app.config['SECRET_KEY'] = config.SECRET_KEY

db.init_app(app)
redis_conn = Redis()
q = Queue(connection=redis_conn)

FORM_HTML = '''
<h2>📚 Request an eBook</h2>
{% if message %}<p><strong>{{ message }}</strong></p>{% endif %}
<form method="post">
  Email: <input type="email" name="email" required><br>
  Title: <input type="text" name="title" required><br>
  Author: <input type="text" name="author" required><br>
  Format (pdf/epub): <input type="text" name="format"><br>
  <button type="submit">Submit</button>
</form>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    message = ''
    if request.method == 'POST':
        # Normalize the submitted email to lowercase and trim whitespace
        email = request.form['email'].strip().lower()

        title  = request.form['title']
        author = request.form['author']
        fmt    = request.form.get('format', None)

        if not Client.query.get(email):
            message = (
                "Your email is not whitelisted. "
                f"Please email {config.ADMIN_EMAIL} to request access."
            )
        else:
            log = RequestLog(
                email=email, book_title=title,
                author_name=author, status='pending'
            )
            db.session.add(log)
            db.session.commit()
            q.enqueue(process_book_request, email, title, author, fmt)
            message = 'Request received! Check your email soon.'

    return render_template_string(FORM_HTML, message=message)

if __name__ == '__main__':
    # Initialize database and whitelist before starting
    with app.app_context():
        db.create_all()
        for e in config.WHITELIST:
            if not Client.query.get(e):
                db.session.add(Client(email=e))
        db.session.commit()
    app.run(debug=True)
