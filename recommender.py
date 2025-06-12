import pandas as pd
import numpy as np  # Added missing import
import ast
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os
from functools import lru_cache
import gc
import joblib

load_dotenv()

# Configuration
CACHE_DIR = "./.cache"
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_MOVIES = 1000

@lru_cache(maxsize=1)
def load_data():
    """Load and cache the movie data"""
    try:
        movies = pd.read_csv(
            "movies_metadata.csv",
            usecols=['id', 'title', 'overview', 'genres'],
            low_memory=False
        ).head(MAX_MOVIES)
        
        movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
        movies = movies.dropna(subset=['id'])
        movies['id'] = movies['id'].astype(int)
        
        movies['genres'] = movies['genres'].apply(
            lambda x: ' '.join([i['name'] for i in ast.literal_eval(x)]) if pd.notna(x) else ''
        )
        movies['soup'] = movies['overview'].fillna('') + ' ' + movies['genres']
        return movies
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame(columns=['id', 'title', 'overview', 'genres', 'soup'])

def compute_similarity():
    """Compute or load cached similarity matrix"""
    cache_file = os.path.join(CACHE_DIR, "similarity.npy")
    
    if os.path.exists(cache_file):
        return joblib.load(cache_file)
    
    movies = load_data()
    if movies.empty:
        return np.array([])
    
    count = CountVectorizer(stop_words='english', max_features=2000)
    count_matrix = count.fit_transform(movies['soup'])
    cosine_sim = cosine_similarity(count_matrix, count_matrix)
    
    joblib.dump(cosine_sim, cache_file)
    del count_matrix
    gc.collect()
    
    return cosine_sim

# TMDB API Functions
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

@lru_cache(maxsize=1024)
def fetch_movie_details(tmdb_id):
    try:
        if not tmdb_id or pd.isna(tmdb_id):
            return "", "", ""
            
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY, 'language': 'en-US'},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        return (
            f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
            ', '.join(g['name'] for g in data.get('genres', [])),
            data.get('release_date', '')[:4] if data.get('release_date') else ""
        )
    except Exception as e:
        print(f"Error fetching details for {tmdb_id}: {e}")
        return "", "", ""

@lru_cache(maxsize=1024)  # Added missing function
def fetch_trailer(tmdb_id):
    try:
        if not tmdb_id or pd.isna(tmdb_id):
            return ""
            
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/videos"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        for video in data.get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return f"https://youtu.be/{video['key']}"
        return ""
    except Exception as e:
        print(f"Error fetching trailer for {tmdb_id}: {e}")
        return ""

def recommend(title):
    """Main recommendation function"""
    try:
        movies = load_data()
        if movies.empty:
            return [], [], [], [], []
            
        cosine_sim = compute_similarity()
        if cosine_sim.size == 0:
            return [], [], [], [], []
        
        indices = pd.Series(movies.index, 
                          index=movies['title'].str.lower()).drop_duplicates()
        
        title_lower = title.lower()
        if title_lower not in indices:
            return [], [], [], [], []
        
        idx = indices[title_lower]
        sim_scores = sorted(enumerate(cosine_sim[idx]), 
                          key=lambda x: x[1], reverse=True)[1:6]
        
        results = []
        for i, _ in sim_scores:
            movie = movies.iloc[i]
            poster, genre, year = fetch_movie_details(movie['id'])
            trailer = fetch_trailer(movie['id'])
            results.append((movie['title'], poster, genre, year, trailer))
        
        return tuple(zip(*results)) if results else ([], [], [], [], [])
    except Exception as e:
        print(f"Error in recommendation: {e}")
        return [], [], [], [], []