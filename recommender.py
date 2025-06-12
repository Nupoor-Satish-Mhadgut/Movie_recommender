import pandas as pd
import ast
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os
from functools import lru_cache
import gc

load_dotenv()

# Configuration
CACHE_DIR = "./.cache"
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_MOVIES = 1000  # Reduced for memory efficiency

@lru_cache(maxsize=1)
def load_data():
    """Load and cache the movie data"""
    movies = pd.read_csv(
        "movies_metadata.csv",
        usecols=['id', 'title', 'overview', 'genres'],
        low_memory=False
    ).head(MAX_MOVIES)
    
    # Basic processing
    movies['genres'] = movies['genres'].apply(
        lambda x: ' '.join([i['name'] for i in ast.literal_eval(x)]) if pd.notna(x) else ''
    )
    movies['soup'] = movies['overview'].fillna('') + ' ' + movies['genres']
    return movies

def compute_similarity():
    """Compute or load cached similarity matrix"""
    cache_file = os.path.join(CACHE_DIR, "similarity.joblib")
    
    if os.path.exists(cache_file):
        return pd.read_pickle(cache_file)
    
    movies = load_data()
    count = CountVectorizer(stop_words='english', max_features=2000)
    count_matrix = count.fit_transform(movies['soup'])
    cosine_sim = cosine_similarity(count_matrix, count_matrix)
    
    # Cache and clean up
    pd.to_pickle(cosine_sim, cache_file)
    del count_matrix
    gc.collect()
    
    return cosine_sim

# TMDB API Functions
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

@lru_cache(maxsize=1024)
def fetch_movie_details(tmdb_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY, 'language': 'en-US'},
            timeout=5
        )
        data = response.json()
        return (
            f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
            ', '.join(g['name'] for g in data.get('genres', [])),
            data.get('release_date', '')[:4]
        )
    except Exception:
        return "", "", ""

@lru_cache(maxsize=1024)
def fetch_trailer(tmdb_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/videos"
        response = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=5)
        data = response.json()
        for video in data.get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return f"https://youtu.be/{video['key']}"
        return ""
    except Exception:
        return ""

def recommend(title):
    """Main recommendation function"""
    movies = load_data()
    cosine_sim = compute_similarity()
    indices = pd.Series(movies.index, index=movies['title']).drop_duplicates()
    
    if title not in indices:
        return [], [], [], [], []
    
    idx = indices[title]
    sim_scores = sorted(enumerate(cosine_sim[idx]), key=lambda x: x[1], reverse=True)[1:6]
    
    results = []
    for i, _ in sim_scores:
        movie = movies.iloc[i]
        poster, genre, year = fetch_movie_details(movie.get('id'))  # Using internal ID as fallback
        trailer = fetch_trailer(movie.get('id'))
        results.append((movie['title'], poster, genre, year, trailer))
    
    return tuple(zip(*results)) if results else ([], [], [], [], [])