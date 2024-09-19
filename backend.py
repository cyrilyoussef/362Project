import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Spotify Developer credentials
SPOTIPY_CLIENT_ID = '2447b4ad00f2495788be95c6146cd455'
SPOTIPY_CLIENT_SECRET = '13ce0cabb83a4fe582df33c5449d83bb'
SPOTIPY_REDIRECT_URI = 'http://127.0.0.1:9090'

# Scope needed for the app to access user's top artists, tracks and recommendations
scope = "user-top-read"

# Authenticate the user
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope=scope))

# Function to get top artists, tracks, and genres
def get_top_data(time_range='medium_term', limit=5):
    # Get top artists
    top_artists = sp.current_user_top_artists(time_range=time_range, limit=limit)
    artists = [artist['name'] for artist in top_artists['items']]
    
    # Get top tracks
    top_tracks = sp.current_user_top_tracks(time_range=time_range, limit=limit)
    tracks = [track['name'] for track in top_tracks['items']]
    
    # Get genres from top artists
    genres = set()
    for artist in top_artists['items']:
        genres.update(artist['genres'])
    genres = list(genres)[:limit]
    
    return artists, tracks, genres

# Function to recommend songs based on user's top tracks
def recommend_songs(time_range='medium_term', limit=5):
    top_tracks = sp.current_user_top_tracks(time_range=time_range, limit=limit)
    top_track_ids = [track['id'] for track in top_tracks['items']]
    
    # Recommend songs based on top tracks
    recommendations = sp.recommendations(seed_tracks=top_track_ids[:2], limit=limit)
    recommended_songs = [track['name'] for track in recommendations['tracks']]
    
    return recommended_songs

# Helper function to print top data and recommendations
def display_user_data(time_range, label):
    print(f"--- {label} ---")
    artists, tracks, genres = get_top_data(time_range)
    print(f"Top Artists: {', '.join(artists)}")
    print(f"Top Songs: {', '.join(tracks)}")
    print(f"Top Genres: {', '.join(genres)}")
    
    recommended_songs = recommend_songs(time_range)
    print(f"Recommended Songs: {', '.join(recommended_songs)}")
    print("\n")

if __name__ == "__main__":
    # Display user data for different time ranges
    display_user_data('short_term', "Top Data (1 Month)")
    display_user_data('medium_term', "Top Data (6 Months)")
    display_user_data('long_term', "Top Data (12 Months)")
