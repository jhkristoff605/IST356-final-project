import time
from typing import Dict, List, Tuple
import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import googlemaps

API_KEY = os.environ["GMAPS_KEY"]
CATEGORIES: Dict[str, str] = {
    "Landmarks / Attractions": "tourist_attraction",
    "Museums": "museum",
    "Parks": "park",
    "Restaurants": "restaurant",
    "Cafes": "cafe",
}
st.set_page_config(page_title="City Explorer", layout="wide")
st.title("City Explorer")
@st.cache_resource
def get_gmaps_client() -> googlemaps.Client:
    return googlemaps.Client(key=API_KEY)
def geocode_city(city_name: str) -> Tuple[float, float, str]:
    gmaps = get_gmaps_client()
    res = gmaps.geocode(city_name)

    if not res:
        raise ValueError(f"Could not geocode city: {city_name}")

    loc = res[0]["geometry"]["location"]
    formatted = res[0].get("formatted_address", city_name)

    return float(loc["lat"]), float(loc["lng"]), formatted


def fetch_nearby(
    lat: float,
    lng: float,
    place_type: str,
    radius_m: int,
    max_pages: int,
) -> List[dict]:

    gmaps = get_gmaps_client()
    results: List[dict] = []
    page_token = None

    for _ in range(max_pages):
        response = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius_m,
            type=place_type,
            page_token=page_token,
        )

        results.extend(response.get("results", []))
        page_token = response.get("next_page_token")

        if not page_token:
            break

        time.sleep(2)  # required delay for pagination token

    return results


def build_map(
    city_label: str,
    center: Tuple[float, float],
    categorized_places: Dict[str, List[dict]],
) -> folium.Map:

    lat, lng = center
    m = folium.Map(location=(lat, lng), zoom_start=13)

    folium.Marker(
        (lat, lng),
        tooltip=f"{city_label} (center)",
        popup=city_label,
    ).add_to(m)

    for category, places in categorized_places.items():
        layer = folium.FeatureGroup(name=category, show=True)

        for p in places:
            loc = p.get("geometry", {}).get("location", {})
            if "lat" not in loc or "lng" not in loc:
                continue

            name = p.get("name", "Unknown")
            rating = p.get("rating")
            address = p.get("vicinity", "")

            popup = f"<b>{name}</b><br/>"
            if rating is not None:
                popup += f"Rating: {rating}<br/>"
            popup += address

            folium.Marker(
                (loc["lat"], loc["lng"]),
                tooltip=name,
                popup=popup,
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def places_to_dataframe(categorized_places: Dict[str, List[dict]]) -> pd.DataFrame:
    rows = []

    for category, places in categorized_places.items():
        for p in places:
            loc = p.get("geometry", {}).get("location", {})
            rows.append({
                "category": category,
                "name": p.get("name"),
                "rating": p.get("rating"),
                "address": p.get("vicinity"),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "place_id": p.get("place_id"),
            })

    df = pd.DataFrame(rows)

    if "place_id" in df.columns:
        df = df.drop_duplicates(subset="place_id")

    return df.sort_values(
        by=["category", "rating"],
        ascending=[True, False],
        na_position="last"
    )
with st.sidebar:
    city = st.text_input("City", "Denver, CO")
    selected_categories = st.multiselect(
        "Categories",
        list(CATEGORIES.keys()),
        default=["Landmarks / Attractions", "Restaurants"]
    )
    radius = st.slider("Search radius (meters)", 1000, 20000, 8000, step=500)
    pages = st.slider("Pages per category", 1, 3, 2)

    run_search = st.button("Find places", type="primary")
    clear = st.button("Clear results")
if clear:
    for key in ["categorized_results", "results_df", "meta"]:
        st.session_state.pop(key, None)
if run_search:
    if not selected_categories:
        st.warning("Please select at least one category.")
        st.stop()

    try:
        with st.spinner("Searching for places..."):
            lat, lng, formatted_city = geocode_city(city)

            categorized_results = {}
            for label in selected_categories:
                categorized_results[label] = fetch_nearby(
                    lat=lat,
                    lng=lng,
                    place_type=CATEGORIES[label],
                    radius_m=radius,
                    max_pages=pages,
                )
            # STORE DATA (NOT MAP) IN SESSION STATE
            st.session_state["categorized_results"] = categorized_results
            st.session_state["results_df"] = places_to_dataframe(categorized_results)
            st.session_state["meta"] = {
                "formatted_city": formatted_city,
                "lat": lat,
                "lng": lng,
            }

    except Exception as e:
        st.error(str(e))
        st.stop()
if "categorized_results" in st.session_state and "meta" in st.session_state:
    meta = st.session_state["meta"]

    city_map = build_map(
        meta["formatted_city"],
        (meta["lat"], meta["lng"]),
        st.session_state["categorized_results"]
    )

    col1, col2 = st.columns([1.3, 1])

    with col1:
        st.subheader("Map")
        st_folium(city_map, width=900, height=650, key="poi_map")

    with col2:
        st.subheader("Places")
        df = st.session_state["results_df"]
        st.caption(f"{len(df)} unique places")
        st.dataframe(df, use_container_width=True, height=650)

        st.download_button(
            "Download CSV",
            df.to_csv(index=False),
            file_name="places.csv",
            mime="text/csv",
        )
else:
    st.info("Enter a city and click **Find places**.")