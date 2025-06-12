import pandas as pd
import ast
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os
import gc
from functools import lru_cache
from joblib import dump, load

load_dotenv()

from config import CACHE_DIR # Import the shared cache directory
cache_file = os.path.join(CACHE_DIR, 'similarity.joblib')

# --- Memory Optimized Data Loading ---
def load_and_filter_data():
    # Load only the first 3000 movies to reduce memory
    movies = pd.read_csv(
        os.path.join('movies', 'movies_metadata.csv'),
        low_memory=False,
        usecols=['id', 'title', 'overview', 'genres']
    ).head(2000)
    
    # Load and merge other datasets
    credits = pd.read_csv(
        "https://huggingface.co/datasets/nupoorm/credits-dataset/resolve/main/credits.csv",
        usecols=['id', 'cast', 'crew']
    )
    keywords = pd.read_csv(
        os.path.join('movies', 'keywords.csv'),
        usecols=['id', 'keywords']
    )
    links = pd.read_csv(
        os.path.join('movies', 'links.csv'),
        usecols=['tmdbId']
    )
    
    # Clean and merge
    for df in [credits, keywords, links]:
        movies = movies.merge(df, how='left', left_on='id', right_on='id' if 'id' in df.columns else 'tmdbId')
    
    return movies

movies = load_and_filter_data()

def process_movies(movies):
    # Convert to efficient dtypes
    movies = movies.astype({
        'id': 'int32',
        'title': 'category',
        'overview': 'string'
    })
    
    # Parsing functions with memory cleanup
    def safe_parse(x):
        try:
            if pd.isna(x):
                return []
            return [i['name'] for i in ast.literal_eval(x)]
        except (ValueError, SyntaxError):
            return []

    # Apply parsing with null checks
    movies['genres'] = movies['genres'].apply(safe_parse)
    movies['keywords'] = movies['keywords'].apply(lambda x: safe_parse(x) if pd.notna(x) else [])
    
    # Get top 3 cast members
    movies['cast'] = movies['cast'].apply(
        lambda x: safe_parse(x)[:3] if pd.notna(x) else [])
    
    # Get director only
    def get_director(x):
        try:
            if pd.isna(x):
                return ''
            crew = ast.literal_eval(x)
            return next((i['name'] for i in crew if i['job'] == 'Director'), '')
        except (ValueError, SyntaxError, StopIteration):
            return ''
    
    movies['crew'] = movies['crew'].apply(get_director)
    
    # Create combined text feature with null checks
    movies['soup'] = (
        movies['overview'].fillna('') + ' ' +
        movies['genres'].apply(lambda x: ' '.join(x) if x else '') + ' ' +
        movies['keywords'].apply(lambda x: ' '.join(x) if x else '') + ' ' +
        movies['cast'].apply(lambda x: ' '.join(x) if x else '') + ' ' +
        movies['crew'].fillna('')
    )
    
    return movies

movies = process_movies(movies)

# --- Optimized Similarity Calculation ---


def compute_similarity():
    """Calculate or load cached similarity matrix"""
    cache_file = 'similarity.joblib'
    
    if os.path.exists(cache_file):
        print("Loading pre-computed similarity matrix...")
        return load(cache_file)
    
    print("Computing similarity matrix...")
    count = CountVectorizer(stop_words='english', max_features=5000)
    count_matrix = count.fit_transform(movies['soup'])
    
    # Compute in chunks for large datasets
    cosine_sim = cosine_similarity(count_matrix, count_matrix)
    
    # Clean up and cache
    del count_matrix
    dump(cosine_sim, cache_file)
    gc.collect()
    
    return cosine_sim

# Initialize the matrix (will load or compute)
cosine_sim = compute_similarity()

# ... (keep all previous imports and data loading code) ...

# --- TMDB API Functions ---
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

@lru_cache(maxsize=1024)
def fetch_movie_details(tmdb_id):
    """Get movie details from TMDB API with caching"""
    if pd.isna(tmdb_id):
        return "", "", ""
    
    try:
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY, 'language': 'en-US'},
            timeout=5
        )
        if response.status_code != 200:
            return "", "", ""
        
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
    """Get movie trailer from TMDB API with caching"""
    if pd.isna(tmdb_id):
        return ""
    
    try:
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/videos"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY, 'language': 'en-US'},
            timeout=5
        )
        if response.status_code != 200:
            return ""
        
        data = response.json()
        for video in data.get("results", []):
            if video.get("site") == "YouTube" and video.get("type") == "Trailer":
                return f"https://www.youtube.com/embed/{video['key']}"
        return ""
    except Exception:
        return ""

# --- Recommendation Function ---
def recommend(title, cosine_sim=cosine_sim):
    """Get movie recommendations with details"""
    indices = pd.Series(movies.index, index=movies['title']).drop_duplicates()
    
    if title not in indices:
        return [], [], [], [], []
    
    idx = indices[title]
    sim_scores = sorted(enumerate(cosine_sim[idx]), 
                 key=lambda x: x[1], reverse=True)[1:6]
    
    results = []
    for i, _ in sim_scores:
        movie = movies.iloc[i]
        tmdb_id = movie.get('tmdbId')
        poster, genre, year = fetch_movie_details(tmdb_id)
        trailer = fetch_trailer(tmdb_id)
        results.append((movie['title'], poster, genre, year, trailer))
    
    return tuple(zip(*results)) if results else ([], [], [], [], [])

