from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
import time
from datetime import datetime
import atexit

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///cornell_sun.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    saved_articles = db.relationship('Article', backref='user', lazy='dynamic')

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(512), nullable=False)
    link = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text)
    author = db.Column(db.String(256))
    pub_date = db.Column(db.DateTime)
    image_url = db.Column(db.String(512))
    outlet_id = db.Column(db.Integer, db.ForeignKey('outlet.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "author": self.author,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "image_url": self.image_url,
            "outlet": {
                "id": self.outlet.id,
                "name": self.outlet.name,
            }
        }

def fetch_and_store_feeds():
    


@app.route("/articles/")
def list_articles():
    """
    Temporary endpoint. List all articles in the database.
    """
    articles = Article.query.order_by(Article.pub_date.desc()).all()
    return jsonify([a.to_dict() for a in articles])


def start_scheduler():
    """
    Start the background scheduler to fetch and store the RSS feed periodically.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_store_feeds, "interval", minutes=15)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        fetch_and_store_feeds()
        start_scheduler()
    app.run()
