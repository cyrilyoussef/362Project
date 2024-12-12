from flask import Flask, redirect, request, session, url_for, render_template, jsonify
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
SCOPE = "user-top-read user-read-private playlist-modify-public playlist-modify-private"

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

@app.route('/add-to-playlist', methods=["POST"])
def add_to_playlist():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    headers = {"Authorization": f"Bearer {session['access_token']}"}
    track_uri = request.form.get('track_uri')
    playlist_id = request.form.get('playlist_id')

    # Ensure both track_uri and playlist_id are provided
    if track_uri and playlist_id:
        # Add the track to the selected playlist
        add_url = f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks"
        response = requests.post(add_url, headers=headers, json={"uris": [track_uri]})

        if response.status_code == 201:
            return "Track added successfully!"
        else:
            return f"Failed to add track: {response.status_code}", response.status_code
    else:
        return "Track URI or Playlist ID missing", 400

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

    # Get user's playlists
    response_playlists = requests.get(f"{SPOTIFY_API_URL}/me/playlists", headers=headers)
    playlists = response_playlists.json().get('items', [])

    # Get top 5 genres
    top_genres = [genre for genre, count in Counter(genres).most_common(5)]

    return render_template('callback.html',
                           artists=top_artists,
                           tracks=top_tracks,
                           genres=top_genres,
                           playlists=playlists)

@app.route('/get_album_tracks/<album_id>')
def get_album_tracks(album_id):
    # Use the access token from the session
    if 'access_token' not in session:
        return redirect(url_for('login'))

    access_token = session['access_token']
    SPOTIFY_BASE_URL = "https://api.spotify.com/v1"
    
    # Call Spotify API to get album tracks
    url = f"{SPOTIFY_BASE_URL}/albums/{album_id}/tracks"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Return track data as JSON
        data = response.json()
        tracks = [
            {"name": track["name"], "uri": track["uri"]}
            for track in data.get("items", [])
        ]
        return jsonify(tracks)
    else:
        # Handle errors
        return jsonify({"error": "Unable to fetch tracks"}), response.status_code
@app.route('/search', methods=["POST", "GET"])
def search():
    if 'access_token' not in session:
        return redirect(url_for('login'))

    headers = {"Authorization": f"Bearer {session['access_token']}"}
    query = request.form.get('query', '')
    search_type = request.form.get('search_type', 'track')

    # Fetch user playlists
    response_playlists = requests.get(f"{SPOTIFY_API_URL}/me/playlists", headers=headers)
    playlists = response_playlists.json().get('items', [])

    items = []
    if query:
        # Search Spotify for tracks, albums, or artists
        search_url = f"{SPOTIFY_API_URL}/search"
        params = {"q": query, "type": search_type, "limit": 5}
        response_search = requests.get(search_url, headers=headers, params=params)
        result = response_search.json()

        # Get the relevant search result
        if search_type == 'track':
            items = result.get('tracks', {}).get('items', [])
        elif search_type == 'album':
            items = result.get('albums', {}).get('items', [])
            # Fetch tracks for each album
            for album in items:
                album_id = album['id']
                response_album_tracks = requests.get(f"{SPOTIFY_API_URL}/albums/{album_id}/tracks", headers=headers)
                album_tracks = response_album_tracks.json().get('items', [])
                album['tracks'] = album_tracks
        elif search_type == 'artist':
            items = result.get('artists', {}).get('items', [])
            # Fetch top tracks for each artist
            for artist in items:
                artist_id = artist['id']
                response_artist_tracks = requests.get(f"{SPOTIFY_API_URL}/artists/{artist_id}/top-tracks", params={"country": "US"}, headers=headers)
                artist_tracks = response_artist_tracks.json().get('tracks', [])
                artist['top_tracks'] = artist_tracks

    return render_template('search.html', query=query, search_type=search_type, items=items, playlists=playlists)

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