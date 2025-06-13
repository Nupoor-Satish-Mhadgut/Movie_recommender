import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os
from functools import lru_cache

load_dotenv()

# Configuration
MAX_MOVIES = 5000  # Reduced for better performance

@lru_cache(maxsize=1)
def load_data():
    """Load and cache movie data"""
    try:
        movies = pd.read_csv(
            "movies_metadata.csv",
            usecols=['id', 'title', 'genres', 'release_date'],
            low_memory=False
        ).head(MAX_MOVIES)
        
        # Clean data
        movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
        movies = movies.dropna(subset=['id'])
        movies['id'] = movies['id'].astype(int)
        
        # Process genres
        movies['genres'] = movies['genres'].apply(
            lambda x: ', '.join([i['name'] for i in ast.literal_eval(x)]) if pd.notna(x) else ''
        )
        
        # Process year
        movies['year'] = movies['release_date'].str[:4]
        
        return movies[['id', 'title', 'genres', 'year']]
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def compute_similarity():
    """Compute similarity matrix"""
    movies = load_data()
    if movies.empty:
        return None
    
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(movies['genres'])
    return cosine_similarity(tfidf_matrix, tfidf_matrix)

# TMDB API
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

@lru_cache(maxsize=1024)
def fetch_movie_poster(tmdb_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
        response = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=5)
        data = response.json()
        return f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}"
    except:
        return ""

@lru_cache(maxsize=1024)
def fetch_trailer(tmdb_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos"
        response = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=5)
        data = response.json()
        for video in data.get("results", []):
            if video.get("type") == "Trailer":
                return f"https://youtu.be/{video['key']}"
        return ""
    except:
        return ""

def recommend(title):
    """Main recommendation function"""
    try:
        movies = load_data()
        cosine_sim = compute_similarity()
        
        if movies.empty or cosine_sim is None:
            return [], [], [], [], []
        
        # Find matching movie
        matches = movies[movies['title'].str.lower() == title.lower()]
        if matches.empty:
            return [], [], [], [], []
        
        idx = matches.index[0]
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
        
        results = []
        for i, _ in sim_scores:
            movie = movies.iloc[i]
            poster = fetch_movie_poster(movie['id'])
            trailer = fetch_trailer(movie['id'])
            results.append((movie['title'], poster, movie['genres'], movie['year'], trailer))
        
        return tuple(zip(*results)) if results else ([], [], [], [], [])
    except Exception as e:
        print(f"Error in recommendation: {e}")
        return [], [], [], [], []