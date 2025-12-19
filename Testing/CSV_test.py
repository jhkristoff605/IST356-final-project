import pytest
import pandas as pd
import folium


from typing import List, Tuple
from dataclasses import dataclass
# Constants
CSV = "Files/Euro_city.csv"
REQUIRED_COLS = [
    "Country_from", "City_from", "Lat_from", "Long_from",
    "Country_to", "City_to", "Lat_to", "Long_to",
    "Distance_km", "Distance_mi"
]
@dataclass
class Stop:
    country: str
    city: str
    lat: float
    lon: float
    @property
    def coun_(self) -> str:
        return self.country
def validate_columns(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
def normalize_text_cols(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["Country_from", "City_from", "Country_to", "City_to"]:
        df[c] = df[c].astype(str).str.strip()
    return df
def get_origin_rows(df: pd.DataFrame, country: str, city: str) -> pd.DataFrame:
    return df[(df["Country_from"] == country) & (df["City_from"] == city)]
def pick_start_stop(df: pd.DataFrame, country: str, city: str) -> Stop:
    rows = get_origin_rows(df, country, city)
    if rows.empty:
        raise ValueError(f"No starting point found for {city}, {country}")
    row = rows.iloc[0]
    return Stop(
        country=row["Country_from"],
        city=row["City_from"],
        lat=float(row["Lat_from"]),
        lon=float(row["Long_from"])
    )
def get_leg_candidates(df: pd.DataFrame, origin: Stop) -> pd.DataFrame:
    return df[(df["Country_from"] == origin.country) & (df["City_from"] == origin.city)]
def select_leg_row(legs: pd.DataFrame, dest_country: str, dest_city: str) -> pd.Series:
    row = legs[(legs["Country_to"] == dest_country) & (legs["City_to"] == dest_city)]
    if row.empty:
        raise ValueError(f"No leg found to {dest_city}, {dest_country}")
    return row.iloc[0]
def add_leg(routes: List[dict], stops: List[Stop], row: pd.Series) -> Tuple[List[dict], List[Stop], Stop]:
    routes.append({c: row[c] for c in REQUIRED_COLS})
    new_stop = Stop(
        country=row["Country_to"],
        city=row["City_to"],
        lat=float(row["Lat_to"]),
        lon=float(row["Long_to"])
    )
    stops.append(new_stop)
    return routes, stops, new_stop

@pytest.fixture
def sample_df() -> pd.DataFrame:
    # A tiny, deterministic dataset with whitespace to test normalization too.
    data = [
        {
            "Country_from": "France ", "City_from": "Paris ",
            "Lat_from": 48.8566, "Long_from": 2.3522,
            "Country_to": "Netherlands", "City_to": "Amsterdam",
            "Lat_to": 52.3676, "Long_to": 4.9041,
            "Distance_km": 507.0, "Distance_mi": 315.0
        },
        {
            "Country_from": "Netherlands", "City_from": "Amsterdam",
            "Lat_from": 52.3676, "Long_from": 4.9041,
            "Country_to": "Germany", "City_to": "Berlin",
            "Lat_to": 52.5200, "Long_to": 13.4050,
            "Distance_km": 577.0, "Distance_mi": 359.0
        },
    ]
    df = pd.DataFrame(data)
    # Ensure all required columns exist
    for c in REQUIRED_COLS:
        assert c in df.columns
    return df


def test_validate_columns_ok(sample_df):
    validate_columns(sample_df)  # should not raise


def test_validate_columns_missing_raises(sample_df):
    bad = sample_df.drop(columns=["Distance_mi"])
    with pytest.raises(ValueError) as e:
        validate_columns(bad)
    assert "Missing columns" in str(e.value)


def test_normalize_text_cols_trims_whitespace(sample_df):
    df2 = normalize_text_cols(sample_df)
    assert df2.loc[0, "Country_from"] == "France"
    assert df2.loc[0, "City_from"] == "Paris"


def test_get_origin_rows_filters_correctly(sample_df):
    df2 = normalize_text_cols(sample_df)
    rows = get_origin_rows(df2, "France", "Paris")
    assert len(rows) == 1
    assert rows.iloc[0]["City_to"] == "Amsterdam"

def test_pick_start_stop_returns_coordinates(sample_df):
    df2 = normalize_text_cols(sample_df)
    start = pick_start_stop(df2, "France", "Paris")
    assert isinstance(start, Stop)
    assert start.city == "Paris"
    assert start.country == "France"
    assert abs(start.lat - 48.8566) < 1e-6
    assert abs(start.lon - 2.3522) < 1e-6

def test_pick_start_stop_raises_if_missing(sample_df):
    df2 = normalize_text_cols(sample_df)
    with pytest.raises(ValueError):
        pick_start_stop(df2, "Italy", "Rome")

def test_get_leg_candidates_returns_outbound_rows(sample_df):
    df2 = normalize_text_cols(sample_df)
    origin = pick_start_stop(df2, "France", "Paris")
    legs = get_leg_candidates(df2, origin)
    assert len(legs) == 1
    assert legs.iloc[0]["Country_to"] == "Netherlands"

def test_select_leg_row_finds_specific_destination(sample_df):
    df2 = normalize_text_cols(sample_df)
    origin = pick_start_stop(df2, "France", "Paris")
    legs = get_leg_candidates(df2, origin)
    row = select_leg_row(legs, "Netherlands", "Amsterdam")
    assert row["Distance_km"] == 507.0

def test_select_leg_row_raises_if_not_found(sample_df):
    df2 = normalize_text_cols(sample_df)
    origin = pick_start_stop(df2, "France", "Paris")
    legs = get_leg_candidates(df2, origin)
    with pytest.raises(ValueError):
        select_leg_row(legs, "Germany", "Berlin")


def test_add_leg_appends_route_and_stop_and_returns_new_origin(sample_df):
    df2 = normalize_text_cols(sample_df)
    start = pick_start_stop(df2, "France", "Paris")
    legs = get_leg_candidates(df2, start)
    row = select_leg_row(legs, "Netherlands", "Amsterdam")

    routes, stops, new_origin = add_leg(routes=[], stops=[start], row=row)

    assert len(routes) == 1
    assert len(stops) == 2
    assert new_origin.city == "Amsterdam"
    assert new_origin.country == "Netherlands"
