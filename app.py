from flask import Flask, render_template, request, redirect, url_for, flash, session
from recommender import recommend
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")  # Keep this secure

# Initialize feedback_store for feedback handling
feedback_store = {}

@app.route("/", methods=["GET", "POST"])
def home():
    recs, posters, genres, years, trailers = [], [], [], [], []
    if request.method == "POST":
        movie = request.form["movie"]
        recs, posters, genres, years, trailers = recommend(movie)

        # Save current recommendations in session history
        session.setdefault('history', [])
        # Save as a list of dicts (title + poster + genre + year + trailer)
        for i in range(len(recs)):
            session['history'].append({
                'title': recs[i],
                'poster': posters[i],
                'genre': genres[i],
                'year': years[i],
                'trailer': trailers[i]
            })
        session.modified = True  # To tell Flask session data changed

    # Load history from session (if any)
    history = session.get('history', [])

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
    movie_title = request.form.get("movie_title")
    user_feedback = request.form.get("feedback")  # 'like' or 'dislike'

    if movie_title and user_feedback in ("like", "dislike"):
        if movie_title not in feedback_store:
            feedback_store[movie_title] = {"like": 0, "dislike": 0}
        feedback_store[movie_title][user_feedback] += 1
        flash(f"Thanks for your feedback on '{movie_title}'!", "success")
    else:
        flash("Invalid feedback submission.", "danger")

    return redirect(url_for("home"))

@app.route("/clear_history")
def clear_history():
    session.pop('history', None)
    flash("History cleared!", "info")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
