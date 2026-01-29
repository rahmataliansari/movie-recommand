import requests
import streamlit as st

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com" or "https://movie-recommand-recod.onrender.com/" or "http://127.0.0.1:8000"
# API_BASE = "http://127.0.0.1:8000"   # local use ke liye

TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(
    page_title="🎬 Movie Recommender",
    page_icon="🎬",
    layout="wide"
)

# =============================
# STYLES
# =============================
st.markdown("""
<style>
.block-container { max-width: 1400px; padding-top: 1rem; }
.movie-title {
    font-size: 0.9rem;
    line-height: 1.2rem;
    height: 2.4rem;
    overflow: hidden;
}
.small-muted { color:#6b7280; font-size:0.9rem; }
</style>
""", unsafe_allow_html=True)

# =============================
# SESSION STATE
# =============================
if "page" not in st.session_state:
    st.session_state.page = "home"

if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

# =============================
# ROUTING
# =============================
def goto_home():
    st.session_state.page = "home"
    st.session_state.selected_tmdb_id = None
    st.rerun()

def goto_details(tmdb_id):
    st.session_state.page = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.rerun()

# =============================
# API HELPER
# =============================
@st.cache_data(ttl=30)
def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

# =============================
# POSTER GRID (FIXED)
# =============================
def poster_grid(cards, cols=6):
    if not cards:
        st.info("No movies found.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0

    for _ in range(rows):
        columns = st.columns(cols)
        for col in columns:
            if idx >= len(cards):
                break

            movie = cards[idx]
            idx += 1

            with col:
                if movie.get("poster_url"):
                    # ✅ FIX: compatible with all Streamlit versions
                    st.image(movie["poster_url"], width=200)
                else:
                    st.write("🖼️ No poster")

                if st.button("Open", key=f"open_{movie['tmdb_id']}"):
                    goto_details(movie["tmdb_id"])

                st.markdown(
                    f"<div class='movie-title'>{movie.get('title','')}</div>",
                    unsafe_allow_html=True
                )

# =============================
# HEADER
# =============================
st.title("🎬 Movie Recommender")
st.markdown(
    "<div class='small-muted'>Search → Select → Details → Recommendations</div>",
    unsafe_allow_html=True
)
st.divider()

# ==========================================================
# HOME PAGE
# ==========================================================
if st.session_state.page == "home":

    query = st.text_input("🔍 Search movie title")

    if query.strip():
        data = api_get("/tmdb/search", params={"query": query.strip()})

        if isinstance(data, dict) and "results" in data:

            # ---------- SUGGESTIONS ----------
            suggestions = []
            label_to_id = {}

            for m in data["results"][:10]:
                title = m.get("title")
                tmdb_id = m.get("id")
                year = (m.get("release_date") or "")[:4]

                if title and tmdb_id:
                    label = f"{title} ({year})" if year else title
                    suggestions.append(label)
                    label_to_id[label] = tmdb_id

            if suggestions:
                selected = st.selectbox(
                    "🎯 Suggestions",
                    ["-- Select a movie --"] + suggestions
                )

                if selected != "-- Select a movie --":
                    goto_details(label_to_id[selected])
                    st.stop()

            # ---------- GRID RESULTS ----------
            cards = []
            for m in data["results"][:24]:
                cards.append({
                    "tmdb_id": m["id"],
                    "title": m["title"],
                    "poster_url": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None
                })

            st.subheader("Results")
            poster_grid(cards)

        st.stop()

    # ---------- HOME FEED ----------
    st.subheader("🔥 Trending Movies")
    home_cards = api_get("/home", params={"category": "trending", "limit": 24})
    poster_grid(home_cards)

# ==========================================================
# DETAILS PAGE
# ==========================================================
elif st.session_state.page == "details":

    tmdb_id = st.session_state.selected_tmdb_id
    if not tmdb_id:
        st.warning("No movie selected.")
        st.stop()

    data = api_get(f"/movie/id/{tmdb_id}")
    if not data:
        st.stop()

    left, right = st.columns([1, 2])

    with left:
        if data.get("poster_url"):
            st.image(data["poster_url"], width=300)

    with right:
        st.subheader(data.get("title", ""))
        st.markdown(
            f"<div class='small-muted'>Release: {data.get('release_date','-')}</div>",
            unsafe_allow_html=True
        )
        st.write(data.get("overview", ""))

    st.divider()
    st.subheader("✅ Recommendations")

    bundle = api_get(
        "/movie/search",
        params={"query": data.get("title",""), "tfidf_top_n": 12, "genre_limit": 12}
    )

    if isinstance(bundle, dict):

        if bundle.get("tfidf_recommendations"):
            st.markdown("### 🔎 Similar Movies")
            tfidf_cards = []
            for x in bundle["tfidf_recommendations"]:
                tmdb = x.get("tmdb", {})
                tfidf_cards.append({
                    "tmdb_id": tmdb.get("tmdb_id"),
                    "title": tmdb.get("title"),
                    "poster_url": tmdb.get("poster_url")
                })
            poster_grid(tfidf_cards)

        if bundle.get("genre_recommendations"):
            st.markdown("### 🎭 Genre Based")
            poster_grid(bundle["genre_recommendations"])

    if st.button("⬅ Back to Home"):
        goto_home()
