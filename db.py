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

# Helper functions
def parse_pub_date(entry):
    try:
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
    except Exception:
        pass
    return None


def get_image_url(entry):
    try:
        if hasattr(entry, "media_content") and entry.media_content:
            return entry.media_content[0].get("url")
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            return entry.media_thumbnail[0].get("url")
        if "enclosures" in entry and entry.enclosures:
            return entry.enclosures[0].get("href")
    except Exception:
        pass
    return None


# Database Models

class Outlet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    slug = db.Column(db.String(128), nullable=False, unique=True)

    rss_feed = db.Column(db.String(512))
    url = db.Column(db.String(512))
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    articles = db.relationship('Article', backref='outlet', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "rss_feed": self.rss_feed,
            "url": self.url,
            "description": self.description,
            "logo_url": self.logo_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(512), unique=True, nullable=False)

    title = db.Column(db.String(512), nullable=False)
    link = db.Column(db.String(512), nullable=False)
    description = db.Column(db.Text)
    author = db.Column(db.String(256))
    categories = db.Column(db.String(512))
    pub_date = db.Column(db.DateTime)
    image_url = db.Column(db.String(512))
    outlet_id = db.Column(db.Integer, db.ForeignKey('outlet.id'), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "guid": self.guid,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "author": self.author,
            "categories": self.categories.split(",") if self.categories else [],
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "image_url": self.image_url,
            "outlet": {
                "id": self.outlet.id,
                "name": self.outlet.name,
                "slug": self.outlet.slug,
            } if getattr(self, "outlet", None) else None,
        }

def fetch_and_store_feeds():
    """Fetch all outlets' feeds and store new articles. Falls back to DEFAULT_FEED if no outlets exist."""
    with app.app_context():
        outlets = Outlet.query.filter(Outlet.rss_feed != None).all()

        for outlet in outlets:
            try:
                feed = feedparser.parse(outlet.rss_feed)

                for entry in feed.entries:
                    guid = getattr(entry, "id", None) or getattr(entry, "guid", None) or getattr(entry, "link", None)
                    if not guid:
                        continue

                    if Article.query.filter_by(guid=guid).first():
                        continue

                    categories = None
                    try:
                        categories = ",".join([t.term for t in entry.tags]) if getattr(entry, "tags", None) else None
                    except Exception:
                        categories = None

                    article = Article(
                        guid=guid,
                        title=getattr(entry, "title", None) or "",
                        link=getattr(entry, "link", None) or "",
                        description=getattr(entry, "description", None) or getattr(entry, "summary", None),
                        author=getattr(entry, "author", None),
                        categories=categories,
                        pub_date=parse_pub_date(entry),
                        image_url=get_image_url(entry),
                        outlet_id=outlet.id,
                    )

                    db.session.add(article)

                db.session.commit()
                print("Feed updated for outlet:", outlet.name)
            except Exception as e:
                print(f"Error fetching feed for outlet {outlet.name} ({outlet.rss_feed}):", e)


@app.route("/articles")
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
