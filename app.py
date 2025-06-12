from flask import Flask, render_template, request, redirect, url_for, flash
from recommender import recommend  # Your recommendation logic
import psutil
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')  # Prefer environment variable

# Configure persistent cache directory for Render
# Replace the CACHE_DIR code at the top with:
from config import CACHE_DIR

@app.route('/memory')
def memory_usage():
    """Endpoint to check current memory usage"""
    process = psutil.Process(os.getpid())
    return {
        'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
        'cache_dir': CACHE_DIR,
        'cache_exists': os.path.exists(CACHE_DIR)
    }

@app.route("/", methods=["GET", "POST"])
def index():
    recs, posters, genres, years, trailers = [], [], [], [], []
    history = request.cookies.get("history", "[]")  # Default empty JSON array
    
    if request.method == "POST":
        movie = request.form.get("movie", "").strip()
        if not movie:
            flash("Please enter a movie title!", "warning")
        else:
            try:
                recs, posters, genres, years, trailers = recommend(movie)
                if not recs:
                    flash("Movie not found. Try another title!", "danger")
            except Exception as e:
                flash(f"Error generating recommendations: {str(e)}", "danger")
                app.logger.error(f"Recommendation error: {str(e)}")
    
    return render_template(
        "index.html",
        recs=recs,
        posters=posters,
        genres=genres,
        years=years,
        trailers=trailers,
        history=history
    )

@app.route("/feedback", methods=["POST"])
def feedback():
    """Handle user feedback on recommendations"""
    movie_title = request.form.get("movie_title", "Unknown")
    feedback_type = request.form.get("feedback", "none")
    
    # Here you could log feedback to a file in the persistent cache:
    feedback_log = Path(CACHE_DIR) / "feedback.log"
    with open(feedback_log, "a") as f:
        f.write(f"{movie_title},{feedback_type}\n")
    
    flash(f"Thanks for your feedback on '{movie_title}'!", "success")
    return redirect(url_for("index"))

@app.route("/clear")
def clear_history():
    """Clear user history cookie"""
    response = redirect(url_for("index"))
    response.set_cookie("history", "", expires=0)
    flash("History cleared!", "info")
    return response

if __name__ == "__main__":
    # Ensure cache directory exists before starting
    Path(CACHE_DIR).mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))