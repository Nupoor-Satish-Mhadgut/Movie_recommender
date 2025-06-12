import streamlit as st
from recommender import recommend
import time
from PIL import Image

# Page Configuration
st.set_page_config(
    page_title="Nupoor Mhadgut's Movie Recommendation",
    page_icon="🎬",
    layout="wide"
)

# Load custom CSS
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"CSS file {file_name} not found. Using default styles.")

local_css("style.css")

# Header with Logo
col1, col2 = st.columns([0.1, 0.9])
with col1:
    st.markdown("""
    <div class="logo-badge">NM</div>
    """, unsafe_allow_html=True)
    
with col2:
    st.title("Nupoor Mhadgut's Movie Recommender")

# Initialize session state for feedback if not exists
if 'feedback' not in st.session_state:
    st.session_state.feedback = {}

# Recommendation Engine
movie = st.text_input("Enter a movie you like:", placeholder="The Dark Knight", key="movie_input")

if st.button("Get Recommendations", key="recommend_button"):
    if not movie.strip():
        st.warning("Please enter a movie title!")
    else:
        with st.spinner("Finding the best recommendations..."):
            start_time = time.time()
            
            try:
                recs, posters, genres, years, trailers = recommend(movie)
                
                if not recs:
                    st.error("Movie not found. Try another title!")
                else:
                    st.success(f"Found {len(recs)} recommendations in {time.time()-start_time:.2f} seconds")
                    
                    # Display recommendations in responsive grid
                    cols = st.columns(3)
                    for i, (rec, poster, genre, year, trailer) in enumerate(zip(recs, posters, genres, years, trailers)):
                        with cols[i % 3]:
                            with st.container():
                                # Movie Poster
                                poster_url = poster if poster else "https://via.placeholder.com/300x450?text=No+Poster"
                                st.image(
                                    poster_url,
                                    width=200,
                                    caption=rec,
                                    use_column_width=True
                                )
                                
                                # Movie Info
                                st.markdown(f"### {rec}")
                                st.caption(f"**{genre}** | {year}")
                                
                                # Trailer Button
                                if trailer:
                                    st.markdown(
                                        f'<a href="{trailer}" target="_blank" class="trailer-button">▶ Watch Trailer</a>',
                                        unsafe_allow_html=True
                                    )
                                
                                # Feedback Buttons
                                feedback_col1, feedback_col2 = st.columns(2)
                                with feedback_col1:
                                    if st.button(f"👍 Like", key=f"like_{i}"):
                                        st.session_state.feedback[rec] = 'liked'
                                        st.toast(f"You liked {rec}!")
                                with feedback_col2:
                                    if st.button(f"👎 Dislike", key=f"dislike_{i}"):
                                        st.session_state.feedback[rec] = 'disliked'
                                        st.toast(f"You disliked {rec}!")
                                
                                st.markdown("---")  # Separator
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.stop()

# Optional: Display feedback history in sidebar
with st.sidebar:
    if st.session_state.feedback:
        st.subheader("Your Feedback History")
        for movie_title, feedback in st.session_state.feedback.items():
            st.write(f"{'👍' if feedback == 'liked' else '👎'} {movie_title}")