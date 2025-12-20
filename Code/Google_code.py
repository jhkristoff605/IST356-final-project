import time
from typing import Dict, List, Tuple
import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
import googlemaps
# =====================================================
API_KEY= "AIzaSyCTYnU0WUrcYaSe7I2a37Z4XD56-wrhj60"
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
                "user_ratings_total": p.get("user_ratings_total"),
                "address": p.get("vicinity", p.get("formatted_address", "")),
                "lat": loc.get("lat"),
                "lng": loc.get("lng"),
                "place_id": p.get("place_id"),
            })
    df = pd.DataFrame(rows)
    if "place_id" in df.columns:
        df = df.drop_duplicates(subset="place_id")
    return df.sort_values(by=["category", "rating"], ascending=[True, False], na_position="last")
# =====================================================
if "saved_places" not in st.session_state:
    st.session_state["saved_places"] = pd.DataFrame(
        columns=["category", "name", "rating", "user_ratings_total", "address", "lat", "lng", "place_id"]
    )
if "end_mode" not in st.session_state:
    st.session_state["end_mode"] = False
# =====================================================
with st.sidebar:
    st.header("Search")
    city = st.text_input("City", "Denver, CO")
    selected_categories = st.multiselect(
        "Categories",
        list(CATEGORIES.keys()),
        default=["Landmarks / Attractions", "Restaurants"]
    )
    radius = st.slider("Search radius (meters)", 1000, 20000, 8000, step=500)
    pages = st.slider("Pages per category", 1, 3, 2)
    run_search = st.button("Find places", type="primary")
    clear_results = st.button("Clear results")
    clear_saved = st.button("Clear saved places")
    st.divider()
    end_btn = st.button("End (Preview saved)", type="secondary")
if clear_results:
    for key in ["categorized_results", "results_df", "meta"]:
        st.session_state.pop(key, None)
if clear_saved:
    st.session_state["saved_places"] = st.session_state["saved_places"].iloc[0:0]
    st.session_state["end_mode"] = False
if end_btn:
    st.session_state["end_mode"] = True
if run_search:
    st.session_state["end_mode"] = False  # leaving preview mode if they search again
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
if st.session_state["end_mode"]:
    st.subheader("Saved Places (Preview)")

    saved_df = st.session_state["saved_places"].copy()
    if saved_df.empty:
        st.info("You have not saved any places yet. Go back, check places to save, then click 'Save selected places'.")
    else:
        st.caption(f"{len(saved_df)} saved place(s)")
        st.dataframe(saved_df.drop(columns=["place_id"], errors="ignore"), use_container_width=True)

        st.download_button(
            "Download saved places as CSV",
            saved_df.to_csv(index=False),
            file_name="saved_places.csv",
            mime="text/csv",
        )
    st.divider()
    st.button("Back to search/results", on_click=lambda: st.session_state.update({"end_mode": False}))
    st.stop()
if "categorized_results" in st.session_state and "meta" in st.session_state and "results_df" in st.session_state:
    meta = st.session_state["meta"]
    results_df = st.session_state["results_df"].copy()
    # Add checkbox column for saving
    results_for_editor = results_df.copy()
    results_for_editor.insert(0, "Save", False)
    city_map = build_map(
        meta["formatted_city"],
        (meta["lat"], meta["lng"]),
        st.session_state["categorized_results"]
    )
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.subheader("Map")
        st_folium(city_map, width=900, height=650, key="poi_map")

    with col2:
        st.subheader("Results (check to save)")
        st.caption("Select places using the Save checkbox, then click “Save selected places.”")
        edited = st.data_editor(
            results_for_editor,
            use_container_width=True,
            height=520,
            hide_index=True,
            column_config={
                "Save": st.column_config.CheckboxColumn(required=False),
            },
            disabled=[c for c in results_for_editor.columns if c != "Save"],
            key="results_editor",
        )
        save_clicked = st.button("Save selected places", type="primary")

        if save_clicked:
            selected = edited[edited["Save"] == True].drop(columns=["Save"])
            if selected.empty:
                st.warning("No places selected. Check at least one box before saving.")
            else:
                current_saved = st.session_state["saved_places"]
                combined = pd.concat([current_saved, selected], ignore_index=True)
                if "place_id" in combined.columns:
                    combined = combined.drop_duplicates(subset="place_id", keep="first")

                st.session_state["saved_places"] = combined
                st.success(f"Saved {len(selected)} place(s). Total saved: {len(st.session_state['saved_places'])}")

        st.divider()
        st.caption(f"Currently saved: {len(st.session_state['saved_places'])} place(s).")
        st.caption("When finished, click **End (Preview saved)** in the sidebar.")
else:
    st.info("Enter a city and click **Find places**.")