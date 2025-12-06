# scope-backend

colin park and boris chu

## Docker Hub: https://hub.docker.com/r/bchucs/scope-backend

## Overview
A Flask-based backend service that aggregates news articles from Cornell and Ithaca news outlets via RSS feeds and web scraping. Features include user authentication, article saving, and text-to-speech generation for articles.

## News Sources

The application aggregates news from:
- The Cornell Daily Sun
- 14850 Magazine
- The Ithaca Voice
- Cornell Chronicle (40+ different categories and colleges)

## Features
- Automated RSS feed aggregation from 40+ Cornell and local news sources
- Web scraping for full article content
- User authentication with session management
- Save/unsave articles functionality
- Text-to-speech audio generation for articles
- Background scheduler for automatic feed updates every 15 minutes

## Technical Implementation

### Technology Stack & Third-Party Libraries

**Backend Framework:**
- Flask 3.1.2 - Python web framework
- Flask-SQLAlchemy 3.1.1 - ORM for database interactions
- Flask-Session 0.8.0 - Server-side session management with filesystem storage

**News Aggregation:**
- feedparser 6.0.11 - RSS/Atom feed parsing
- BeautifulSoup4 4.12.3 - HTML parsing and web scraping

**Audio Generation:**
- gTTS 2.5.0 - Google Text-to-Speech library for converting article text to MP3 audio files

**Background Processing:**
- APScheduler 3.10.4 - Background scheduler for periodic RSS feed updates (runs every 15 minutes)

**Security:**
- Werkzeug 3.1.3 - Password hashing using `generate_password_hash` and `check_password_hash`

**Database:**
- SQLite - File-based relational database (`articles.db`)
- SQLAlchemy 2.0.44 - Python SQL toolkit and ORM

### Database Schema

**User Model:**
- `id` (Integer, Primary Key) - Unique user identifier
- `username` (String(80), Unique, Required) - User's username
- `email` (String(120), Unique, Required) - User's email address
- `password_hash` (String(256), Required) - Bcrypt-hashed password
- `saved_articles` (Relationship) - Many-to-many relationship with Article model

**Article Model:**
- `id` (Integer, Primary Key) - Unique article identifier
- `title` (String(512), Required) - Article headline
- `link` (String(512), Unique, Required) - Original article URL
- `text` (Text) - Full article content (scraped from source)
- `author` (String(256)) - Article author name
- `pub_date` (DateTime) - Publication date and time
- `image_url` (String(512)) - Featured image URL
- `audio_file` (String(512)) - Generated MP3 filename (e.g., "1.mp3")
- `outlet_id` (Integer, Foreign Key) - Reference to Outlet model

**Outlet Model:**
- `id` (Integer, Primary Key) - Unique outlet identifier
- `name` (String(256), Unique, Required) - News outlet name
- `slug` (String(128), Unique, Required) - URL-friendly identifier
- `rss_feed` (String(512)) - RSS feed URL
- `url` (String(512)) - Outlet website URL
- `description` (Text) - Outlet description
- `logo_url` (String(512)) - Logo image URL

**Association Table:**
- `saved_articles` - Many-to-many join table linking Users and Articles

### Implementation Details

**Authentication:**
- Session-based authentication using Flask-Session with filesystem storage
- Passwords secured with Werkzeug's password hashing (bcrypt-based)
- Session data stored in `flask_session/` directory
- User sessions persist across server restarts

**Web Scraping Strategy:**
- Primary content extraction from RSS feeds using feedparser
- Full article text obtained via web scraping with BeautifulSoup4
- Removes navigation, headers, footers, scripts, and style elements before extraction
- User-Agent spoofing to avoid bot detection

**Text-to-Speech:**
- Audio files generated on-demand via POST `/articles/:id/generate-audio`
- Uses Google's gTTS API (no API key required)
- MP3 files stored in `audios/` directory
- Filenames based on article ID (e.g. `1.mp3`, `2.mp3`)
- Audio files served statically via `/audios/:filename` route

**Background Scheduler:**
- APScheduler runs `fetch_and_store_feeds()` every 15 minutes
- Automatically fetches new articles from all 40+ RSS feeds
- Deduplicates articles by checking if `link` already exists in database
- Gracefully handles feed parsing errors with try/except blocks

## API Specification

### Base URL
`http://localhost:5000` (development)

---

## Article Endpoints

### GET /articles
List all articles in the database, ordered by publication date (newest first).

