import requests
import sqlite3

# SQLite connection to retrieve secret info (id,secret,user_id)
conn = sqlite3.connect('wwoz.db')
db = conn.cursor()

# Your Important Stuff // using these to build our Tokens which we'll use to navigate API endpoints
db.execute("SELECT CLIENT_ID FROM secrets")
CLIENT_ID = db.fetchone()[0]
db.execute("SELECT CLIENT_SECRET FROM secrets")
CLIENT_SECRET = db.fetchone()[0]

# URLS
REDIRECT_URL = 'https://developer.spotify.com/dashboard/applications/f769c91b844d4156aeca31c16193108b'
TOKEN_URL = 'https://accounts.spotify.com/api/token'
AUTH_URL = 'https://accounts.spotify.com/authorize'

# 1.) AUTHORIZE ACCOUNT //  Make a request to the /authorize endpoint to get an authorization code
auth_code = requests.get(AUTH_URL,params={
                                        'client_id': CLIENT_ID,
                                        'response_type': 'code',
                                        'redirect_uri': REDIRECT_URL,
                                        'scope': 'playlist-modify-private playlist-modify-public'})
                                
print(f'\n\n --please go to-- \n\n {auth_code.url}, \n\n click authorize, then copy the URL it redirects you to')

# 2.) GET REFRESH TOKEN // copy paste URL you were redirected to here:
while True:
    url_input = input('\nPlease enter the URL you just copied: ')
    if url_input != '':
        CODE = url_input.split("code=")[1]
        break

token_response = requests.post(TOKEN_URL, {
    'grant_type':'authorization_code',
    'code':CODE,
    'redirect_uri':REDIRECT_URL,
    'client_id':CLIENT_ID,
    'client_secret':CLIENT_SECRET
})

if token_response.status_code in [200,201]:
    token_response_data = token_response.json()
    
    access_token = token_response_data['access_token']
    refresh_token = token_response_data['refresh_token']
    
#Create SQLITE tables to store my Tokens, Credentials, to navigate the API
#Tokens Table
db.execute("DROP TABLE IF EXISTS tokens")
db.executescript('''
    CREATE TABLE tokens (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        refresh_token TEXT UNIQUE,
        access_token TEXT UNIQUE
        )
        ''')

#Playlists Table
db.execute("DROP TABLE IF EXISTS playlists")
db.executescript('''
    CREATE TABLE playlists (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT UNIQUE,
        date INTEGER UNIQUE
    )
''')

#Tracks Table
db.execute("DROP TABLE IF EXISTS tracks")
db.executescript('''
    CREATE TABLE tracks (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        artist TEXT,
        song TEXT,
        uri TEXT UNIQUE,
        playlist_id INTEGER REFERENCES playlists(id)
    )
''')

#Insert Tokens + Credentials into tokens table
db.execute("INSERT INTO tokens (refresh_token,access_token) VALUES (?,?)",(refresh_token,access_token))

conn.commit()
conn.close()

