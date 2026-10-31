import os
from dotenv import load_dotenv
from supabase import create_client
import requests

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials!")

# Connect to Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Connected to Supabase!")


##----------Functions----------##

def get_steam_game(app_id):
    url = "https://store.steampowered.com/api/appdetails"

    params = {
        "appids": app_id,
        "cc": "gb",
        "l": "en"
    }

    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()

    game_data = data.get(str(app_id), {})

    if not game_data.get("success"):
        print(f"Could not retrieve game {app_id}")
        return None

    return game_data["data"]

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

#----------End of Functions----------##

# Test importing Counter-Strike 2
game = get_steam_game(730)

if game:
    save_game_to_supabase(game)
