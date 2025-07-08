from flask import Flask, request, redirect, session, url_for
import requests
import os

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
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAX Laps Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .segment {{ background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .btn {{ background-color: #fc4c02; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; margin: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏔️ MAX Laps Dashboard</h1>
            <p>Welcome {athlete.get('firstname', '')} {athlete.get('lastname', '')}!</p>
            
            <h2>Tracking These Segments:</h2>
            <div class="segment">
                <h3>🏃 Smuggler Uphill Trail Run</h3>
                <p>Segment ID: 4805244</p>
            </div>
            <div class="segment">
                <h3>🚴 ACC - Smuggler TT (Ride)</h3>
                <p>Segment ID: 2344230</p>
            </div>
            
            <p><em>Full leaderboard functionality coming soon!</em></p>
            
            <a href="/logout" class="btn">Logout</a>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
