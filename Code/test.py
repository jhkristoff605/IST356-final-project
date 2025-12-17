import os
import time
import googlemaps as GM
import folium

GMAPS_KEY = "AIzaSyCTYnU0WUrcYaSe7I2a37Z4XD56-wrhj60"
gmaps = GM.Client(key=GMAPS_KEY)

CATEGORIES = {
    "Landmarks": "tourist_attraction",
    "Museums": "museum",
    "Parks": "park",
    "Restaurants": "restaurant",
    "Cafes": "cafe",
}

def geocode_city(city_name: str):
    res = gmaps.geocode(city_name)
    if not res:
        raise ValueError(f"Could not geocode city: {city_name}")
    loc = res[0]["geometry"]["location"]
    return loc["lat"], loc["lng"]

def fetch_nearby(lat, lng, place_type, radius_m=6000, max_pages=2):
    # Google returns up to 20 results per page; pagination uses next_page_token.
    out = []
    page_token = None

    for _ in range(max_pages):
        resp = gmaps.places_nearby(
            location=(lat, lng),
            radius=radius_m,
            type=place_type,
            page_token=page_token,
        )
        out.extend(resp.get("results", []))

        page_token = resp.get("next_page_token")
        if not page_token:
            break

        # token often needs a short delay before it becomes valid
        time.sleep(2)

    return out

def build_city_map(city_name: str, radius_m=6000):
    lat, lng = geocode_city(city_name)
    m = folium.Map(location=(lat, lng), zoom_start=13)

    folium.Marker(
        (lat, lng),
        tooltip=f"{city_name} (center)",
        popup=city_name,
    ).add_to(m)

    for label, place_type in CATEGORIES.items():
        places = fetch_nearby(lat, lng, place_type, radius_m=radius_m, max_pages=2)

        for p in places:
            gloc = p.get("geometry", {}).get("location")
            if not gloc:
                continue
            folium.Marker(
                (gloc["lat"], gloc["lng"]),
                tooltip=f"{p.get('name', 'Unknown')} [{label}]",
                popup=p.get("vicinity", p.get("formatted_address", "")),
            ).add_to(m)

    return m

# Example:
# m = build_city_map("Denver, CO", radius_m=8000)
# m.save("denver_things_to_do.html")
