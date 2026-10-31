import os
from dotenv import load_dotenv
from supabase import create_client
import requests
import time
import json

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
STEAM_API_KEY = os.getenv("STEAM_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials!")

if not STEAM_API_KEY:
    raise ValueError("Missing Steam API Key!")


# Connect to Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Connected to Supabase!")


##----------FUNCTIONS----------##

# Get Steam Games
def get_steam_catalogue(last_appid=None, max_results=1000):
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    input_data = {
        "include_games": True,
        "include_dlc": False,
        "include_software": False,
        "include_videos": False,
        "include_hardware": False,
        "max_results": max_results
    }

    if last_appid is not None:
        input_data["last_appid"] = last_appid

    params = {
        "key": STEAM_API_KEY,
        "input_json": json.dumps(input_data)
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json()["response"]



# Save Steam Catalogue to Supabase
def save_catalogue_to_supabase(apps):
    if not apps:
        print("No catalogue entries to save.")
        return

    records = [
        {
            "app_id": app["appid"],
            "name": app["name"],
            "app_type": app.get("type")
        }
    for app in apps
    if app.get("name")
]
    # Insert in batches of 500
    for i in range(0, len(records), 500):
        batch = records[i:i + 500]

        supabase.table("steam_apps").upsert(
            batch
        ).execute()

        print(f"Saved {len(batch)} catalogue entries.")


# Save Game to Database
def save_game_to_supabase(game):
    app_id = game["steam_appid"]

    # Extract pricing information
    price = game.get("price_overview", {})

    # Convert Steam data into our database format
    record = {
        "app_id": app_id,
        "name": game.get("name"),
        "type": game.get("type"),
        "short_description": game.get("short_description"),
        "developers": game.get("developers", []),
        "publishers": game.get("publishers", []),
        "genres": [
            genre["description"]
            for genre in game.get("genres", [])
        ],
        "header_image": game.get("header_image"),
        "release_date": game.get("release_date", {}).get("date"),
        "is_free": game.get("is_free", False),

        "currency": price.get("currency"),
        "initial_price": price.get("initial"),
        "final_price": price.get("final"),
        "discount_percent": price.get("discount_percent", 0)
    }

    # Insert or update the game
    response = (
        supabase
        .table("games")
        .upsert(record)
        .execute()
    )

    print(f"Successfully saved: {record['name']}")

# Preview Steam Games
def import_catalogue(max_pages=2):
    last_appid = None
    page = 0
    total_imported = 0

    while True:
        page += 1

        print(f"\nFetching catalogue page {page}...")

        response = get_steam_catalogue(
            last_appid=last_appid,
            max_results=1000
        )

        apps = response.get("apps", [])

        if not apps:
            break

        save_catalogue_to_supabase(apps)

        total_imported += len(apps)

        print(f"Retrieved {len(apps)} apps.")
        print(f"Total discovered: {total_imported}")

        if not response.get("have_more_results"):
            break

        last_appid = response.get("last_appid")

        if last_appid is None:
            print("Missing pagination ID. Stopping.")
            break

        # Temporary safety limit
        if max_pages is not None and page >= max_pages:
            print("Reached page limit.")
            break

    print(f"\nFinished! Processed {total_imported} catalogue entries.")



#----------End of Functions----------##


if __name__ == "__main__":
    import_catalogue(max_pages=2)