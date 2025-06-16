
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

# Music Playlist IDs for each emotion
music_dist = {
    0: "1n6cpWo9ant4WguEo91KZh",  # Sad
    1: "4cllEPvFdoX6NIVWPKai9I",  # Fearful
    2: "4amvTpvtGLi5Vybl1bEDWV",  # Surprised
    3: "4kvSlabrnfRCQWfN0MgtgA",  # Neutral
    4: "1n6cpWo9ant4WguEo91KZh",  # Disgusted
    5: "0deORnapZgrxFY4nsKr9JA",  # Happy
    6: "0l9dAmBrUJLylii66JOsHB",  # Angry
}

# Updated Podcast Show IDs for each emotion (working as of March 2025, designed to overcome emotions)
podcast_dist = {
    0: "6ZcvVBPQ2ToLXEWVbaw59P",  # Sad - "The Tony Robbins Podcast" (motivational and uplifting)
    1: "4Y2CYvyTxKjbv3QtQI7vII",  # Fear - "Feel Better, Live More" (overcoming fear and anxiety)
    2: "1wRGZlmaS1faQED6BGexI4",  # Surprise - "My Favorite Murder" (therapeutic storytelling)
    3: "69ZUhdV0q2JtibNU2yLTpQ",  # Neutral - "The Daily" (balanced news)
    4: "4iIbt6RNiBOJer7uvjnnqA",  # Disgust - "The Minimalists Podcast" (simplify life, counter disgust)
    5: "6E709HRH7XaiZrMfgtNCun",  # Happy - "The Happiness Lab" (reinforces positivity)
    6: "4a0jm50FkdZEvZUqh6DwEx"   # Angry - "Ten Percent Happier" (calming anger with mindfulness)
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
    token = json_result.get("access_token")

    if not token:
        print("❌ Token retrieval failed. Response:", json_result)
        return None
    
    return token

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
    for item in data['items']:
        track = item['track']
        # Construct YouTube search URL
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
    
    # Check if 'items' exists in the response
    if 'items' not in data:
        print("❌ No podcast episodes found in the response")
        return []
    
    for episode in data['items']:
        try:
            podcast_info = {
                "type": "podcast",
                "name": episode.get('name', 'Unknown Episode'),
                "publisher": episode.get('show', {}).get('publisher', 'Unknown Publisher'),
                "description": episode.get('description', 'No description available'),
                "spotify_url": episode.get('external_urls', {}).get('spotify', '#'),
                "image": episode.get('images', [{}])[0].get('url', None),
                "release_date": episode.get('release_date', 'Unknown date')
            }
            podcasts.append(podcast_info)
        except Exception as e:
            print(f"❌ Error processing podcast episode: {e}")
            continue
    
    return podcasts

def recommend_media(emotion_id):
    """Fetch both music and podcast recommendations based on emotion"""
    token = get_token()
    if not token:
        print("❌ Failed to get Spotify token.")
        return None

    # Get music recommendations
    playlist_id = music_dist.get(emotion_id, music_dist[3])  # Default to neutral
    tracks = get_track_details(playlist_id, token)
    
    # Get podcast recommendations
    show_id = podcast_dist.get(emotion_id, podcast_dist[3])  # Default to neutral
    podcasts = get_podcast_details(show_id, token)

    if not tracks and not podcasts:
        print("❌ No recommendations found.")
        return None

    # Combine and return results
    recommendations = {
        "emotion": emotion_dict[emotion_id],
        "music": tracks[:5],  # Return top 5 tracks
        "podcasts": podcasts[:3]  # Return top 3 podcast episodes
    }

    # Print results for debugging
    print(f"\n🎵 Recommended {emotion_dict[emotion_id]} Music:")
    for i, track in enumerate(recommendations['music'], 1):
        print(f"{i}. {track['name']} - {track['artist']}")

    print(f"\n🎙️ Recommended {emotion_dict[emotion_id]} Podcasts:")
    for i, podcast in enumerate(recommendations['podcasts'], 1):
        print(f"{i}. {podcast['name']} - {podcast['publisher']}")

    return recommendations

# Example usage
if __name__ == "__main__":
    # Test with a specific emotion (e.g., Angry)
    emotion_id =0# Angry
    recommendations = recommend_media(emotion_id)

