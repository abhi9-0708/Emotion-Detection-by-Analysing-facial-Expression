from dotenv import load_dotenv
import os
import base64
from requests import post, get
import json
import urllib.parse

# Load environment variables
load_dotenv()

# Spotify API credentials
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# Emotion Mapping
emotion_dict = {
    0: "sad", 
    1: "fear", 
    2: "surprise", 
    3: "neutral", 
    4: "disgust", 
    5: "happy", 
    6: "angry"
}

# English Music Playlist IDs
english_music_dist = {
    0: "1n6cpWo9ant4WguEo91KZh",  # Sad
    1: "4cllEPvFdoX6NIVWPKai9I",  # Fear
    2: "4amvTpvtGLi5Vybl1bEDWV",  # Surprise
    3: "4kvSlabrnfRCQWfN0MgtgA",  # Neutral
    4: "1n6cpWo9ant4WguEo91KZh",  # Disgust
    5: "0deORnapZgrxFY4nsKr9JA",  # Happy
    6: "0l9dAmBrUJLylii66JOsHB",  # Angry
}

# Hindi Music Playlist IDs (Replace these with valid Spotify playlist IDs)
hindi_music_dist = {
    0: "37i9dQZF1DX5QfIRfEIfQJ",  # Sad (Replace with real Hindi playlist ID)
    1: "37i9dQZF1DX6QWgr6aC22U",  # Fear (Replace)
    2: "37i9dQZF1DX8G6uERfhfPM",  # Surprise (Replace)
    3: "37i9dQZF1DX0XUfTFmNBRM",  # Neutral (Replace)
    4: "37i9dQZF1DWVgSTa5nzg1k",  # Disgust (Replace)
    5: "37i9dQZF1DX0h0QnLkMBl4",  # Happy (Replace)
    6: "37i9dQZF1DX4sWSpwq3LiO",  # Angry (Replace)
}

# Podcast Show IDs for each emotion
podcast_dist = {
    0: "6z4NLXyHPgaaxGkHlPDTND",  # Sad - "The Tony Robbins Podcast"
    1: "4Y2CYvyTxKjbv3QtQI7vII",  # Fear - "Feel Better, Live More"
    2: "1wRGZlmaS1faQED6BGexI4",  # Surprise - "My Favorite Murder"
    3: "69ZUhdV0q2JtibNU2yLTpQ",  # Neutral - "The Daily"
    4: "4iIbt6RNiBOJer7uvjnnqA",  # Disgust - "The Minimalists Podcast"
    5: "6E709HRH7XaiZrMfgtNCun",  # Happy - "The Happiness Lab"
    6: "4a0jm50FkdZEvZUqh6DwEx"   # Angry - "Ten Percent Happier"
}

def get_token():
    """Get Spotify access token dynamically"""
    auth_string = client_id + ":" + client_secret
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")
    
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    result = post(url, headers=headers, data=data)

    if result.status_code != 200:
        print(f"❌ Failed Request (Status {result.status_code}):", result.text)
        return None

    json_result = json.loads(result.content)
    return json_result.get("access_token")

def get_track_details(playlist_id, token):
    """Fetch track details from a Spotify playlist"""
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch playlist (Status {response.status_code}):", response.text)
        return []

    data = response.json()
    tracks = []
    for item in data.get('items', []):
        track = item['track']
        query = f"{track['name']} {track['artists'][0]['name']} official video"
        youtube_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
        
        tracks.append({
            "type": "music",
            "name": track['name'],
            "artist": track['artists'][0]['name'],
            "spotify_url": track['external_urls']['spotify'],
            "youtube_url": youtube_url,
            "image": track['album']['images'][0]['url'] if track['album']['images'] else None
        })
    return tracks

def get_podcast_details(show_id, token):
    """Fetch podcast details from a Spotify show"""
    url = f"https://api.spotify.com/v1/shows/{show_id}/episodes?limit=5"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ Failed to fetch podcast (Status {response.status_code}):", response.text)
        return []

    data = response.json()
    podcasts = []
    for episode in data.get('items', []):
        podcasts.append({
            "type": "podcast",
            "name": episode.get('name', 'Unknown Episode'),
            "publisher": episode.get('show', {}).get('publisher', 'Unknown Publisher'),
            "description": episode.get('description', 'No description available'),
            "spotify_url": episode.get('external_urls', {}).get('spotify', '#'),
            "image": episode.get('images', [{}])[0].get('url', None),
            "release_date": episode.get('release_date', 'Unknown date')
        })
    return podcasts

def recommend_media(emotion_id):
    """Fetch both music (English + Hindi) and podcast recommendations based on emotion"""
    token = get_token()
    if not token:
        print("❌ Failed to get Spotify token.")
        return None

    english_playlist_id = english_music_dist.get(emotion_id, english_music_dist[3])
    hindi_playlist_id = hindi_music_dist.get(emotion_id, hindi_music_dist[3])

    english_tracks = get_track_details(english_playlist_id, token)[:5]
    hindi_tracks = get_track_details(hindi_playlist_id, token)[:5]

    show_id = podcast_dist.get(emotion_id, podcast_dist[3])
    podcasts = get_podcast_details(show_id, token)[:3]

    recommendations = {
        "emotion": emotion_dict[emotion_id],
        "music": english_tracks + hindi_tracks,  # 10 songs (5 English + 5 Hindi)
        "podcasts": podcasts
    }

    return recommendations

# Example usage
if __name__ == "__main__":
    emotion_id = 1  # Example: Fear
    recommendations = recommend_media(emotion_id)
