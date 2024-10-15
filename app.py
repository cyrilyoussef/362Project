from flask import Flask, redirect, request, session, url_for, render_template
import requests
import base64
import os
from urllib.parse import urlencode
from collections import Counter
import webbrowser
import threading
import time

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Spotify API credentials
CLIENT_ID = "2447b4ad00f2495788be95c6146cd455"
CLIENT_SECRET = "13ce0cabb83a4fe582df33c5449d83bb"
REDIRECT_URI = "http://localhost:8888/callback"

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
SCOPE = "user-top-read user-read-private"

def get_auth_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "show_dialog": "true"  # Always show login dialog
    }
    return f"{SPOTIFY_AUTH_URL}/?{urlencode(params)}"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = get_auth_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    if not auth_code:
        return redirect(url_for('index'))

    # Request Access Token
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode())
    headers = {
        "Authorization": f"Basic {auth_header.decode()}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=data)
    response_data = response.json()

    session['access_token'] = response_data.get("access_token")
    session['refresh_token'] = response_data.get("refresh_token")
    session['token_expires_in'] = response_data.get("expires_in")
    
    return redirect(url_for('choose_time_range'))

@app.route('/choose-time-range')
def choose_time_range():
    return render_template('choose_time_range.html')

@app.route('/top-items', methods=["POST"])
def top_items():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    time_range = request.form.get('time_range', 'medium_term')

    headers = {"Authorization": f"Bearer {session['access_token']}"}
    params = {"time_range": time_range, "limit": 5}

    # Get Top Artists
    response_artists = requests.get(f"{SPOTIFY_API_URL}/me/top/artists", headers=headers, params=params)
    top_artists = response_artists.json().get('items', [])
    
    # Collect Genres from Artists
    genres = []
    for artist in top_artists:
        genres.extend(artist.get('genres', []))
    
    # Get Top Tracks
    response_tracks = requests.get(f"{SPOTIFY_API_URL}/me/top/tracks", headers=headers, params=params)
    top_tracks = response_tracks.json().get('items', [])

    # Calculate Listening Time
    total_listening_time = sum([track['duration_ms'] for track in top_tracks]) // 60000  # Convert ms to minutes

    # Get Recommendations based on top tracks and artists
    seed_artists = ','.join([artist['id'] for artist in top_artists[:2]])  # Use 2 top artists
    seed_tracks = ','.join([track['id'] for track in top_tracks[:2]])  # Use 2 top tracks
    recommendations = requests.get(f"{SPOTIFY_API_URL}/recommendations",
                                   headers=headers,
                                   params={"seed_artists": seed_artists, "seed_tracks": seed_tracks, "limit": 5})
    recommended_tracks = recommendations.json().get('tracks', [])

    # Get top 3 genres
    top_genres = [genre for genre, count in Counter(genres).most_common(3)]

    return render_template('callback.html',
                           artists=top_artists,
                           tracks=top_tracks,
                           genres=top_genres,
                           listening_time=total_listening_time,
                           recommendations=recommended_tracks)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def open_browser():
    """Function to open the web browser after a short delay."""
    time.sleep(1)  # Wait a moment for the server to start
    webbrowser.open_new("http://localhost:8888/")

if __name__ == '__main__':
    # Start a thread to open the browser
    threading.Thread(target=open_browser).start()
    # Run the Flask app
    app.run(port=8888, debug=True, use_reloader=False)
