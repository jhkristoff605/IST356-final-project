import os
import sys
import types
import importlib
import pytest
import pandas as pd

from pathlib import Path
import importlib.util

# ----------------------------
# Minimal fakes so importing Streamlit app won't run UI
# ----------------------------
class _DummyCtx:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class _FakeStreamlit:
    def __init__(self):
        self.session_state = {}
        self.sidebar = _DummyCtx()

    def set_page_config(self, **kwargs): pass
    def title(self, *args, **kwargs): pass
    def header(self, *args, **kwargs): pass
    def divider(self, *args, **kwargs): pass
    def subheader(self, *args, **kwargs): pass
    def caption(self, *args, **kwargs): pass
    def dataframe(self, *args, **kwargs): pass
    def download_button(self, *args, **kwargs): pass
    def success(self, *args, **kwargs): pass
    def warning(self, *args, **kwargs): pass
    def error(self, *args, **kwargs): pass
    def info(self, *args, **kwargs): pass
    def stop(self): raise RuntimeError("st.stop() called")

    def spinner(self, *args, **kwargs): return _DummyCtx()
    def columns(self, *args, **kwargs): return (_DummyCtx(), _DummyCtx())

    def text_input(self, label, value=""): return value
    def multiselect(self, label, options, default=None): return default or []
    def slider(self, label, min_value, max_value, value, step=1): return value

    # IMPORTANT: make buttons return False so the app doesn't execute search logic at import time
    def button(self, label, type=None, on_click=None): return False

    def data_editor(self, df, **kwargs): return df

    def cache_resource(self, fn): return fn

    class column_config:
        class CheckboxColumn:
            def __init__(self, required=False):
                self.required = required


@pytest.fixture
def google_app(monkeypatch):
    """
    Imports Google_code.py safely (without launching Streamlit UI) and returns the module.
    """
    # Your code uses os.environ["GMAPS_KEY"] at import time
    monkeypatch.setenv("GMAPS_KEY", "FAKE_KEY_FOR_TESTS")

    # Fake streamlit
    fake_st = _FakeStreamlit()
    st_mod = types.ModuleType("streamlit")
    for name in dir(fake_st):
        if name.startswith("_"):
            continue
        setattr(st_mod, name, getattr(fake_st, name))
    st_mod.session_state = fake_st.session_state
    st_mod.sidebar = fake_st.sidebar
    st_mod.column_config = fake_st.column_config
    st_mod.cache_resource = fake_st.cache_resource

    # Fake streamlit_folium
    st_folium_mod = types.ModuleType("streamlit_folium")
    st_folium_mod.st_folium = lambda *args, **kwargs: {}

    # Fake googlemaps module just so import succeeds
    googlemaps_mod = types.ModuleType("googlemaps")
    class Client:
        def __init__(self, key): self.key = key
    googlemaps_mod.Client = Client

    sys.modules["streamlit"] = st_mod
    sys.modules["streamlit_folium"] = st_folium_mod
    sys.modules["googlemaps"] = googlemaps_mod

    # Re-import fresh each test
    if "Google_code" in sys.modules:
        del sys.modules["Google_code"]
    
    # Load Google_code.py from /code folder explicitly
    root = Path(__file__).resolve().parents[1]  # repo root
    google_path = root / "Code" / "Google_code.py"

    if not google_path.exists():
        raise FileNotFoundError(f"Expected Google_code.py at {google_path}")

    spec = importlib.util.spec_from_file_location("Google_code", google_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["Google_code"] = mod
    spec.loader.exec_module(mod)

    return mod


# ----------------------------
# Fixtures with tiny deterministic sample responses
# ----------------------------
@pytest.fixture
def sample_geocode_response():
    return [{
        "geometry": {"location": {"lat": 39.7392, "lng": -104.9903}},
        "formatted_address": "Denver, CO, USA"
    }]

@pytest.fixture
def sample_places_pages():
    # Simulate 2 pages of results
    return [
        {"results": [
            {
                "name": "Place A",
                "rating": 4.7,
                "user_ratings_total": 100,
                "vicinity": "Addr A",
                "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                "place_id": "id1",
            }
        ], "next_page_token": "TOKEN"},
        {"results": [
            {
                "name": "Place B",
                "rating": 4.9,
                "user_ratings_total": 200,
                "vicinity": "Addr B",
                "geometry": {"location": {"lat": 3.0, "lng": 4.0}},
                "place_id": "id2",
            }
        ]}
    ]


# ----------------------------
# Tests (same style as your teammate)
# ----------------------------
def test_geocode_city_success(google_app, monkeypatch, sample_geocode_response):
    class FakeGmaps:
        def geocode(self, city_name):
            return sample_geocode_response

    monkeypatch.setattr(google_app, "get_gmaps_client", lambda: FakeGmaps())

    lat, lng, formatted = google_app.geocode_city("Denver, CO")
    assert lat == 39.7392
    assert lng == -104.9903
    assert formatted == "Denver, CO, USA"


def test_geocode_city_empty_raises(google_app, monkeypatch):
    class FakeGmaps:
        def geocode(self, city_name):
            return []

    monkeypatch.setattr(google_app, "get_gmaps_client", lambda: FakeGmaps())

    with pytest.raises(ValueError):
        google_app.geocode_city("Fake City")


def test_fetch_nearby_paginates(google_app, monkeypatch, sample_places_pages):
    calls = {"i": 0}

    class FakeGmaps:
        def places_nearby(self, location, radius, type, page_token=None):
            resp = sample_places_pages[calls["i"]]
            calls["i"] += 1
            return resp

    monkeypatch.setattr(google_app, "get_gmaps_client", lambda: FakeGmaps())
    monkeypatch.setattr(google_app.time, "sleep", lambda _: None)  # avoid real delay

    out = google_app.fetch_nearby(
        lat=0.0, lng=0.0,
        place_type="restaurant",
        radius_m=1000,
        max_pages=3
    )

    assert len(out) == 2
    assert [p["place_id"] for p in out] == ["id1", "id2"]


def test_places_to_dataframe_dedup_and_sort(google_app):
    categorized = {
        "Restaurants": [
            {
                "name": "A",
                "rating": 4.7,
                "user_ratings_total": 100,
                "vicinity": "Addr A",
                "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                "place_id": "id1",
            },
            {
                "name": "B",
                "rating": 4.9,
                "user_ratings_total": 200,
                "vicinity": "Addr B",
                "geometry": {"location": {"lat": 3.0, "lng": 4.0}},
                "place_id": "id2",
            },
            {
                "name": "A duplicate",
                "rating": 4.0,
                "user_ratings_total": 50,
                "vicinity": "Addr A2",
                "geometry": {"location": {"lat": 1.0, "lng": 2.0}},
                "place_id": "id1",  # duplicate
            },
        ]
    }

    df = google_app.places_to_dataframe(categorized)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert set(df["place_id"]) == {"id1", "id2"}

    # Sorted by rating desc within category: B first
    assert df.iloc[0]["name"] == "B"


def test_build_map_returns_folium_map(google_app):
    categorized = {
        "Restaurants": [
            {"name": "A", "geometry": {"location": {"lat": 1.0, "lng": 2.0}}, "vicinity": "Addr"}
        ]
    }
    m = google_app.build_map("Test City", (0.0, 0.0), categorized)
    assert m.__class__.__name__ == "Map"
