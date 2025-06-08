import pandas as pd
import ast
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from dotenv import load_dotenv
import os

load_dotenv()

# Load the datasets
movies = pd.read_csv(r'C:\Users\user\movie_recommender\movies\movies_metadata.csv', low_memory=False)
credits = pd.read_csv(r'C:\Users\user\movie_recommender\movies\credits.csv')
keywords = pd.read_csv(r'C:\Users\user\movie_recommender\movies\keywords.csv')
links_df = pd.read_csv(r'C:\Users\user\movie_recommender\movies\links.csv')

# Clean IDs
movies['id'] = pd.to_numeric(movies['id'], errors='coerce')
credits['id'] = pd.to_numeric(credits['id'], errors='coerce')
keywords['id'] = pd.to_numeric(keywords['id'], errors='coerce')
links_df['tmdbId'] = pd.to_numeric(links_df['tmdbId'], errors='coerce')

# Merge datasets
movies = movies.merge(credits, on='id')
movies = movies.merge(keywords, on='id')

# Keep relevant columns
movies = movies[['id', 'title', 'overview', 'genres', 'keywords', 'cast', 'crew']]

# Merge TMDB IDs
movies = movies.merge(links_df, left_on='id', right_on='tmdbId', how='left')

# Parsing functions
def parse(x):
    try:
        return [i['name'] for i in ast.literal_eval(x)]
    except:
        return []

def get_director(x):
    try:
        for i in ast.literal_eval(x):
            if i['job'] == 'Director':
                return [i['name']]
        return []
    except:
        return []

def top_3(x):
    try:
        return [i['name'] for i in ast.literal_eval(x)[:3]]
    except:
        return []

# Apply parsing
movies['genres'] = movies['genres'].apply(parse)
movies['keywords'] = movies['keywords'].apply(parse)
movies['cast'] = movies['cast'].apply(top_3)
movies['crew'] = movies['crew'].apply(get_director)
movies['overview'] = movies['overview'].fillna('')

# Combine into one string
movies['soup'] = movies['overview'] + ' ' + \
                 movies['genres'].apply(lambda x: ' '.join(x)) + ' ' + \
                 movies['keywords'].apply(lambda x: ' '.join(x)) + ' ' + \
                 movies['cast'].apply(lambda x: ' '.join(x)) + ' ' + \
                 movies['crew'].apply(lambda x: ' '.join(x))

movies = movies.head(5000)

# Vectorize the soup
count = CountVectorizer(stop_words='english')
count_matrix = count.fit_transform(movies['soup'])

# Compute similarity matrix
cosine_sim = cosine_similarity(count_matrix, count_matrix)

# Reset index
movies = movies.reset_index()
indices = pd.Series(movies.index, index=movies['title']).drop_duplicates()

# Recommendation function
# def recommend(title, cosine_sim=cosine_sim):
#     if title not in indices:
#         return ["Movie not found."]
#     idx = indices[title]
#     sim_scores = list(enumerate(cosine_sim[idx].flatten()))
#     sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
#     movie_indices = [i[0] for i in sim_scores]
#     return movies['title'].iloc[movie_indices].tolist()

def recommend(title, cosine_sim=cosine_sim):
    if title not in indices:
        return [], [], [], [], []

    idx = indices[title]
    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:6]
    movie_indices = [i[0] for i in sim_scores]

    recommendations, posters, genres, years, trailers = [], [], [], [], []

    for i in movie_indices:
        movie = movies.iloc[i]
        recommendations.append(movie['title'])
        poster, genre, year = fetch_movie_details(movie['tmdbId'])
        trailer_url = fetch_trailer(movie['tmdbId'])

        posters.append(poster)
        genres.append(genre)
        years.append(year)
        trailers.append(trailer_url)

    return recommendations, posters, genres, years, trailers






TMDB_API_KEY = os.getenv("TMDB_API_KEY")  # 🔁 Replace this with your actual TMDB API key

# def fetch_details(title):
#     url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
#     data = requests.get(url).json()
#     if data['results']:
#         result = data['results'][0]
#         poster_url = "https://image.tmdb.org/t/p/w500" + result.get("poster_path", "")
#         year = result.get("release_date", "N/A")[:4]
#         genre_ids = result.get("genre_ids", [])
#         genre_map = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
#                      99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
#                      27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Science Fiction",
#                      10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"}
#         genres = [genre_map.get(gid, "") for gid in genre_ids]
#         return poster_url, ', '.join(genres), year
#     return "", "No Genre", "N/A"


# def recommend_with_details(title):
#     rec_titles = recommend(title)
#     posters = []
#     genres = []
#     years = []
#     for rec in rec_titles:
#         poster, genre, year = fetch_details(rec)
#         posters.append(poster)
#         genres.append(genre)
#         years.append(year)
#     return rec_titles, posters, genres, years

# def get_genre_year(movie_titles):
#     details = []
#     for title in movie_titles:
#         try:
#             result = movies[movies['title'] == title]
#             if not result.empty:
#                 genres = result['genres'].values[0]
#                 genres = ', '.join(genres) if isinstance(genres, list) else ''
#                 release_date = result.get('release_date', ['']).values[0]
#                 year = release_date.split("-")[0] if release_date else "N/A"
#                 details.append(f"{genres} | {year}")
#             else:
#                 details.append("Genre Unknown | Year Unknown")
#         except:
#             details.append("Genre Unknown | Year Unknown")
#     return details

# def get_movie_details(titles, df):
#     details = []
#     for title in titles:
#         try:
#             row = df[df['title'] == title].iloc[0]
#             year = row.get('release_date', '')[:4] if pd.notnull(row.get('release_date', '')) else 'N/A'
#             genres = [g['name'] for g in ast.literal_eval(row['genres'])] if pd.notnull(row.get('genres', '')) else []
#             genre_str = ', '.join(genres) if genres else 'No Genre'
#             details.append(f"{genre_str} | {year}")
#         except Exception as e:
#             details.append("No Genre | N/A")
#     return details


def fetch_movie_details(tmdb_id):
    if pd.isna(tmdb_id):
        return "", "", ""

    url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}?api_key={TMDB_API_KEY}&language=en-US"
    response = requests.get(url)
    if response.status_code != 200:
        return "", "", ""

    data = response.json()
    poster = "https://image.tmdb.org/t/p/w500" + data.get("poster_path", "")
    genre = ', '.join([g['name'] for g in data.get("genres", [])])
    year = data.get("release_date", "")[:4]
    return poster, genre, year

def fetch_trailer(tmdb_id):
    if pd.isna(tmdb_id):
        return ""

    url = f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/videos?api_key={TMDB_API_KEY}&language=en-US"
    response = requests.get(url)

    if response.status_code != 200:
        return ""

    data = response.json()
    videos = data.get("results", [])

    for video in videos:
        if video["site"] == "YouTube" and video["type"] == "Trailer":
            return f"https://www.youtube.com/embed/{video['key']}"

    return ""
