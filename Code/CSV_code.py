import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static

CSV = "Files/Euro_city.csv"
COLS = ["Country_from","City_from","Lat_from","Long_from",
        "Country_to","City_to","Lat_to","Long_to","Distance_km","Distance_mi"]
st.set_page_config(page_title="Euro Route Picker + Map", layout="wide")
st.title("European Route Picker+ Folium Map")
@st.cache_data
def load_df():
    df = pd.read_csv(CSV)
    miss = [c for c in COLS if c not in df.columns]
    if miss: raise ValueError(f"Missing columns: {miss}")
    for c in ["Country_from","City_from","Country_to","City_to"]:
        df[c] = df[c].astype(str).str.strip()
    return df
ss = st.session_state
ss.setdefault("routes", [])
ss.setdefault("stops", [])          # list of {"country","city","lat","lon"}
ss.setdefault("origin", None)       # {"country","city","lat","lon"}
ss.setdefault("final", False)
df = load_df()
def reset():
    ss.routes, ss.stops, ss.origin, ss.final = [], [], None, False
def build_map(stops):
    pts = [(float(s["lat"]), float(s["lon"])) for s in stops]
    m = folium.Map(location=pts[0], zoom_start=5)
    for i, s in enumerate(stops, 1):
        loc = (float(s["lat"]), float(s["lon"]))
        folium.Marker(
            loc,
            popup=f"{i}. {s['city']}, {s['country']}",
            tooltip=f"{i}. {s['city']}",
            icon=folium.Icon(color="red" if i == 1 else ("green" if i == len(stops) else "blue"))
        ).add_to(m)
    if len(pts) >= 2:
        folium.PolyLine(pts, weight=4, opacity=0.8).add_to(m)
        m.fit_bounds(pts)
    return m

# ---------- FINAL: map only here ----------
if ss.final:
    st.subheader("Trip locked – route + map")
    out = pd.DataFrame(ss.routes)
    st.dataframe(out[["Country_from","City_from","Country_to","City_to","Distance_km","Distance_mi"]],
                 use_container_width=True)
    st.metric("Total km", f"{out['Distance_km'].sum():,.1f}")
    st.metric("Total mi", f"{out['Distance_mi'].sum():,.1f}")

    if len(ss.stops) >= 1:
        folium_static(build_map(ss.stops), width=900, height=550)

    st.download_button("Download finalized_trip.csv",
                       out.to_csv(index=False).encode(),
                       "finalized_trip.csv", "text/csv")
    if st.button("Reset"):
        reset(); st.rerun()
    st.stop()

# ---------- START CITY: require explicit confirmation ----------
if ss.origin is None:
    st.subheader("Step 1: Set your starting city (required)")
    with st.form("start_form", clear_on_submit=False):
        c0 = st.selectbox("Country_from", sorted(df.Country_from.unique()), index=None,
                          placeholder="Select a country")
        city0 = None
        if c0:
            city0 = st.selectbox("City_from", sorted(df[df.Country_from == c0].City_from.unique()), index=None,
                                 placeholder="Select a city")
        start = st.form_submit_button("Set starting city", type="primary")

    if start:
        if not c0 or not city0:
            st.warning("Please select both a Country_from and a City_from.")
        else:
            row0 = df[(df.Country_from == c0) & (df.City_from == city0)].iloc[0]
            origin = {"country": c0, "city": city0,
                      "lat": float(row0["Lat_from"]), "lon": float(row0["Long_from"])}
            ss.origin = origin
            ss.stops = [origin]   # FIRST STOP is the user-chosen city (no defaults)
            st.rerun()

    st.stop()

# ---------- ROUTE PICKING----------
origin = ss.origin
st.info(f"Current start: **{origin['city']}, {origin['country']}**")

leg_df = df[(df.Country_from == origin["country"]) & (df.City_from == origin["city"])]
if leg_df.empty:
    st.warning("No outbound routes found from this starting city in the dataset.")
    if st.button("Reset"):
        reset(); st.rerun()
    st.stop()
st.subheader("Step 2: Add next destination(s)")
ct = st.selectbox("Country_to", sorted(leg_df.Country_to.unique()), index=None, placeholder="Select a destination country")
if ct:
    ct_df = leg_df[leg_df.Country_to == ct]
    cityt = st.selectbox("City_to", sorted(ct_df.City_to.unique()), index=None, placeholder="Select a destination city")
else:
    ct_df, cityt = None, None

c1, c2, c3 = st.columns([1,1,2])

with c1:
    if st.button("Add route", type="primary", disabled=not (ct and cityt)):
        row = ct_df[ct_df.City_to == cityt].iloc[0]
        ss.routes.append({c: row[c] for c in COLS})

        dest = {"country": ct, "city": cityt,
                "lat": float(row["Lat_to"]), "lon": float(row["Long_to"])}
        ss.stops.append(dest)
        ss.origin = dest  # chain
        st.rerun()

with c2:
    if st.button("Finish trip", disabled=(len(ss.routes) == 0)):
        ss.final = True
        st.rerun()

with c3:
    st.write(f"Legs selected: **{len(ss.routes)}**")

if ss.routes:
    st.subheader("Current trip legs")
    st.dataframe(pd.DataFrame(ss.routes)[["Country_from","City_from","Country_to","City_to","Distance_km"]],
                 use_container_width=True)

if st.button("Reset"):
    reset(); st.rerun()
