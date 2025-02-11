from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from openai import OpenAI
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import time

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

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    for track_id in track_ids:
        try:
            track_info = sp.track(track_id)
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            track_details.append(f"{track_name}, {artist_name}")
            time.sleep(0.3)  # 200ms delay to avoid Spotify rate-limiting
        except Exception as e:
            track_details.append(f"Error fetching track {track_id}: {str(e)}")

    # Split track details into batches of 150 lines
    batch_size = 150
    batches = [track_details[i:i + batch_size] for i in range(0, len(track_details), batch_size)]

    # Process each batch with OpenAI API
    all_results = []
    for batch in batches:
        formatted_text = "\n".join(batch)
        prompt = f"""
        The following are song titles and artists extracted from Spotify links:
        ---
        {formatted_text}
        ---
        Analyze the songs and return the results in CSV format. Ensure that you have the Artist, Name of Song, and Language.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            analysis = response.choices[0].message.content
            all_results.append(analysis)
        except Exception as e:
            all_results.append(f"An error occurred: {str(e)}")

        # Add a delay between batches to avoid OpenAI rate limits
        time.sleep(10)  # 10-second delay between batches

    # Combine all batch results
    final_analysis = "\n".join(all_results)
    return render_template('analyze.html', analysis=final_analysis, user={"name": "User"})

if __name__ == '__main__':
    app.run(debug=True)