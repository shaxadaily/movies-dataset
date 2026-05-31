import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Movie Recommendation Insights", layout="wide")
st.title("🎬 Movie Recommendation Insights Dashboard")


@st.cache_data
def load_data():
    movies_df = pd.read_csv("./movies.csv")
    ratings_df = pd.read_csv("./ratings.csv")

    movies_df["title"] = movies_df["title"].str.replace(r'^"|"$', "", regex=True)
    movies_df["year"] = movies_df["title"].str.extract(r"\((\d{4})\)").astype("Int64")
    movies_df["genre_list"] = movies_df["genres"].apply(
        lambda x: x.split("|") if pd.notna(x) else []
    )
    ratings_df["rating_year"] = pd.to_datetime(ratings_df["timestamp"], unit="s").dt.year

    all_genres = sorted({g for gl in movies_df["genre_list"] for g in gl})
    all_years = sorted(movies_df["year"].dropna().unique().tolist(), reverse=True)

    return movies_df, ratings_df, all_genres, all_years


@st.cache_data
def build_master(movies_df, ratings_df):
    stats = (
        ratings_df.groupby("movieId")["rating"]
        .agg(average_rating="mean", number_of_ratings="count")
        .reset_index()
    )
    return movies_df.merge(stats, on="movieId", how="inner")


@st.cache_data
def build_comparison_df(ratings_df, movies_df):
    return ratings_df.merge(movies_df[["movieId", "title"]], on="movieId", how="left")


movies_df, ratings_df, all_genres, all_years = load_data()
master_df = build_master(movies_df, ratings_df)
comparison_df = build_comparison_df(ratings_df, movies_df)

with st.sidebar:
    st.header("Filter Criteria")
    max_ratings = int(master_df["number_of_ratings"].max()) if not master_df.empty else 1
    min_ratings_input = st.number_input(
        "Minimum Number of Ratings", min_value=0, max_value=max_ratings, value=50, step=1
    )
    selected_genre = st.selectbox("Select Genre", ["All"] + all_genres)
    selected_year = st.selectbox("Select Year", ["All"] + [str(y) for y in all_years])

filtered_df = master_df[master_df["number_of_ratings"] >= min_ratings_input]
if selected_genre != "All":
    filtered_df = filtered_df[filtered_df["genre_list"].apply(lambda x: selected_genre in x)]
if selected_year != "All":
    filtered_df = filtered_df[filtered_df["year"] == int(selected_year)]

top_10 = (
    filtered_df
    .sort_values(["average_rating", "number_of_ratings"], ascending=[False, False])
    .head(10)[["title", "average_rating", "number_of_ratings", "genres"]]
    .reset_index(drop=True)
    .rename(columns={
        "title": "Movie Title",
        "average_rating": "Average Rating",
        "number_of_ratings": "Number of Ratings",
        "genres": "Genres",
    })
)

st.subheader("🏆 Top 10 Results Based on Filters")
if not top_10.empty:
    st.dataframe(top_10.style.format({"Average Rating": "{:.2f}"}), use_container_width=True)
else:
    st.info("No movies matched your filters.")

st.divider()
st.header("🎥 Compare Two Movies")

movie_options = sorted(master_df["title"].dropna().unique())
col1, col2 = st.columns(2)
with col1:
    movie_1 = st.selectbox("Select First Movie", movie_options, key="movie1")
with col2:
    movie_2 = st.selectbox(
        "Select Second Movie", movie_options, index=min(1, len(movie_options) - 1), key="movie2"
    )

m1 = comparison_df[comparison_df["title"] == movie_1]
m2 = comparison_df[comparison_df["title"] == movie_2]


def rating_stats(s):
    if s.empty:
        return {"avg": float("nan"), "count": 0, "std": float("nan")}
    return {"avg": round(s.mean(), 3), "count": int(s.count()), "std": round(s.std(), 3)}


s1, s2 = rating_stats(m1["rating"]), rating_stats(m2["rating"])

st.subheader("📊 Rating Statistics")
st.dataframe(
    pd.DataFrame({
        "Metric": ["Average Rating", "Number of Ratings", "Standard Deviation"],
        movie_1: [s1["avg"], s1["count"], s1["std"]],
        movie_2: [s2["avg"], s2["count"], s2["std"]],
    }),
    use_container_width=True,
)

st.subheader("📈 Histogram of Ratings")
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(m1["rating"], bins=10, alpha=0.6, label=movie_1)
ax.hist(m2["rating"], bins=10, alpha=0.6, label=movie_2)
ax.set(title="Ratings Distribution", xlabel="Rating", ylabel="Frequency")
ax.legend()
st.pyplot(fig)
plt.close(fig)

for subheader, agg_fn, ylabel, title in [
    ("⭐ Average Rating Per Year",
     lambda df: df.groupby("rating_year")["rating"].mean().reset_index(),
     "Average Rating", "Average Rating Per Year"),
    ("🗳️ Number of Ratings Per Year",
     lambda df: df.groupby("rating_year")["rating"].count().reset_index(),
     "Number of Ratings", "Number of Ratings Per Year"),
]:
    st.subheader(subheader)
    fig, ax = plt.subplots(figsize=(10, 4))
    for df, label in [(m1, movie_1), (m2, movie_2)]:
        agg = agg_fn(df)
        ax.plot(agg["rating_year"], agg["rating"], marker="o", label=label)
    ax.set(xlabel="Year", ylabel=ylabel, title=title)
    ax.legend()
    st.pyplot(fig)
    plt.close(fig)
