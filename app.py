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
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style.css")

# Header with Logo
col1, col2 = st.columns([0.1, 0.9])
with col1:
    # You can replace this with your actual logo image
    # st.image("nm_logo.png", width=40)
    st.markdown("""
    <div class="logo-badge">NM</div>
    """, unsafe_allow_html=True)
    
with col2:
    st.title("Nupoor Mhadgut's Movie Recommender")

# Recommendation Engine
movie = st.text_input("Enter a movie you like:", placeholder="The Dark Knight")

if st.button("Get Recommendations"):
    if not movie:
        st.warning("Please enter a movie title!")
    else:
        with st.spinner("Finding the best recommendations..."):
            time.sleep(1)  # Simulate loading
            
            recs, posters, genres, years, trailers = recommend(movie)
            
            if not recs:
                st.error("Movie not found. Try another title!")
            else:
                st.success("Here are your recommendations:")
                
                cols = st.columns(3)
                for i in range(len(recs)):
                    with cols[i % 3]:
                        with st.container():
                            st.image(
                                posters[i] if posters[i] else "https://via.placeholder.com/300x450?text=No+Poster",
                                width=200,
                                caption=recs[i]
                            )
                            st.write(f"**{genres[i]}** | {years[i]}")
                            
                            if trailers[i]:
                                st.markdown(
                                    f'<a href="{trailers[i]}" target="_blank" class="trailer-button">▶ Watch Trailer</a>',
                                    unsafe_allow_html=True
                                )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button(f"👍 Like {i+1}", key=f"like_{i}"):
                                    st.session_state[f'feedback_{i}'] = 'liked'
                                    st.toast(f"You liked {recs[i]}!")
                            with col2:
                                if st.button(f"👎 Dislike {i+1}", key=f"dislike_{i}"):
                                    st.session_state[f'feedback_{i}'] = 'disliked'
                                    st.toast(f"You disliked {recs[i]}!")