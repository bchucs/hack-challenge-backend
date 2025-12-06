# hack-challenge-backend

colin park and boris chu

## Overview
A Flask-based backend service that aggregates news articles from Cornell and Ithaca news outlets via RSS feeds and web scraping. Features include user authentication, article saving, and text-to-speech generation for articles.

## Features
- Automated RSS feed aggregation from 40+ Cornell and local news sources
- Web scraping for full article content
- User authentication with session management
- Save/unsave articles functionality
- Text-to-speech audio generation for articles
- Background scheduler for automatic feed updates every 15 minutes

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

## Data Models

### User
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com"
}
```

### Article
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
  "saved": false
}
```

### Outlet
```json
{
  "id": 1,
  "name": "The Cornell Daily Sun",
  "slug": "cornell-sun",
  "rss_feed": "https://www.cornellsun.com/plugin/feeds/all.xml",
  "url": "https://www.cornellsun.com",
  "description": "Cornell University's independent student newspaper",
  "logo_url": null
}
```

---

## Installation

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

---

## News Sources

The application aggregates news from:
- The Cornell Daily Sun
- 14850 Magazine
- The Ithaca Voice
- Cornell Chronicle (40+ different categories and colleges)

Articles are fetched via RSS feeds and full content is obtained through web scraping.
