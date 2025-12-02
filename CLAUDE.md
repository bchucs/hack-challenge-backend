# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based RSS feed aggregator backend for news outlets. The application fetches RSS feeds from various outlets, stores articles in a SQLite database, and provides API endpoints to retrieve articles.

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Note: apscheduler is imported but not in requirements.txt - add it if needed:
pip install apscheduler feedparser
```

### Running the Application
```bash
# Run the Flask application (creates database, fetches feeds, starts scheduler)
python db.py
```

The application will:
1. Create the SQLite database (`cornell_sun.db`) if it doesn't exist
2. Initialize all database tables
3. Fetch initial RSS feeds
4. Start a background scheduler that fetches feeds every 15 minutes
5. Start the Flask development server

### Database Operations
```bash
# The database is automatically created on first run
# To reset the database, delete the file:
rm cornell_sun.db

# Then run the application again to recreate it
python db.py
```

## Architecture

### Application Structure
- **Single-file application**: All code is in `db.py` containing models, routes, and background jobs
- **Database**: SQLite with Flask-SQLAlchemy ORM
- **Background processing**: APScheduler for periodic RSS feed fetching

### Database Models

**Outlet**
- Represents a news outlet/publication
- Fields: `id`, `name`, `slug`, `rss_feed`, `url`, `description`, `logo_url`
- Has one-to-many relationship with Articles

**Article**
- Represents individual news articles from RSS feeds
- Fields: `id`, `guid` (unique identifier from RSS), `title`, `link`, `description`, `author`, `pub_date`, `outlet_id`
- Foreign key relationship to Outlet
- Note: Model references `image_url` field in `fetch_and_store_feeds()` (line 116) but the field is not defined in the Article model schema

### RSS Feed Processing

The `fetch_and_store_feeds()` function:
- Runs on application startup and every 15 minutes via scheduler
- Queries all outlets with non-null `rss_feed` URLs
- Uses `feedparser` to parse RSS/Atom feeds
- Extracts article data with fallback logic for missing fields
- Uses `guid`, `id`, or `link` as unique identifier to prevent duplicates
- Helper functions `parse_pub_date()` and `get_image_url()` handle various RSS feed formats

### API Endpoints

**GET /articles**
- Returns all articles ordered by publication date (descending)
- Includes nested outlet information (id, name, slug)
- Marked as temporary endpoint in code comments

## Important Notes

### Known Issues
- `image_url` field is set in `fetch_and_store_feeds()` (line 116) but not defined in the Article model
- `apscheduler` and `feedparser` are imported but not listed in `requirements.txt`

### Development Considerations
- The application uses Flask development server (`app.run()`) - not suitable for production
- No authentication or rate limiting on API endpoints
- Background scheduler runs in-process - will restart on every application restart
- SQLite is used - consider migration path for production deployment
