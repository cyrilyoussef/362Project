import os

class Config:
    CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "2447b4ad00f2495788be95c6146cd455")
    CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "13ce0cabb83a4fe582df33c5449d83bb")
    REDIRECT_URI = "http://localhost:8888/callback"
    SCOPE = "user-top-read user-read-private"
