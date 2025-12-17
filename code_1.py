import os
import sys
import pandas as pd
CSV_FILE = "Euro_city.csv"

REQUIRED_COLS = [
    "Country_from", "City_from", "Lat_from", "Long_from",
    "Country_to", "City_to", "Lat_to", "Long_to",
    "Distance_km", "Distance_mi"
]


def normalize(s: str) -> str:
    return str(s).strip()


def load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Could not find '{path}' in:\n  {os.getcwd()}")

    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    # Normalize text columns for consistent matching
    df["Country_from"] = df["Country_from"].map(normalize)
    df["City_from"] = df["City_from"].map(normalize)
    df["Country_to"] = df["Country_to"].map(normalize)
    df["City_to"] = df["City_to"].map(normalize)
    return df


def choose_from_list(options, title: str) -> str:
    """
    Displays a numbered menu and returns the chosen option (exact string).
    Allows:
      - entering a number
      - entering text to filter (case-insensitive), then re-prompts
    """
    options = sorted(set([o for o in options if str(o).strip() != ""]))
    if not options:
        raise ValueError(f"No options available for: {title}")

    filtered = options

    while True:
        print(f"\n{title}")
        print("-" * len(title))

        max_show = min(len(filtered), 40)
        for i in range(max_show):
            print(f"{i+1:>3}. {filtered[i]}")
        if len(filtered) > max_show:
            print(f"... (showing first {max_show} of {len(filtered)})")

        user = input("\nEnter number OR type to filter (blank = show all): ").strip()

        if user == "":
            filtered = options
            continue

        if user.isdigit():
            idx = int(user) - 1
            if 0 <= idx < len(filtered):
                return filtered[idx]
            print("Invalid number. Try again.")
            continue

        # filter by substring
        q = user.lower()
        filtered2 = [o for o in options if q in o.lower()]
        if not filtered2:
            print("No matches. Try a different filter.")
            continue
        filtered = filtered2


def yes_no(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print("Please enter y/n.")


def main():
    try:
        df = load_data(CSV_FILE)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Loaded {len(df):,} rows from '{CSV_FILE}'.")

    # ---- Pick origin: Country_from -> City_from
    country_from = choose_from_list(df["Country_from"].unique(), "Select Country_from")
    df_from_country = df[df["Country_from"] == country_from]

    city_from = choose_from_list(df_from_country["City_from"].unique(), f"Select City_from in {country_from}")
    df_origin = df_from_country[df_from_country["City_from"] == city_from]

    # ---- Pick one or more destinations
    results = []
    while True:
        country_to = choose_from_list(df_origin["Country_to"].unique(), "Select Country_to")
        df_to_country = df_origin[df_origin["Country_to"] == country_to]

        city_to = choose_from_list(df_to_country["City_to"].unique(), f"Select City_to in {country_to}")

        match = df_to_country[df_to_country["City_to"] == city_to]

        if match.empty:
            print("\nNo matching route found for that selection (unexpected).")
        else:
            # Often there should be exactly 1 row; if multiple, keep them all.
            for _, row in match.iterrows():
                results.append(row.to_dict())

            km = match["Distance_km"].iloc[0]
            mi = match["Distance_mi"].iloc[0]
            print(f"\nRoute: {city_from}, {country_from}  ->  {city_to}, {country_to}")
            print(f"Distance: {km} km  |  {mi} mi")

        if not yes_no("\nAdd another destination city (y/n)? "):
            break

    # ---- Output results
    if results:
        out_df = pd.DataFrame(results)[REQUIRED_COLS]
        print("\nSelected routes:")
        show_cols = ["Country_from", "City_from", "Country_to", "City_to", "Distance_km", "Distance_mi"]
        print(out_df[show_cols].to_string(index=False))

        out_file = "selected_routes.csv"
        out_df.to_csv(out_file, index=False)
        print(f"\nSaved to '{out_file}'.")
    else:
        print("\nNo routes selected. Nothing saved.")


if __name__ == "__main__":
    main()
