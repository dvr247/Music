from dotenv import load_dotenv
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import requests
import time
import csv
from datetime import datetime

# Loading Spotipy Credentials

load_dotenv(dotenv_path=r"C:\Users\Dhruv Gummala\Desktop\Spotify\Credentials.env")

client_id = os.getenv("SPOTIPY_CLIENT_ID")
client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI")

# Spotify Authentication

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI"),
    scope="user-read-playback-state user-read-currently-playing"
))

# Test: print current playback
current_track = sp.current_playback()

if current_track and current_track["is_playing"]:
    song = current_track["item"]["name"]
    artist = current_track["item"]["artists"][0]["name"]
    
else:
    print("No song is currently playing.")
    
# Weather Info

import requests

def get_weather_description(lat=47.3769, lon=8.5417):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    response = requests.get(url)
    data = response.json()
    
    if "current_weather" not in data:
        return "Unknown"

    code = data["current_weather"]["weathercode"]
    
    if code is None:
        return "Unknown"

    weather_map = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Cloudy",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Moderate showers",
        82: "Violent showers",
        95: "Thunderstorm",
        99: "Hailstorm"
    }

    return weather_map.get(code, "Unknown")

weather = get_weather_description()

# Create Database
    
csv_file = "mood_logger.csv"

if not os.path.exists(csv_file):
    with open(csv_file, "w", newline = "", encoding = "utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Song", "Artist", "Weather"])
        
# Poll Spotify

print("Starting to monitor Spotify ...")
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
                
                # Append to CSV
                
                with open(csv_file, "a", newline="", encoding="utf-8") as f:
                    writer  = csv.writer(f)
                    writer.writerow([datetime.now().isoformat(), song, artist, weather])
                    
                print(f"Logged: {song} - {artist} | Weather: {weather}")
                last_song_id = track_id
                
        else:
    
            last_song_id = None
    
    except Exception as e:
    
        print("Error:", e)
    
    time.sleep(30)
