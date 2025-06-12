import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os
import numpy as np
from functools import lru_cache
import gc
import joblib
from datasets import load_dataset  # For Hugging Face dataset

load_dotenv()

# Configuration
CACHE_DIR = "./.cache"
os.makedirs(CACHE_DIR, exist_ok=True)
MAX_MOVIES = 10000
CREDITS_URL = "https://huggingface.co/datasets/nupoorm/credits-dataset/resolve/main/credits.csv"

@lru_cache(maxsize=1)
def load_data():
    """Load and cache all movie data with proper merging"""
    try:
        # Load movies metadata
        movies = pd.read_csv(
            "movies_metadata.csv",
            usecols=['id', 'title', 'overview', 'genres', 'popularity', 'vote_average'],
            low_memory=False
        ).head(MAX_MOVIES)
        
        # Clean and convert ID column
        movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
        movies = movies.dropna(subset=['id'])
        movies['id'] = movies['id'].astype(int)

        # Load links data
        links = pd.read_csv("links.csv")
        links['tmdbId'] = pd.to_numeric(links['tmdbId'], errors='coerce')
        links = links.dropna(subset=['tmdbId'])
        links['tmdbId'] = links['tmdbId'].astype(int)

        # Load keywords data
        keywords = pd.read_csv("keywords.csv")
        keywords['id'] = pd.to_numeric(keywords['id'], errors='coerce')
        keywords = keywords.dropna(subset=['id'])
        keywords['id'] = keywords['id'].astype(int)

        # Load credits data from Hugging Face
        credits = pd.read_csv(CREDITS_URL)
        credits['id'] = pd.to_numeric(credits['id'], errors='coerce')
        credits = credits.dropna(subset=['id'])
        credits['id'] = credits['id'].astype(int)

        # Process genres
        movies['genres'] = movies['genres'].apply(
            lambda x: ' '.join([i['name'] for i in ast.literal_eval(x)]) if pd.notna(x) else ''
        )

        # Process keywords
        keywords['keywords'] = keywords['keywords'].apply(
            lambda x: ' '.join([k['name'] for k in ast.literal_eval(x)]) if pd.notna(x) else ''
        )

        # Process credits (cast and crew)
        def process_credits(df):
            df['cast'] = df['cast'].apply(
                lambda x: ' '.join([i['name'] for i in ast.literal_eval(x)][:5]) if pd.notna(x) else ''
            )
            df['crew'] = df['crew'].apply(
                lambda x: ' '.join([i['name'] for i in ast.literal_eval(x) if i['job'] in ['Director', 'Producer']])
                if pd.notna(x) else ''
            )
            return df

        credits = process_credits(credits)

        # Merge all datasets
        merged = movies.merge(
            links,
            how='left',
            left_on='id',
            right_on='tmdbId'
        ).merge(
            keywords[['id', 'keywords']],
            how='left',
            on='id'
        ).merge(
            credits[['id', 'cast', 'crew']],
            how='left',
            on='id'
        )

        # Create the recommendation soup
        merged['soup'] = (
            merged['overview'].fillna('') + ' ' +
            merged['genres'] + ' ' +
            merged['keywords'] + ' ' +
            merged['cast'] + ' ' +
            merged['crew'] + ' ' +
            merged['vote_average'].astype(str)
        )

        # Clean up
        merged = merged.drop_duplicates(subset=['id'])
        merged = merged.dropna(subset=['soup'])

        return merged

    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def compute_similarity():
    """Compute or load cached similarity matrix"""
    cache_file = os.path.join(CACHE_DIR, "similarity.joblib")
    
    if os.path.exists(cache_file):
        return joblib.load(cache_file)
    
    movies = load_data()
    if movies.empty:
        return np.array([])
    
    # Use TF-IDF with n-grams for better results
    tfidf = TfidfVectorizer(
        stop_words='english',
        max_features=10000,
        ngram_range=(1, 2)  # Include bigrams
    )
    tfidf_matrix = tfidf.fit_transform(movies['soup'])
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    joblib.dump(cosine_sim, cache_file)
    del tfidf_matrix
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
            params={
                'api_key': TMDB_API_KEY,
                'language': 'en-US',
                'append_to_response': 'credits'
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Get top 3 cast members
        cast = ', '.join([actor['name'] for actor in data.get('credits', {}).get('cast', [])[:3]])
        
        return (
            f"https://image.tmdb.org/t/p/w500{data.get('poster_path', '')}",
            cast,
            data.get('release_date', '')[:4] if data.get('release_date') else ""
        )
    except Exception as e:
        print(f"Error fetching details for {tmdb_id}: {e}")
        return "", "", ""

@lru_cache(maxsize=1024)
def fetch_trailer(tmdb_id):
    try:
        if not tmdb_id or pd.isna(tmdb_id):
            return ""
            
        url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/videos"
        response = requests.get(
            url,
            params={'api_key': TMDB_API_KEY},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Try to find official trailer first, then any trailer
        trailer = next(
            (v for v in data.get("results", [])
            if v.get("type") == "Trailer" and v.get("official", False)),
            None
        )
        
        if not trailer:
            trailer = next(
                (v for v in data.get("results", [])
                if v.get("type") == "Trailer"),
                None
            )
        
        return f"https://youtu.be/{trailer['key']}" if trailer else ""
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
        
        # Create index with lowercase for case-insensitive matching
        indices = pd.Series(movies.index, 
                          index=movies['title'].str.lower()).drop_duplicates()
        
        title_lower = title.lower()
        if title_lower not in indices:
            return [], [], [], [], []
        
        idx = indices[title_lower]
        sim_scores = list(enumerate(cosine_sim[idx]))
        
        # Sort by similarity score and popularity
        sim_scores = sorted(sim_scores, 
                          key=lambda x: (x[1], movies.iloc[x[0]]['popularity']), 
                          reverse=True)[1:6]
        
        results = []
        for i, _ in sim_scores:
            movie = movies.iloc[i]
            tmdb_id = movie['tmdbId'] if pd.notna(movie['tmdbId']) else movie['id']
            poster, cast, year = fetch_movie_details(tmdb_id)
            trailer = fetch_trailer(tmdb_id)
            results.append((movie['title'], poster, cast, year, trailer))
        
        return tuple(zip(*results)) if results else ([], [], [], [], [])
    except Exception as e:
        print(f"Error in recommendation: {e}")
        return [], [], [], [], []