from dotenv import load_dotenv
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import requests
import time
import csv
from datetime import datetime
from flask import Flask, request, jsonify
import threading
import unicodedata

# ---------------- SPOTIFY AUTH ----------------

load_dotenv(dotenv_path=r"C:\Users\Dhruv Gummala\Desktop\Spotify\Credentials.env")

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-playback-state user-read-currently-playing"
))

# ---------------- WEATHER ----------------

def get_weather_description(lat=47.3769, lon=8.5417):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    response = requests.get(url)
    data = response.json()

    if "current_weather" not in data:
        return "Unknown"

    code = data["current_weather"]["weathercode"]

    weather_map = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Cloudy",
        45: "Fog", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
        55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 80: "Rain showers",
        81: "Moderate showers", 82: "Violent showers", 95: "Thunderstorm", 99: "Hailstorm"
    }

    return weather_map.get(code, "Unknown")

# ---------------- LOCATION SERVER ----------------

app = Flask(__name__)
latest_location = {}

def replace_umlauts(text: str) -> str:
    """Convert German umlauts to ASCII equivalents."""
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "ß": "ss"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def reverse_geocode(lat, lon):
    """Return address as 'road house_number, postcode (city)' with umlauts replaced."""
    try:
        if lat is None or lon is None:
            return "Unknown address"

        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "SpotifyMoodLogger/1.0"}
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'

        data = response.json().get("address", {})

        road = data.get("road") or data.get("footway") or data.get("pedestrian") or ""
        house_number = data.get("house_number") or ""
        postcode = data.get("postcode") or ""
        city = (
            data.get("city") or data.get("town") or data.get("village") or
            data.get("municipality") or data.get("hamlet") or ""
        )

        # Normalize unicode
        road = unicodedata.normalize("NFC", road)
        house_number = unicodedata.normalize("NFC", house_number)
        postcode = unicodedata.normalize("NFC", postcode)
        city = unicodedata.normalize("NFC", city)

        # Replace umlauts
        road = replace_umlauts(road)
        house_number = replace_umlauts(house_number)
        city = replace_umlauts(city)

        # Format as: "road house_number, postcode (city)"
        line1 = " ".join(filter(None, [road, house_number]))
        line2 = f"{postcode} ({city})" if postcode or city else ""
        full_address = ", ".join(filter(None, [line1, line2]))

        return full_address or "Unknown address"

    except Exception:
        return "Unknown address"

# ---------------- FLASK ROUTES ----------------

@app.route("/location", methods=["POST"])
def receive_location():
    global latest_location
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    latest_location = {
        "lat": data.get("lat"),
        "lon": data.get("lon"),
        "device_id": data.get("device_id"),
        "timestamp": data.get("timestamp"),
        "address": reverse_geocode(data.get("lat"), data.get("lon"))
    }

    return jsonify({"status": "ok"}), 200

@app.route("/location/latest", methods=["GET"])
def get_latest_location():
    if not latest_location:
        return jsonify({"error": "No location yet"}), 404
    return jsonify(latest_location), 200

# Start Flask server in a background thread
def start_flask():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=start_flask, daemon=True).start()

# ---------------- FETCH LATEST LOCATION ----------------

def fetch_latest_location():
    try:
        resp = requests.get("http://172.20.10.4:5000/location/latest", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            lat = data.get("lat")
            lon = data.get("lon")
            address = data.get("address") or "Unknown address"
            return lat, lon, address
    except Exception as e:
        print("Error fetching location:", e)
    return None, None, "Unknown address"

# ---------------- CSV SETUP ----------------

csv_file = "mood_logger.csv"
if not os.path.exists(csv_file):
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Song", "Artist", "Weather", "Latitude", "Longitude", "Address"])

# ---------------- MAIN LOOP ----------------

print("Starting Spotify mood logger...")
last_song_id = None

while True:
    try:
        current_track = sp.current_playback()
        if current_track and current_track["is_playing"]:
            track_id = current_track["item"]["id"]
            if track_id != last_song_id:
                song = current_track["item"]["name"]
                artist = current_track["item"]["artists"][0]["name"]

                weather = get_weather_description()
                lat, lon, address = fetch_latest_location()

                with open(csv_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.now().isoformat(), song, artist, weather, lat, lon, address])

                print(f"Logged: {song} - {artist} | Weather: {weather} | Address: {address}")
                last_song_id = track_id
        else:
            last_song_id = None

    except Exception as e:
        print("Error:", e)

    time.sleep(30)
