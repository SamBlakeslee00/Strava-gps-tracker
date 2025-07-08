from flask import Flask, request, redirect, session, render_template_string
import requests
import pandas as pd
import os
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "max-laps-challenge-2025"

# Strava API credentials - hardcoded
CLIENT_ID = "162020"
CLIENT_SECRET = "61bcb36a6ca4ac4ed59edaaf5ea9fb5f9172cec3"
REDIRECT_URI = "https://strava-gps-tracker.onrender.com/callback"

# Target segments for MAX Laps Challenge
TARGET_SEGMENTS = {
    '4805244': 'Smuggler Uphill Trail Run',
    '2344230': 'ACC - Smuggler TT (Ride)',
}

@app.route('/')
def home():
    """Home page with login/dashboard"""
    if 'access_token' in session:
        return redirect('/dashboard')
    
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=read,activity:read_all"
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Challenge Tracker</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #fc4c02; text-align: center; }
            .btn { background-color: #fc4c02; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
            .btn:hover { background-color: #e34402; }
            .center { text-align: center; }
            .segments { background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏔️ MAX Laps Challenge Tracker</h1>
            <h2>Smuggler Mountain Segment Leaderboard</h2>
            
            <div class="segments">
                <h3>📍 Tracking These Segments:</h3>
                <ul>
                    <li><strong>Smuggler Uphill Trail Run</strong> (ID: 4805244)</li>
                    <li><strong>ACC - Smuggler TT Ride</strong> (ID: 2344230)</li>
                </ul>
            </div>
            
            <div class="center">
                <p>Track who completes the most laps on Smuggler Mountain!</p>
                <a href="{{ auth_url }}" class="btn">Connect with Strava</a>
            </div>
        </div>
    </body>
    </html>
    ''', auth_url=auth_url)

@app.route('/callback')
def callback():
    """Handle Strava OAuth callback"""
    code = request.args.get('code')
    
    if not code:
        return "Error: No authorization code received", 400
    
    # Exchange code for token
    token_url = "https://www.strava.com/oauth/token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(token_url, data=payload)
    
    if response.status_code == 200:
        data = response.json()
        session['access_token'] = data['access_token']
        session['athlete'] = data['athlete']
        return redirect('/dashboard')
    else:
        return f"Error: {response.text}", 400

@app.route('/dashboard')
def dashboard():
    """Main dashboard showing lap counts"""
    if 'access_token' not in session:
        return redirect('/')
    
    token = session['access_token']
    athlete = session.get('athlete', {})
    
    # Get time frame from query params (default: last 30 days)
    days = int(request.args.get('days', 30))
    after_date = datetime.now() - timedelta(days=days)
    
    # Fetch activities from following
    activities = get_following_activities(token, after_date)
    
    # Process activities for segment efforts
    lap_counts = defaultdict(lambda: defaultdict(int))
    segment_times = defaultdict(lambda: defaultdict(list))
    
    for activity in activities:
        athlete_name = f"{activity.get('athlete', {}).get('firstname', '')} {activity.get('athlete', {}).get('lastname', '')}".strip()
        
        # Get full activity details
        full_activity = get_activity_details(token, activity['id'])
        if full_activity:
            for effort in full_activity.get('segment_efforts', []):
                segment_id = str(effort.get('segment', {}).get('id', ''))
                
                if segment_id in TARGET_SEGMENTS:
                    lap_counts[segment_id][athlete_name] += 1
                    elapsed_time = effort.get('elapsed_time', 0)
                    segment_times[segment_id][athlete_name].append(elapsed_time)
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #fc4c02; text-align: center; }
            .athlete-info { background: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
            .segment { background: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #fc4c02; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .filters { margin: 20px 0; text-align: center; }
            .btn { background-color: #fc4c02; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin: 0 5px; }
            .btn:hover { background-color: #e34402; }
            .logout { float: right; }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/logout" class="btn logout">Logout</a>
            <h1>🏔️ MAX Laps Challenge Dashboard</h1>
            
            <div class="athlete-info">
                <strong>Welcome {{ athlete.firstname }} {{ athlete.lastname }}!</strong>
            </div>
            
            <div class="filters">
                <strong>Time Period:</strong>
                <a href="?days=7" class="btn">Last 7 Days</a>
                <a href="?days=30" class="btn">Last 30 Days</a>
                <a href="?days=90" class="btn">Last 90 Days</a>
                <a href="?days=365" class="btn">Last Year</a>
            </div>
            
            <h2>🏆 Leaderboard (Last {{ days }} Days)</h2>
            
            {% for segment_id, segment_name in segments.items() %}
            <div class="segment">
                <h3>{{ segment_name }}</h3>
                <table>
                    <tr>
                        <th>Rank</th>
                        <th>Athlete</th>
                        <th>Laps</th>
                        <th>Best Time</th>
                        <th>Average Time</th>
                    </tr>
                    {% set sorted_athletes = lap_counts[segment_id].items()|sort(reverse=true, attribute=1) %}
                    {% for athlete_name, count in sorted_athletes[:20] %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ athlete_name }}</td>
                        <td><strong>{{ count }}</strong></td>
                        <td>{{ format_time(min(segment_times[segment_id][athlete_name])) }}</td>
                        <td>{{ format_time(sum(segment_times[segment_id][athlete_name]) / count) }}</td>
                    </tr>
                    {% endfor %}
                </table>
                {% if not lap_counts[segment_id] %}
                <p>No activities found for this segment in the selected time period.</p>
                {% endif %}
            </div>
            {% endfor %}
            
            <div style="margin-top: 40px; text-align: center; color: #666;">
                <p>Tracking {{ total_activities }} activities from people you follow</p>
                <p><small>Note: Only shows public activities from people you follow on Strava</small></p>
            </div>
        </div>
    </body>
    </html>
    ''', athlete=athlete, segments=TARGET_SEGMENTS, lap_counts=dict(lap_counts), 
        segment_times=dict(segment_times), days=days, total_activities=len(activities),
        format_time=format_time)

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect('/')

def get_following_activities(token, after_date):
    """Get activities from people you follow"""
    headers = {'Authorization': f'Bearer {token}'}
    activities = []
    page = 1
    
    while True:
        params = {
            'page': page,
            'per_page': 100,
            'after': int(after_date.timestamp())
        }
        
        response = requests.get(
            'https://www.strava.com/api/v3/activities/following',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            batch = response.json()
            if not batch:
                break
            activities.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        else:
            break
    
    return activities

def get_activity_details(token, activity_id):
    """Get full activity details including segments"""
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.get(
        f'https://www.strava.com/api/v3/activities/{activity_id}',
        headers=headers
    )
    
    if response.status_code == 200:
        return response.json()
    return None

def format_time(seconds):
    """Format seconds to MM:SS"""
    if isinstance(seconds, list):
        seconds = seconds[0] if seconds else 0
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
