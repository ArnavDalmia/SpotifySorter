from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from openai import OpenAI
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables
load_dotenv()
app = Flask(__name__)

# Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Initialize Spotify client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    # Get Spotify links from the form
    spotify_links = request.form.get('liked_songs', '').splitlines()

    # Extract track IDs from the links
    track_ids = [link.split("open.spotify.com/track/")[1].split("?")[0]
                 for link in spotify_links if "open.spotify.com/track/" in link]

    # Fetch track details from Spotify API
    track_details = []
    import time

    for track_id in track_ids:
        try:
            track_info = sp.track(track_id)
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            track_details.append(f"{track_name}, {artist_name}")
            time.sleep(0.2)  # 200ms delay to avoid rate-limiting
        except Exception as e:
            track_details.append(f"Error fetching track {track_id}: {str(e)}")


    # Format all track data into a single text block
    formatted_text = "\n".join(track_details)
    print(formatted_text)

    # Create a single request with all track data
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"""
The following are song titles and artists extracted from Spotify links:
---
{formatted_text}
---
Analyze the songs and return the results in CSV format. Ensure that you have the Artist, Name of Song, and Language
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        analysis = response.choices[0].message.content
    except Exception as e:
        analysis = f"An error occurred: {str(e)}"

    return render_template('analyze.html', analysis=analysis, user={"name": "User"})

if __name__ == '__main__':
    app.run(debug=True)
