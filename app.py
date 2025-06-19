
from flask import Flask, request, redirect
import requests
from geopy.distance import geodesic
import pandas as pd
import os

app = Flask(__name__)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CALLBACK_URL = "https://yourappname.onrender.com/exchange_token"

TARGET_POINT = (39.1822403, -106.8761047)
RADIUS_METERS = 305  # 1000 ft
leaderboard = []

@app.route("/")
def authorize():
    auth_url = (
        f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}"
        f"&response_type=code&redirect_uri={CALLBACK_URL}"
        f"&approval_prompt=force&scope=activity:read"
    )
    return redirect(auth_url)

@app.route("/exchange_token")
def exchange_token():
    code = request.args.get("code")
    token_url = "https://www.strava.com/oauth/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    }
    res = requests.post(token_url, data=data)
    token_data = res.json()
    access_token = token_data["access_token"]
    athlete = token_data["athlete"].get("username") or token_data["athlete"]["firstname"]

    headers = {"Authorization": f"Bearer {access_token}"}
    acts = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=100", headers=headers).json()

    hits = 0
    for act in acts:
        stream_url = f"https://www.strava.com/api/v3/activities/{act['id']}/streams"
        params = {"keys": "latlng", "key_by_type": "true"}
        stream = requests.get(stream_url, headers=headers, params=params).json()
        if 'latlng' in stream:
            for point in stream['latlng']['data']:
                if geodesic(TARGET_POINT, tuple(point)).meters <= RADIUS_METERS:
                    hits += 1
                    break

    leaderboard.append({'athlete': athlete, 'visits': hits})
    return f"<h1>{athlete} has {hits} visits near the point!</h1><a href='/leaderboard'>View Leaderboard</a>"

@app.route("/leaderboard")
def show_leaderboard():
    df = pd.DataFrame(leaderboard).sort_values("visits", ascending=False)
    return df.to_html(index=False)

if __name__ == "__main__":
    app.run(debug=True)