**Authentication:** Optional (if logged in, includes saved status)

**Response:**
```json
[
  {
    "id": 1,
    "title": "Article Title",
    "link": "https://example.com/article",
    "text": "Full article text content...",
    "author": "Author Name",
    "pub_date": "2025-12-05T10:30:00",
    "image_url": "https://example.com/image.jpg",
    "audio_file": "1.mp3",
    "outlet": {
      "id": 1,
      "name": "The Cornell Daily Sun"
    },
    "saved": false
  }
]
```

---

### GET /articles/:article_id
Get a specific article by ID.

**Authentication:** Optional (if logged in, includes saved status)

**Response:** `200 OK`
```json
{
  "id": 1,
  "title": "Article Title",
  "link": "https://example.com/article",
  "text": "Full article text content...",
  "author": "Author Name",
  "pub_date": "2025-12-05T10:30:00",
  "image_url": "https://example.com/image.jpg",
  "audio_file": "1.mp3",
  "outlet": {
    "id": 1,
    "name": "The Cornell Daily Sun"
  },
  "saved": true
}
```

**Error:** `404 Not Found`
```json
{
  "error": "Article not found"
}
```

---

### GET /articles/top/:top_k
Get the top K most recent articles.

**Parameters:**
- `top_k` (path): Number of articles to retrieve

**Authentication:** Optional (if logged in, includes saved status)

**Response:** `200 OK`
```json
[
  {
    "id": 5,
    "title": "Latest Article",
    "link": "https://example.com/latest",
    "text": "Article content...",
    "author": "Author Name",
    "pub_date": "2025-12-05T15:00:00",
    "image_url": "https://example.com/image.jpg",
    "audio_file": null,
    "outlet": {
      "id": 2,
      "name": "14850"
    },
    "saved": false
  }
]
```

---

### GET /articles/saved
Get all saved articles for the currently authenticated user.

**Authentication:** Required

**Response:** `200 OK`
```json
[
  {
    "id": 3,
    "title": "Saved Article",
    "link": "https://example.com/saved",
    "text": "Article content...",
    "author": "Author Name",
    "pub_date": "2025-12-04T12:00:00",
    "image_url": "https://example.com/image.jpg",
    "audio_file": "3.mp3",
    "outlet": {
      "id": 1,
      "name": "The Cornell Daily Sun"
    },
    "saved": true
  }
]
```

**Error:** `401 Unauthorized`
```json
{
  "error": "Not authenticated"
}
```

---

### POST /articles/:article_id/save
Save an article for the current user.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "message": "Article saved successfully"
}
```

**If already saved:** `200 OK`
```json
{
  "message": "Article already saved"
}
```

**Errors:**
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Article not found

---

### POST /articles/:article_id/unsave
Remove an article from the user's saved articles.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "message": "Article unsaved successfully"
}
```

**If not saved:** `200 OK`
```json
{
  "message": "Article not saved"
}
```

**Errors:**
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Article not found

---

### POST /articles/:article_id/generate-audio
Generate text-to-speech audio for an article.

**Authentication:** Not required

**Response:** `201 Created`
```json
{
  "message": "Audio generated successfully",
  "audio_file": "1.mp3"
}
```

**If already exists:** `200 OK`
```json
{
  "message": "Audio already exists",
  "audio_file": "1.mp3"
}
```

**Errors:**
- `404 Not Found`: Article not found
- `400 Bad Request`: Article has no text content
- `500 Internal Server Error`: Failed to generate audio

---

### GET /audios/:filename
Serve audio files from the audios directory.

**Parameters:**
- `filename` (path): Name of the audio file (e.g., "1.mp3")

**Response:** Audio file stream

---

## Authentication Endpoints

### POST /auth/register
Register a new user account.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:** `201 Created`
```json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `400 Bad Request`: Missing required fields, username already exists, or email already exists

---

### POST /auth/login
Log in an existing user.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "message": "Logged in successfully",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `400 Bad Request`: Missing username or password
- `401 Unauthorized`: Invalid username or password

---

### POST /auth/logout
Log out the current user.

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

---

### GET /auth/me
Get the currently authenticated user's information.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**Errors:**
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: User not found


---

## Installation & Deployment

### Local Development (Python)

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The server will start on `http://localhost:5000` and will:
- Initialize the database
- Create news outlet entries
- Fetch initial articles from RSS feeds
- Start a background scheduler to update feeds every 15 minutes
