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

### Docker Deployment

#### Build and Run with Docker

```bash
# Build the Docker image
docker build -t hack-challenge-backend .

# Run the container
docker run -p 5000:5000 hack-challenge-backend
```

#### Using Docker Compose

```bash
# Start the application
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the application
docker-compose down
```

The Docker setup includes:
- Persistent volumes for database, audio files, and session data
- Automatic restarts
- Port mapping to 5000

### Cloud Deployment Options

#### Option 1: Render (Recommended for Free Tier)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect the `render.yaml` configuration
6. Click "Create Web Service"

The app will be deployed and accessible at `https://your-app-name.onrender.com`

**Note:** Free tier may spin down after inactivity. First request after inactivity may take 30-60 seconds.

#### Option 2: Railway

1. Push your code to GitHub
2. Go to [Railway](https://railway.app/)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect Docker and deploy

#### Option 3: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Launch app
flyctl launch

# Deploy
flyctl deploy
```

#### Option 4: Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/hack-challenge-backend

# Deploy to Cloud Run
gcloud run deploy hack-challenge-backend \
  --image gcr.io/YOUR_PROJECT_ID/hack-challenge-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Option 5: AWS (EC2 or ECS)

For EC2:
```bash
# SSH into your EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Install Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start

# Clone and run
git clone your-repo-url
cd hack-challenge-backend
sudo docker build -t hack-challenge-backend .
sudo docker run -d -p 80:5000 hack-challenge-backend
```

---

## News Sources

The application aggregates news from:
- The Cornell Daily Sun
- 14850 Magazine
- The Ithaca Voice
- Cornell Chronicle (40+ different categories and colleges)

Articles are fetched via RSS feeds and full content is obtained through web scraping.
