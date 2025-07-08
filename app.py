from flask import Flask, request, redirect, session, url_for
import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

app = Flask(__name__)
app.secret_key = "max-laps-challenge-2025-secret-key"

# Strava API credentials
CLIENT_ID = "162020"
CLIENT_SECRET = "61bcb36a6ca4ac4ed59edaaf5ea9fb5f9172cec3"
REDIRECT_URI = "https://strava-gps-tracker.onrender.com/callback"

# Target segments
TARGET_SEGMENTS = {
    '4805244': 'Smuggler Uphill Trail Run',
    '2344230': 'ACC - Smuggler TT (Ride)',
}

@app.route('/')
def home():
    if 'access_token' in session:
        return redirect('/dashboard')
    
    auth_url = f"https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&approval_prompt=force&scope=read,activity:read_all"
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Challenge</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .btn {{ background-color: #fc4c02; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏔️ MAX Laps Challenge Tracker</h1>
            <h2>Smuggler Mountain Segments</h2>
            <p>Track who completes the most laps!</p>
            <a href="{auth_url}" class="btn">Connect with Strava</a>
        </div>
    </body>
    </html>
    '''

@app.route('/callback')
def callback():
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
    
    try:
        response = requests.post(token_url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            session['access_token'] = data['access_token']
            session['athlete'] = data.get('athlete', {})
            return redirect('/dashboard')
        else:
            return f"Error getting token: {response.text}", 400
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/dashboard')
def dashboard():
    if 'access_token' not in session:
        return redirect('/')
    
    athlete = session.get('athlete', {})
    token = session['access_token']
    
    # Get time period from query params
    days = int(request.args.get('days', 30))
    
    # Fetch activities and count laps
    lap_data, debug_info = get_lap_counts_with_debug(token, days)
    
    # Build leaderboard HTML
    leaderboard_html = ""
    for segment_id, segment_name in TARGET_SEGMENTS.items():
        leaderboard_html += f'<div class="segment"><h3>{"🏃" if "Run" in segment_name else "🚴"} {segment_name}</h3>'
        
        if segment_id in lap_data and lap_data[segment_id]:
            leaderboard_html += '<table><tr><th>Rank</th><th>Athlete</th><th>Laps</th><th>Best Time</th></tr>'
            
            # Sort by lap count
            sorted_athletes = sorted(lap_data[segment_id].items(), key=lambda x: x[1]['count'], reverse=True)
            
            for rank, (athlete_name, data) in enumerate(sorted_athletes[:20], 1):
                best_time = min(data['times']) if data['times'] else 0
                mins = best_time // 60
                secs = best_time % 60
                leaderboard_html += f'<tr><td>{rank}</td><td>{athlete_name}</td><td><strong>{data["count"]}</strong></td><td>{mins}:{secs:02d}</td></tr>'
            
            leaderboard_html += '</table>'
        else:
            leaderboard_html += '<p>No activities found for this segment in the selected period.</p>'
        
        leaderboard_html += '</div>'
    
    # Debug section
    debug_html = f'''
    <div style="background: #f0f0f0; padding: 15px; margin: 20px 0; border-radius: 5px;">
        <h3>Debug Information:</h3>
        <p>Total activities checked: {debug_info['total_activities']}</p>
        <p>Activities with segments: {debug_info['activities_with_segments']}</p>
        <p>Smuggler segments found: {debug_info['smuggler_segments_found']}</p>
        <p>Following count: {debug_info.get('following_count', 'Unknown')}</p>
    </div>
    '''
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .segment {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .btn {{ background-color: #fc4c02; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .filters {{ text-align: center; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #fc4c02; color: white; }}
            tr:hover {{ background-color: #f0f0f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏔️ MAX Laps Dashboard</h1>
            <p>Welcome {athlete.get('firstname', '')} {athlete.get('lastname', '')}!</p>
            
            <div class="filters">
                <strong>Time Period:</strong>
                <a href="?days=7" class="btn">Last 7 Days</a>
                <a href="?days=30" class="btn">Last 30 Days</a>
                <a href="?days=90" class="btn">Last 90 Days</a>
                <a href="?days=365" class="btn">Last Year</a>
            </div>
            
            <h2>🏆 Leaderboard (Last {days} Days)</h2>
            {leaderboard_html}
            
            {debug_html}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/my-laps" class="btn">View My Laps</a>
                <a href="/logout" class="btn">Logout</a>
            </div>
            
            <p style="text-align: center; color: #666; margin-top: 20px;">
                <small>Note: Shows activities from people you follow. Make sure activities are public!</small>
            </p>
        </div>
    </body>
    </html>
    '''

def get_lap_counts_with_debug(token, days):
    """Fetch activities and count laps on target segments with debug info"""
    headers = {'Authorization': f'Bearer {token}'}
    after_date = datetime.now() - timedelta(days=days)
    
    debug_info = {
        'total_activities': 0,
        'activities_with_segments': 0,
        'smuggler_segments_found': 0
    }
    
    # Get activities from people you follow
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
    
    debug_info['total_activities'] = len(activities)
    
    # Process activities for segment efforts
    lap_counts = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'times': []}))
    
    for activity in activities:
        activity_id = activity.get('id')
        
        # Get full activity details
        response = requests.get(
            f'https://www.strava.com/api/v3/activities/{activity_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            full_activity = response.json()
            athlete_name = f"{full_activity.get('athlete', {}).get('firstname', '')} {full_activity.get('athlete', {}).get('lastname', '')}".strip()
            
            if full_activity.get('segment_efforts'):
                debug_info['activities_with_segments'] += 1
            
            # Check segment efforts
            for effort in full_activity.get('segment_efforts', []):
                segment_id = str(effort.get('segment', {}).get('id', ''))
                
                if segment_id in TARGET_SEGMENTS:
                    debug_info['smuggler_segments_found'] += 1
                    lap_counts[segment_id][athlete_name]['count'] += 1
                    lap_counts[segment_id][athlete_name]['times'].append(effort.get('elapsed_time', 0))
    
    return lap_counts, debug_info

@app.route('/my-laps')
def my_laps():
    """Show only the logged-in user's laps"""
    if 'access_token' not in session:
        return redirect('/')
    
    token = session['access_token']
    athlete = session.get('athlete', {})
    athlete_id = athlete.get('id')
    
    # Get user's activities
    headers = {'Authorization': f'Bearer {token}'}
    activities = []
    page = 1
    
    while True:
        params = {'page': page, 'per_page': 100}
        response = requests.get(
            'https://www.strava.com/api/v3/athlete/activities',
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
    
    # Count laps
    my_laps = defaultdict(list)
    
    for activity in activities:
        activity_id = activity.get('id')
        
        # Get full activity details
        response = requests.get(
            f'https://www.strava.com/api/v3/activities/{activity_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            full_activity = response.json()
            
            for effort in full_activity.get('segment_efforts', []):
                segment_id = str(effort.get('segment', {}).get('id', ''))
                
                if segment_id in TARGET_SEGMENTS:
                    my_laps[segment_id].append({
                        'date': effort.get('start_date_local', '')[:10],
                        'time': effort.get('elapsed_time', 0),
                        'activity_name': full_activity.get('name', ''),
                        'pr_rank': effort.get('pr_rank')
                    })
    
    # Build HTML
    laps_html = ""
    for segment_id, segment_name in TARGET_SEGMENTS.items():
        laps_html += f'<div class="segment"><h3>{"🏃" if "Run" in segment_name else "🚴"} {segment_name}</h3>'
        
        if segment_id in my_laps:
            laps = sorted(my_laps[segment_id], key=lambda x: x['date'], reverse=True)
            laps_html += f'<p>Total laps: <strong>{len(laps)}</strong></p>'
            laps_html += '<table><tr><th>Date</th><th>Time</th><th>Activity</th><th>PR</th></tr>'
            
            for lap in laps[:50]:  # Show last 50
                mins = lap['time'] // 60
                secs = lap['time'] % 60
                pr = "⭐" if lap['pr_rank'] == 1 else ""
                laps_html += f'<tr><td>{lap["date"]}</td><td>{mins}:{secs:02d}</td><td>{lap["activity_name"]}</td><td>{pr}</td></tr>'
            
            laps_html += '</table>'
        else:
            laps_html += '<p>No laps found.</p>'
        
        laps_html += '</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>My Laps - MAX Laps</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .segment {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .btn {{ background-color: #fc4c02; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #fc4c02; color: white; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 My Smuggler Mountain Laps</h1>
            <p>{athlete.get('firstname', '')} {athlete.get('lastname', '')}</p>
            
            {laps_html}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/dashboard" class="btn">Back to Leaderboard</a>
                <a href="/logout" class="btn">Logout</a>
            </div>
        </div>
    </body>
    </html>
    '''@app.route('/dashboard')
def dashboard():
    if 'access_token' not in session:
        return redirect('/')
    
    athlete = session.get('athlete', {})
    token = session['access_token']
    
    # Get time period from query params
    days = int(request.args.get('days', 30))
    
    # Fetch activities and count laps
    lap_data = get_lap_counts(token, days)
    
    # Build leaderboard HTML
    leaderboard_html = ""
    for segment_id, segment_name in TARGET_SEGMENTS.items():
        leaderboard_html += f'<div class="segment"><h3>{"🏃" if "Run" in segment_name else "🚴"} {segment_name}</h3>'
        
        if segment_id in lap_data and lap_data[segment_id]:
            leaderboard_html += '<table><tr><th>Rank</th><th>Athlete</th><th>Laps</th><th>Best Time</th></tr>'
            
            # Sort by lap count
            sorted_athletes = sorted(lap_data[segment_id].items(), key=lambda x: x[1]['count'], reverse=True)
            
            for rank, (athlete_name, data) in enumerate(sorted_athletes[:20], 1):
                best_time = min(data['times']) if data['times'] else 0
                mins = best_time // 60
                secs = best_time % 60
                leaderboard_html += f'<tr><td>{rank}</td><td>{athlete_name}</td><td><strong>{data["count"]}</strong></td><td>{mins}:{secs:02d}</td></tr>'
            
            leaderboard_html += '</table>'
        else:
            leaderboard_html += '<p>No activities found for this segment in the selected period.</p>'
        
        leaderboard_html += '</div>'
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .segment {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .btn {{ background-color: #fc4c02; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin: 5px; }}
            .filters {{ text-align: center; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #fc4c02; color: white; }}
            tr:hover {{ background-color: #f0f0f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏔️ MAX Laps Dashboard</h1>
            <p>Welcome {athlete.get('firstname', '')} {athlete.get('lastname', '')}!</p>
            
            <div class="filters">
                <strong>Time Period:</strong>
                <a href="?days=7" class="btn {'active' if days == 7 else ''}">Last 7 Days</a>
                <a href="?days=30" class="btn {'active' if days == 30 else ''}">Last 30 Days</a>
                <a href="?days=90" class="btn {'active' if days == 90 else ''}">Last 90 Days</a>
            </div>
            
            <h2>🏆 Leaderboard (Last {days} Days)</h2>
            {leaderboard_html}
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/logout" class="btn">Logout</a>
            </div>
            
            <p style="text-align: center; color: #666; margin-top: 20px;">
                <small>Note: Shows activities from people you follow. Make sure activities are public!</small>
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def get_lap_counts(token, days):
    """Fetch activities and count laps on target segments"""
    headers = {'Authorization': f'Bearer {token}'}
    after_date = datetime.now() - timedelta(days=days)
    
    # Get activities from people you follow
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
    
    # Process activities for segment efforts
    lap_counts = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'times': []}))
    
    for activity in activities:
        activity_id = activity.get('id')
        
        # Get full activity details
        response = requests.get(
            f'https://www.strava.com/api/v3/activities/{activity_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            full_activity = response.json()
            athlete_name = f"{full_activity.get('athlete', {}).get('firstname', '')} {full_activity.get('athlete', {}).get('lastname', '')}".strip()
            
            # Check segment efforts
            for effort in full_activity.get('segment_efforts', []):
                segment_id = str(effort.get('segment', {}).get('id', ''))
                
                if segment_id in TARGET_SEGMENTS:
                    lap_counts[segment_id][athlete_name]['count'] += 1
                    lap_counts[segment_id][athlete_name]['times'].append(effort.get('elapsed_time', 0))
    
    return lap_counts

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
