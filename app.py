import streamlit as st
from recommender import recommend  # Your existing recommendation function

# Page config
st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# Custom CSS for dark/light mode (optional)
st.markdown("""
    <style>
        .stApp { background-color: #f8f9fa; }
        .dark-mode { background-color: #121212; color: white; }
    </style>
""", unsafe_allow_html=True)

# Sidebar for theme toggle
with st.sidebar:
    st.title("Settings")
    dark_mode = st.toggle("Dark Mode", False)

# Main UI
st.title("🎬 Nupoor's Movie Recommender")

# Input movie
movie = st.text_input("Enter a movie title:", placeholder="The Dark Knight")

if st.button("Recommend"):
    if not movie:
        st.warning("Please enter a movie title!")
    else:
        with st.spinner("Finding recommendations..."):
            recs, posters, genres, years, trailers = recommend(movie)

        if not recs:
            st.error("Movie not found. Try another title!")
        else:
            st.success("Here are your recommendations:")
            cols = st.columns(3)
            for i in range(len(recs)):
                with cols[i % 3]:
                    st.image(posters[i], caption=recs[i], width=200)
                    st.write(f"**Genre:** {genres[i]}")
                    st.write(f"**Year:** {years[i]}")
                    if trailers[i]:
                        st.markdown(f"[▶ Watch Trailer]({trailers[i]})")