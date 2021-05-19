import requests
import sqlite3
import pandas as pd
from selenium import webdriver
from bs4 import BeautifulSoup
import sqlite3
import numpy as np
import time
import datetime as dt
import json
import requests


class spotifyDB():
    def __init__(self):
        self.conn = sqlite3.connect('wwoz.db')
    
    def InsertPlaylist(self,name):
        db = self.conn.cursor()
        date = dt.datetime.today().strftime('%m-%d-%Y')
        db.execute("INSERT INTO playlists (name,date) VALUES (?,?)",(name,date))
        self.conn.commit()
    
    def InsertTrack(self,artist,song,uri,playlist_id):
        db = self.conn.cursor()
        db.execute("INSERT INTO tracks (artist,song,uri,playlist_id) VALUES (?,?,?,?)",(artist,song,uri,playlist_id))
        self.conn.commit()

    def GetUris(self):
        db = self.conn.cursor()
        db.execute("SELECT uri FROM tracks")
        return db.fetchall()

    def GetPlaylistid(self):
        db = self.conn.cursor()
        db.execute("SELECT id FROM playlists WHERE id = (SELECT MAX(id) FROM playlists)")
        return db.fetchone()[0]

    def GetSecrets(self):
        db = self.conn.cursor()
        db.execute("SELECT CLIENT_ID,CLIENT_SECRET,USER_ID FROM secrets")
        return db.fetchone()
    
    def GetTokens(self):
        db = self.conn.cursor()
        db.execute("SELECT refresh_token, access_token FROM tokens")
        return db.fetchone()
    
    def UpdateToken(self,newToken):
        db = self.conn.cursor()
        #SQL UPDATE tokens.db SET VALUE of ACCESS_TOKEN = newToken
        db.execute("UPDATE tokens SET access_token = ?", (newToken,))
        conn.commit()


# ------------------- Method Definitions -------------------------

def scrape_top_100(url):
    #create new chrome session
    driver = webdriver.Chrome()
    #load the web page
    driver.get(url)
    #wait for the page to fully load
    driver.implicitly_wait(5)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source,'html.parser')
    cols = soup.find_all('td')

    artists = [col.text for col in cols if col.attrs['data-bind'] == 'artist']
    albums = [col.text for col in cols if col.attrs['data-bind'] == 'album']
    songs = [col.text for col in cols if col.attrs['data-bind'] == 'title']
    track_dict = {'Artist':artists,'Album':albums,'Title':songs}
    df = pd.DataFrame(track_dict)
    return df

def refresh():
    #Post Request to Spotify API with our 1.) endpoint 2.) auth 3.) request body
    reqBody = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}
    r = requests.post('https://accounts.spotify.com/api/token', auth=basicToken(), data=reqBody)
    resJson = r.json()
    newToken = resJson['access_token']
    spotifyDB.UpdateToken(newToken)
    #return it for our session to hit API endpoints all damn day
    return newToken

#Our Header Function which will be used to hit endpoints //
def authHeader():
    return {'Authorization': 'Bearer {}'.format(access_token)}

#Basic Token-Generator via Credentials, used in Header request for Refreshing our access_token //
def basicToken():
    return client_credentials

#Scraper
def scrape_top_100():
    #create new chrome session
    driver = webdriver.Chrome()
    #load the web page
    driver.get(url)
    #wait for the page to fully load
    driver.implicitly_wait(5)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source,'html.parser')
    cols = soup.find_all('td')
    return cols

#Clean Scraped data in Pandas DataFrame
def df_prep():
    artists = [col.text for col in cols if col.attrs['data-bind'] == 'artist']
    albums = [col.text for col in cols if col.attrs['data-bind'] == 'album']
    songs = [col.text for col in cols if col.attrs['data-bind'] == 'title']
    
    track_dict = {'Artist':artists,'Album':albums,'Title':songs}
    df = pd.DataFrame(track_dict)
    replace_dict = {'featuring':'','ft.':'','ft':'','feat':'','feat.':'','&':''}
    df['Title'] = df['Title'].str.replace(r"\*+",'')
    df['Artist'] = df['Artist'].replace(replace_dict,regex=True)
    df['Artist'] = df['Artist'].str.replace(r"\(.*\)",'')
    df = df.reset_index()
    
    track_n_artist = df['Title'].str.lower()+ ' ' + df['Artist'].str.lower()
    track_n_artist = track_n_artist.str.replace(' ','+')
    return track_n_artist,df

