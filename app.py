from flask import Flask, render_template, request, redirect, url_for, flash
from recommender import recommend  # Your recommendation logic
import psutil
import os


app = Flask(__name__)
app.secret_key = '3f1e2b9d8c4f7a6e5b3d0c1f9a2e8b7'  # You can use an environment variable here for security

@app.route('/memory')
def memory_usage():
    process = psutil.Process(os.getpid())
    return f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB"

@app.route("/", methods=["GET", "POST"])
def index():
    recs, posters, genres, years, trailers = [], [], [], [], []
    history = request.cookies.get("history")  # Optional history feature
    
    if request.method == "POST":
        movie = request.form.get("movie")
        if not movie:
            flash("Please enter a movie title!", "warning")
        else:
            recs, posters, genres, years, trailers = recommend(movie)
            if not recs:
                flash("Movie not found. Try another title!", "danger")
    
    return render_template(
        "index.html",
        recs=recs,
        posters=posters,
        genres=genres,
        years=years,
        trailers=trailers,
        history=[]  # Implement if needed
    )

@app.route("/feedback", methods=["POST"])
def feedback():
    movie_title = request.form.get("movie_title")
    feedback = request.form.get("feedback")
    # Optional: store feedback
    flash(f"Feedback recorded: {feedback} for {movie_title}", "success")
    return redirect(url_for("index"))

@app.route("/clear")
def clear_history():
    resp = redirect(url_for("index"))
    resp.set_cookie("history", "", expires=0)
    return resp

if __name__ == "__main__":
    app.run(debug=True)
