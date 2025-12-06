from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import feedparser
import time
from datetime import datetime
import re
import html
import requests
import ssl
import urllib.request
from bs4 import BeautifulSoup
from gtts import gTTS
import os

ssl._create_default_https_context = ssl._create_unverified_context

db = SQLAlchemy()

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


def strip_html(text):
    """Remove HTML tags and convert HTML entities to plain text."""
    if not text:
        return None
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\\(["\'])', lambda m: m.group(1), text)
    return text


def scrape_article_content(url):
    """Scrape article content from a URL and extract the main text."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            script.decompose()

        # Try to find the main article content
        # Common article container tags and classes
        article_content = None

        # Try different selectors in order of specificity
        selectors = [
            'article',
            '[class*="article-content"]',
            '[class*="article-body"]',
            '[class*="post-content"]',
            '[class*="entry-content"]',
            'main',
            '[role="main"]',
        ]

        for selector in selectors:
            article_content = soup.select_one(selector)
            if article_content:
                break

        # If no specific article container found, try to get all paragraphs
        if not article_content:
            article_content = soup.find('body')

        if article_content:
            # Extract text from paragraphs
            paragraphs = article_content.find_all('p')
            text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

            text = re.sub(r'\s+', ' ', text).strip()

            return text if text else None

        return None
    except Exception as e:
        print(f"Error scraping article from {url}: {e}")
        return None


def generate_article_tts(article_id, text):
    """Generate text-to-speech audio for an article and save it to the audios folder."""
    if not text or not text.strip():
        print(f"No text available for article {article_id}")
        return None

    try:
        # Create audios directory if it doesn't exist
        os.makedirs('audios', exist_ok=True)

        # Generate filename
        filename = f"{article_id}.mp3"
        filepath = os.path.join('audios', filename)

        # Generate TTS
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(filepath)

        print(f"Generated TTS for article {article_id}: {filepath}")
        return filename
    except Exception as e:
        print(f"Error generating TTS for article {article_id}: {e}")
        return None


# Association table for many-to-many relationship between users and saved articles
saved_articles = db.Table('saved_articles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('article_id', db.Integer, db.ForeignKey('article.id'), primary_key=True)
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    saved_articles = db.relationship('Article', secondary=saved_articles, backref='saved_by_users', lazy='dynamic')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }


class Outlet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    slug = db.Column(db.String(128), nullable=False, unique=True)
    rss_feed = db.Column(db.String(512))
    url = db.Column(db.String(512))
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(512))
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
        }

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(512), nullable=False)
    link = db.Column(db.String(512), nullable=False, unique=True)
    text = db.Column(db.Text)
    author = db.Column(db.String(256))
    pub_date = db.Column(db.DateTime)
    image_url = db.Column(db.String(512))
    audio_file = db.Column(db.String(512))
    outlet_id = db.Column(db.Integer, db.ForeignKey('outlet.id'), nullable=False)

    def to_dict(self, user_id=None):
        """
        Convert article to dictionary.
        If user_id is provided, includes whether the user has saved this article.
        """
        result = {
            "id": self.id,
            "title": self.title,
            "link": self.link,
            "text": self.text,
            "author": self.author,
            "pub_date": self.pub_date.isoformat() if self.pub_date else None,
            "image_url": self.image_url,
            "audio_file": self.audio_file,
            "outlet": {
                "id": self.outlet.id,
                "name": self.outlet.name,
            }
        }

        if user_id is not None:
            # Check if this article is saved by the user
            user = User.query.get(user_id)
            result["saved"] = user and self in user.saved_articles.all()

        return result

def initialize_outlets():
    """Create the news outlets if they don't exist."""
    outlets_data = [
        {
            "name": "The Cornell Daily Sun",
            "slug": "cornell-sun",
            "rss_feed": "https://www.cornellsun.com/plugin/feeds/all.xml",
            "url": "https://www.cornellsun.com",
            "description": "Cornell University's independent student newspaper",
        },
        {
            "name": "14850",
            "slug": "14850",
            "rss_feed": "https://14850.com/feed",
            "url": "https://14850.com",
            "description": "Ithaca's community news magazine",
        },
        {
            "name": "The Ithaca Voice",
            "slug": "ithaca-voice",
            "rss_feed": "https://ithacavoice.org/feed/",
            "url": "https://ithacavoice.org",
            "description": "Independent local news for Ithaca and Tompkins County",
        },
        {
            "name": "Cornell Chronicle Architecture & Design",
            "slug": "cornell-chronicle-architecture-and-design",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14242/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Architecture & Design"
        },
        {
            "name": "Cornell Chronicle Arts & Humanities",
            "slug": "cornell-chronicle-arts-and-humanities",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14243/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Arts & Humanities"
        },
        {
            "name": "Cornell Chronicle Business, Economics & Entrepreneurship",
            "slug": "cornell-chronicle-business-economics-and-entrepreneurship",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14244/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Business, Economics & Entrepreneurship"
        },
        {
            "name": "Cornell Chronicle Computing & Information Sciences",
            "slug": "cornell-chronicle-computing-and-information-sciences",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14256/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Computing & Information Sciences"
        },
        {
            "name": "Cornell Chronicle Energy, Environment & Sustainability",
            "slug": "cornell-chronicle-energy-environment-and-sustainability",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/15621/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Energy, Environment & Sustainability"
        },
        {
            "name": "Cornell Chronicle Food & Agriculture",
            "slug": "cornell-chronicle-food-and-agriculture",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14247/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Food & Agriculture"
        },
        {
            "name": "Cornell Chronicle Global Reach",
            "slug": "cornell-chronicle-global-reach",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14249/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Global Reach"
        },
        {
            "name": "Cornell Chronicle Health, Nutrition & Medicine",
            "slug": "cornell-chronicle-health-nutrition-and-medicine",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14248/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Health, Nutrition & Medicine"
        },
        {
            "name": "Cornell Chronicle Law, Government & Public Policy",
            "slug": "cornell-chronicle-law-government-and-public-policy",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14250/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Law, Government & Public Policy"
        },
        {
            "name": "Cornell Chronicle Life Sciences & Veterinary Medicine",
            "slug": "cornell-chronicle-life-sciences-and-veterinary-medicine",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/15056/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Life Sciences & Veterinary Medicine"
        },
        {
            "name": "Cornell Chronicle Physical Sciences & Engineering",
            "slug": "cornell-chronicle-physical-sciences-and-engineering",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14252/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Physical Sciences & Engineering"
        },
        {
            "name": "Cornell Chronicle Social & Behavioral Sciences",
            "slug": "cornell-chronicle-social-and-behavioral-sciences",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14253/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Social & Behavioral Sciences"
        },
        {
            "name": "Cornell Chronicle Inclusion and Belonging",
            "slug": "cornell-chronicle-inclusion-and-belonging",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/89/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Inclusion and Belonging"
        },
        {
            "name": "Cornell Chronicle News & Events",
            "slug": "cornell-chronicle-news-and-events",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/81/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: News & Events"
        },
        {
            "name": "Cornell Chronicle New York City",
            "slug": "cornell-chronicle-new-york-city",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/83/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: New York City"
        },
        {
            "name": "Cornell Chronicle Public Engagement",
            "slug": "cornell-chronicle-public-engagement",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/82/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Public Engagement"
        },
        {
            "name": "Cornell Chronicle Agriculture and Life Sciences",
            "slug": "cornell-chronicle-agriculture-and-life-sciences",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/21/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Agriculture and Life Sciences"
        },
        {
            "name": "Cornell Chronicle Architecture, Art and Planning",
            "slug": "cornell-chronicle-architecture-art-and-planning",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/22/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Architecture, Art and Planning"
        },
        {
            "name": "Cornell Chronicle Arts and Sciences",
            "slug": "cornell-chronicle-arts-and-sciences",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/23/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Arts and Sciences"
        },
        {
            "name": "Cornell Chronicle Computing & Information Sciences College",
            "slug": "cornell-chronicle-computing-and-information-sciences-college",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14245/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Computing & Information Sciences"
        },
        {
            "name": "Cornell Chronicle Continuing Education and Summer Sessions",
            "slug": "cornell-chronicle-continuing-education-and-summer-sessions",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/34/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Continuing Education and Summer Sessions"
        },
        {
            "name": "Cornell Chronicle Jeb E. Brooks School of Public Policy",
            "slug": "cornell-chronicle-jeb-e-brooks-school-of-public-policy",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/23613/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Cornell Jeb E. Brooks School of Public Policy"
        },
        {
            "name": "Cornell Chronicle SC Johnson College of Business",
            "slug": "cornell-chronicle-sc-johnson-college-of-business",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14254/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Cornell SC Johnson College of Business"
        },
        {
            "name": "Cornell Chronicle University Library",
            "slug": "cornell-chronicle-university-library",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14255/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Cornell University Library"
        },
        {
            "name": "Cornell Chronicle Cornell Tech",
            "slug": "cornell-chronicle-cornell-tech",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/33/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Cornell Tech"
        },
        {
            "name": "Cornell Chronicle Engineering",
            "slug": "cornell-chronicle-engineering",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/26/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Engineering"
        },
        {
            "name": "Cornell Chronicle Graduate School",
            "slug": "cornell-chronicle-graduate-school",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/27/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Graduate School"
        },
        {
            "name": "Cornell Chronicle School of Hotel Administration",
            "slug": "cornell-chronicle-school-of-hotel-administration",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14259/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: School of Hotel Administration"
        },
        {
            "name": "Cornell Chronicle Human Ecology",
            "slug": "cornell-chronicle-human-ecology",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/29/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Human Ecology"
        },
        {
            "name": "Cornell Chronicle Industrial and Labor Relations",
            "slug": "cornell-chronicle-industrial-and-labor-relations",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/30/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Industrial and Labor Relations"
        },
        {
            "name": "Cornell Chronicle Johnson Graduate School of Management",
            "slug": "cornell-chronicle-johnson-graduate-school-of-management",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14257/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Johnson Graduate School of Management"
        },
        {
            "name": "Cornell Chronicle Law School",
            "slug": "cornell-chronicle-law-school",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/32/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Law School"
        },
        {
            "name": "Cornell Chronicle Veterinary Medicine",
            "slug": "cornell-chronicle-veterinary-medicine",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/35/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Veterinary Medicine"
        },
        {
            "name": "Cornell Chronicle Weill Cornell Medicine-NY",
            "slug": "cornell-chronicle-weill-cornell-medicine-ny",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/14/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Weill Cornell Medicine-NY"
        },
        {
            "name": "Cornell Chronicle Ithaca",
            "slug": "cornell-chronicle-ithaca",
            "rss_feed": "https://news.cornell.edu/taxonomy/term/63/feed",
            "url": "https://news.cornell.edu",
            "description": "Cornell University's Official News Source: Ithaca"
        }
    ]

    for outlet_data in outlets_data:
        existing = Outlet.query.filter_by(slug=outlet_data["slug"]).first()
        if not existing:
            outlet = Outlet(**outlet_data)
            db.session.add(outlet)
            print(f"Created outlet: {outlet_data['name']}")
        else:
            print(f"Outlet already exists: {outlet_data['name']}")

    db.session.commit()


def fetch_and_store_feeds():
    """Fetch all outlets' feeds and store new articles."""
    outlets = Outlet.query.filter(Outlet.rss_feed != None).all()

    for outlet in outlets:
        try:
            feed = feedparser.parse(outlet.rss_feed)

            for entry in feed.entries:
                link = getattr(entry, "link", None)
                if not link:
                    continue

                # Check if article already exists
                if Article.query.filter_by(link=link).first():
                    continue

                # # Get text from RSS feed first
                # text = strip_html(getattr(entry, "text", None) or getattr(entry, "summary", None))

                # # If text is missing or empty, scrape the article content
                # if not text:
                #     print(f"No text in feed for {link}, scraping content...")
                text = scrape_article_content(link)

                article = Article(
                    title=getattr(entry, "title", None) or "",
                    link=link,
                    text=text,
                    author=getattr(entry, "author", None),
                    pub_date=parse_pub_date(entry),
                    image_url=get_image_url(entry),
                    outlet_id=outlet.id,
                )

                db.session.add(article)

            db.session.commit()
            print(f"Feed updated for outlet: {outlet.name}")
        except Exception as e:
            print(f"Error fetching feed for outlet {outlet.name} ({outlet.rss_feed}): {e}")