#Call Spotify API
def api(series):
    correct = []
    for i,s in enumerate(series):
        queryParams = f'?q={s}&type=track'
        r = requests.get('https://api.spotify.com/v1/search' + queryParams, headers=headers)
        res = r.json()
        for y in res['tracks']['items']:
            if y['artists'][0]['name'].lower()[:5] in df['Artist'].iloc[i].lower():
                if y['name'].lower()[:4] == df['Title'].iloc[i][:4].lower():
                    correct.append((i,y['name'],y['artists'][0]['name'],y['id']))
    return correct

# Filter song_id // URI Output into a new DataFrame          
def uri_matches(correct):
    df2 = pd.DataFrame(correct)
    df2 = df2.rename(columns={0:'index',1:'track',2:'artist',3:'uri'})
    df2 = df2.drop_duplicates(subset='index',keep='first')
    df2.set_index('index')
    df2 = df2.reset_index()
    return df2

# Measure what we got right, and create a DataFrame of the unmatched songs
def measure(df,df2):
    df_outer = pd.merge(df,df2,how='outer',on='index')
    df_inner = pd.merge(df,df2,how='inner',on='index')
    missing = (len(df_outer) - len(df_inner)) / len(df)
    miss_df = df.drop(df_inner.index,axis=0)
    return print(f'Missing {round(missing*100)} Spotify matches'),miss_df

# Create Playlist Name based on Date
def playlist_name():
    today = dt.datetime.today()
    date = today.strftime('%m-%d-%Y')
    weekday = today.strftime('%A')
    name = f'WWOZ {weekday} {date}'
    return name

# API Call to create Spotify playlist
def create_playlist():
    url = BASE_URL + 'users/' + user_id + '/playlists'
    reqbody = json.dumps({'name': playlist_name(),
               'description':'Playlist of WWOZ radio plays scraped from 100 most recent songs',
              'public': 'true'})
    r = requests.post(url = url, data = reqbody, headers=headers)
    db.InsertPlaylist(playlist_name())
    return r.json()['id']

# Ensure songs aren't already in a playlist somewhere // check against SQLite DataBase
def check_redundancies():
    uris = [x[0] for x in db.GetUris()]
    new = df2['uri'].tolist()
    good_to_go = [uri for uri in new if uri not in uris]
    return good_to_go

# API Call to Add songs // Add the newly-added URI's to our SQLite DataBase
def add_tracks_to_spotify(spotify_playlist_id):
    uri_list = list(map(lambda uri: 'spotify:track:'+ uri, check_redundancies()))
    reqbody = json.dumps({'uris': uri_list })
    r = requests.post(f'https://api.spotify.com/v1/users/{user_id}/playlists/{spotify_playlst_id}/tracks', 
            data=reqbody,headers=headers)
    if r.status_code in [200, 201]:
        print('WOOOO!!!')
    try:
        # use check_redundancies() to mask df2 (our matched tracks w/ URIs) for SQL Insert
        playlist_id = db.GetPlaylistid()
        df3 = df2.loc[df2['uri'].isin(check_redundancies())] 
        df3.apply(lambda x: db.InsertTrack(x['artist'],x['track'],x['uri'],playlist_id),axis=1)
    except:
        print('no luck adding these new tracks to database')

def run_that_shit():
    #1.) ---- scrape top 100
    cols = scrape_top_100()

    #2.) ---- prep df into query params
    track_n_artist = df_prep(cols)[0]
    df = df_prep(cols)[1]

    #3.) ---- call_api // store uri's in df
    df2 = uri_matches(api(track_n_artist))

    #4.) ---- make playlist // add tracks
    if len(check_redundancies()) != 0:
        add_tracks_to_spotify(create_playlist())
    else:
        print('Nothing new to add')

    #5.) ---- output missing entries / counts
    print('Success! Check Spotify for your new Playlist')
    return measure(df,df2)

# -------------------------- SCRIPT -------------------------

#1. connect to db class
db = spotifyDB()

#2. fetch tokens / creds / ids
refresh_token = db.GetTokens()[0]
user_id = db.GetSecrets()[2]
client_credentials = db.GetSecrets()[:2]
access_token = db.GetTokens()[1]

#3. try to requests.get our API connection
testRequest = requests.get('https://api.spotify.com/v1/me', headers=authHeader())

# if unauthorized, need to refresh access token
if testRequest.status_code in [401, 403]:
    access_token = refresh()

#4. rip through scrape and parse that HTML shit up. 
url = 'https://www.wwoz.org/programs/playlists'
headers = {'Content-Type':'application/json','Authorization': 'Bearer {token}'.format(token=access_token)}
BASE_URL = 'https://api.spotify.com/v1/'

#5. Run it All.
run_that_shit()



