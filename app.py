from flask import Flask, jsonify, request, session, send_from_directory
from flask_session import Session
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import os
from db import db, User, Article, Outlet, initialize_outlets, fetch_and_store_feeds, generate_article_tts

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///articles.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "b27008c9130ade5a76e9d4ff7f7dffad4ff1605ce103da2dd115d9402ae58e20"
app.config["SESSION_TYPE"] = "filesystem"

# Initialize extensions
db.init_app(app)
Session(app)

@app.route("/")
def index():
    """Welcome endpoint."""
    return "Scope Backend: https://github.com/bchucs/scope-backend", 200 


# Article endpoints
@app.route("/articles")
def list_articles():
    """
    List all articles in the database.
    If user is logged in, includes saved status for each article.
    """
    user_id = session.get('user_id')
    articles = Article.query.order_by(Article.pub_date.desc()).all()
    return jsonify([a.to_dict(user_id=user_id) for a in articles])

@app.route("/articles/<int:article_id>")
def get_article(article_id):
    """Get a specific article by ID."""
    user_id = session.get('user_id')
    article = Article.query.get(article_id)

    if not article:
        return jsonify({"error": "Article not found"}), 404

    return jsonify(article.to_dict(user_id=user_id)), 200

@app.route("/articles/top/<int:top_k>")
def get_top_articles(top_k):
    """Get the top K most recent articles."""
    user_id = session.get('user_id')
    articles = Article.query.order_by(Article.pub_date.desc()).limit(top_k).all()
    return jsonify([a.to_dict(user_id=user_id) for a in articles]), 200

@app.route("/outlets")
def list_outlets():
    """List all parent news outlets (outlets without a parent)."""
    outlets = Outlet.query.filter_by(parent_outlet_id=None).all()
    return jsonify([o.to_dict() for o in outlets]), 200

@app.route("/articles/outlet/<int:outlet_id>")
def get_articles_by_outlet(outlet_id):
    """Get articles from a specific outlet and all its child outlets."""
    user_id = session.get('user_id')
    outlet = Outlet.query.get(outlet_id)

    if not outlet:
        return jsonify({"error": "Outlet not found"}), 404

    # Get outlet IDs: the outlet itself and all its children
    outlet_ids = [outlet.id]
    if outlet.children:
        outlet_ids.extend([child.id for child in outlet.children])

    articles = Article.query.filter(Article.outlet_id.in_(outlet_ids)).order_by(Article.pub_date.desc()).all()
    return jsonify([a.to_dict(user_id=user_id) for a in articles]), 200

@app.route("/articles/outlet/<int:outlet_id>/top/<int:top_k>")
def get_top_articles_by_outlet(outlet_id, top_k):
    """Get the top K most recent articles from a specific outlet and all its child outlets."""
    user_id = session.get('user_id')
    outlet = Outlet.query.get(outlet_id)

    if not outlet:
        return jsonify({"error": "Outlet not found"}), 404

    # Get outlet IDs: the outlet itself and all its children
    outlet_ids = [outlet.id]
    if outlet.children:
        outlet_ids.extend([child.id for child in outlet.children])

    articles = Article.query.filter(Article.outlet_id.in_(outlet_ids)).order_by(Article.pub_date.desc()).limit(top_k).all()
    return jsonify([a.to_dict(user_id=user_id) for a in articles]), 200


@app.route("/articles/saved")
def get_saved_articles():
    """Get all saved articles for the current user."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    saved_articles = user.saved_articles.order_by(Article.pub_date.desc()).all()
    return jsonify([a.to_dict(user_id=user_id) for a in saved_articles]), 200


@app.route("/articles/<int:article_id>/save", methods=["POST"])
def save_article(article_id):
    """Save an article for the current user."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    article = Article.query.get(article_id)

    if not article:
        return jsonify({"error": "Article not found"}), 404

    if article in user.saved_articles.all():
        return jsonify({"message": "Article already saved"}), 200

    user.saved_articles.append(article)
    db.session.commit()

    return jsonify({"message": "Article saved successfully"}), 200


@app.route("/articles/<int:article_id>/unsave", methods=["DELETE"])
def unsave_article(article_id):
    """Unsave an article for the current user."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    article = Article.query.get(article_id)

    if not article:
        return jsonify({"error": "Article not found"}), 404

    if article not in user.saved_articles.all():
        return jsonify({"message": "Article not saved"}), 200

    user.saved_articles.remove(article)
    db.session.commit()

    return jsonify({"message": "Article unsaved successfully"}), 200


@app.route("/articles/<int:article_id>/generate-audio", methods=["POST"])
def generate_audio(article_id):
    """Generate text-to-speech audio for an article."""
    article = Article.query.get(article_id)

    if not article:
        return jsonify({"error": "Article not found"}), 404

    if not article.text:
        return jsonify({"error": "Article has no text content"}), 400

    # Check if audio already exists
    if article.audio_file and os.path.exists(os.path.join('audios', article.audio_file)):
        return jsonify({"message": "Audio already exists", "audio_file": article.audio_file}), 200

    # Generate TTS
    filename = generate_article_tts(article.id, article.text)

    if not filename:
        return jsonify({"error": "Failed to generate audio"}), 500

    # Update article with audio file path
    article.audio_file = filename
    db.session.commit()

    return jsonify({"message": "Audio generated successfully", "audio_file": filename}), 201


@app.route("/audios/<path:filename>")
def serve_audio(filename):
    """Serve audio files from the audios directory."""
    return send_from_directory('audios', filename)


# Authentication endpoints
@app.route("/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already exists"}), 400


    user = User(username=data['username'], email=data['email'])
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()

    # Log the user in
    session['user_id'] = user.id

    return jsonify({"message": "User registered successfully", "user": user.to_dict()}), 201


@app.route("/auth/login", methods=["POST"])
def login():
    """Log in an existing user."""
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid username or password"}), 401

    session['user_id'] = user.id

    return jsonify({"message": "Logged in successfully", "user": user.to_dict()}), 200


@app.route("/auth/logout", methods=["POST"])
def logout():
    """Log out the current user."""
    session.pop('user_id', None)
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/auth/me")
def get_current_user():
    """Get the currently logged in user."""
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)

    if not user:
        session.pop('user_id', None)
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": user.to_dict()}), 200


def start_scheduler():
    """
    Start the background scheduler to fetch and store the RSS feed periodically.
    """
    scheduler = BackgroundScheduler()

    def scheduled_job():
        with app.app_context():
            fetch_and_store_feeds()

    scheduler.add_job(scheduled_job, "interval", minutes=15)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        initialize_outlets()
        fetch_and_store_feeds()
        start_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=False)
