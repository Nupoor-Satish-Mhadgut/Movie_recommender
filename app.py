import streamlit as st
from recommender import recommend
import time
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Nupoor Mhadgut's Movie Recommendation System",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .movie-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .movie-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .trailer-button {
        background-color: #0d6efd;
        color: white;
        padding: 8px 15px;
        border-radius: 5px;
        text-decoration: none;
        display: inline-block;
        margin: 10px 0;
        text-align: center;
        transition: all 0.3s ease;
    }
    .trailer-button:hover {
        background-color: #0b5ed7;
        color: white;
    }
    .feedback-button {
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# App Header
st.title("🎬 Nupoor Mhadgut's Movie Recommendation System")

# Recommendation Engine
movie = st.text_input("Enter a movie you like:", placeholder="Tom and Huck ")

if st.button("Get Recommendations"):
    if not movie.strip():
        st.warning("Please enter a movie title!")
    else:
        with st.spinner("Finding the best recommendations..."):
            time.sleep(1)  # Simulate loading
            
            # Get recommendations (name, poster, genre, year, trailer)
            names, posters, genres, years, trailers = recommend(movie)
            
            if not names:
                st.error("Movie not found. Try another title!")
            else:
                st.success("Here are your recommendations:")
                
                # Display 3 recommendations per row
                cols = st.columns(3)
                for i in range(len(names)):
                    with cols[i % 3]:
                        # Movie Card
                        st.markdown(f"""
                        <div class="movie-card">
                            <img src="{posters[i] if posters[i] else 'https://via.placeholder.com/300x450?text=No+Poster'}" 
                                 style="width:100%; border-radius:8px; margin-bottom:10px;">
                            <h4>{names[i]}</h4>
                            <p><strong>{genres[i]}</strong> | {years[i]}</p>
                            {f'<a href="{trailers[i]}" target="_blank" class="trailer-button">▶ Watch Trailer</a>' if trailers[i] else ''}
                            <div style="display:flex; justify-content:center;">
                                <button class="feedback-button" onclick="alert('You liked {names[i]}!')">👍 Like</button>
                                <button class="feedback-button" onclick="alert('You disliked {names[i]}!')">👎 Dislike</button>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)