from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from openai import OpenAI
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.oauth2 import SpotifyOAuth
import time
import csv

# Load environment variables
load_dotenv()
app = Flask(__name__)

# API creds
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SCOPE = "playlist-modify-private user-read-private"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://localhost/"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIFY_CLIENT_ID,
                                               client_secret=SPOTIFY_CLIENT_SECRET,
                                               redirect_uri=REDIRECT_URI,
                                               scope=SCOPE))
user_id = sp.current_user()['id']


def clean():
    with open('newSorted.csv', 'r') as file:
        content = file.read()
    content = content.strip().strip('"')
    lines = content.splitlines()

    clean_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith("```"):
            continue
        if line.startswith("track_id"):
            continue
        clean_lines.append(line)

    #writing cleaned csv
    with open('cleaned.csv', 'w', newline='') as outfile:
        outfile.write("track_id, language" + "\n")

    with open('cleaned.csv', 'w', newline='') as outfile:
        for line in clean_lines:
            outfile.write(line + "\n")
    print("Cleaned CSV")

def playlist():
    track_ids = []
    with open('cleaned.csv', mode ='r')as file:
        csvFile = csv.reader(file)
        for lines in csvFile:
            track_ids.append(lines[0])
    print(track_ids)

    playlist_name = "Special Playlist Numero Uno"
    playlist_description = "This playlist contains the songs from my Liked Songs that I can't be bothered to sort"
    playlist = sp.user_playlist_create(user=user_id, name=playlist_name, public=False, description=playlist_description)
    playlist_id = playlist['id']
    print(f"Created playlist {playlist_name} with ID {playlist_id}")
    sp.playlist_add_items(playlist_id, track_ids)
    print("Tracks added to the playlist!")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    diff = request.form.get('diff', '')
    spotify_links = request.form.get('liked_songs', '').splitlines()
    track_ids = [link.split("open.spotify.com/track/")[1].split("?")[0]
                 for link in spotify_links if "open.spotify.com/track/" in link]

    track_details = []
    for track_id in track_ids:
        try:
            track_info = sp.track(track_id)
            track_name = track_info['name']
            artist_name = track_info['artists'][0]['name']
            track_details.append(f"{track_id}, {track_name}, {artist_name}")
            time.sleep(0.3)  #delay for Spotify rate-limiting
        except Exception as e:
            track_details.append(f"Error fetching track {track_id}: {str(e)}")

    # Batching of 150 lines for defeating rate limiting
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
        Analyze the songs and return the results in CSV format. Provide the track id once again, and the determined Language in that order. (track_id, language)
        
        Only provide the results that correspond to the users choice given in {diff}. This can be something like the language of choice or even a genre. If nothing is given in this, then simply don't filter anything and return all the songs given.

        In your output start directly with the headers, skip any descriptions or anything, the first character I should see is t from track_id.
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

        #delay between batches for OpenAI rate limitinhg
        time.sleep(10)

    # Combine all batch results
    final_analysis = "\n".join(all_results)

    with open('newSorted.csv', 'w', newline='') as csvfile:
        csvfile.write(final_analysis)

    clean() #cleaned csv into cleaned.csv
    # now just need to parse this and create a playlist

    #playlist()
    #final = "WOW your playlist has been made, go check it out! "

    return render_template('analyze.html', analysis = final_analysis, user={"name": "User"})


if __name__ == '__main__':
    app.run(debug=True)