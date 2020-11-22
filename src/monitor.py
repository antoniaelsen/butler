import base64
import logging
import json
import os
import requests
import time


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1/"

logger = logging.getLogger(__name__)


class Track:
  def __init__(self, isrc, name, artist, album):
    self.isrc = isrc
    self.name = name
    self.artist = artist
    self.album = album

def timecode_from_str(string):
  split = list(map(lambda x: int(x), string.strip("[]").split(":")))
  return split[0] * 60 + split[1]

def compare_tracks(a, b):
  if (a == None or b == None):
    return -1

  if (a.isrc == b.isrc):
    return 1
  
  if (a.name == b.name and a.artist == b.artist):
    if (a.album == b.album):
      return 1
    return 0
  
  return -1


class Monitor:
  def __init__(self, fm, client_id, client_secret):
    version = os.environ.get("BUTLER_VERSION")

    logger.info("Initializing Monitor")
    self.fm = fm
    self.client_id = client_id
    self.client_secret = client_secret

    self.rs = requests.Session();
    self.rs.headers["User-Agent"] = f"Butler/{version}"
    self.token = None
    self.token_expires_in = 0
    self.token_received = 0

    self.last_track = None
    self.last_timecode = 0
    self.history = []

    logger.debug(f" - Client Id: {client_id}")
    logger.debug(f" - Client Secret: {client_secret}")


  def run(self, params):
    # TODO: Make service agnostic
    spotify = params["spotify"]
    album = params["album"]
    artist = params["artist"]
    timecode = params["timecode"]
    track = params["title"]
    track_number = spotify["track_number"]
    isrc = spotify["external_ids"]["isrc"]

    req = {
      "album": album,
      "artist": artist,
      "track": track,
      "trackNumber": track_number,
      "timecode": timecode
    }

    logger.info(
      f'Analyzing playback of [{isrc}] = {req["artist"]} - {req["track"]} '
      f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
    )

    # timecode = timecode_from_str(timecode)
    track = Track(isrc, track, artist, album)

    if (compare_tracks(track, self.last_track) < 0):
      logger.info(
        f'Detected new track [{isrc}] = {req["artist"]} - {req["track"]} '
        f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
      )

      self.get_formats(isrc)

    # else:
    #   if (self.last_timecode - timecode > 30):
    #     logger.info(
    #       f'Detected new playback of [{isrc}] = {req["artist"]} - {req["track"]} '
    #       f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
    #     )

    self.last_track = track
    self.last_timecode = timecode
  
  def get_formats(self, isrc):
    res = self.search(isrc)
  
    if ("error" in res):
      return

    tracks = res["tracks"]["items"]
    for track in tracks:
      album = track["album"]
      album_artists = list(map(lambda a: a["name"], album["artists"]))
      album_name = album["name"]
      album_rd = album["release_date"]
      album_type = album["album_type"]
      album_n_tracks = album["total_tracks"]

      track_artists = list(map(lambda a: a["name"], track["artists"]))
      track_name = track["name"]
      track_number = track["track_number"]

  def request_authorization(self):
    logger.debug(f'Requesting authorization')
    r = self.rs.post(
      SPOTIFY_AUTH_URL,
      auth=(self.client_id, self.client_secret),
      data={ "grant_type": "client_credentials"}
    )
    res = r.json()

    if ("error" in res):
      logger.error(f'Failed to authenticate with Spotify API: {res["error"]}')
      return False;

    self.token = res["access_token"]
    self.token_expires_in = res["expires_in"]
    self.token_received = time.time()

    return True

  def request(self, endpoint, params):
    if (time.time() - self.token_received > self.token_expires_in):
      logger.debug(f'Authorization token expired -- refreshing token')
      res = self.request_authorization()
      if (not res):
        return

    logger.debug(f'Making request to {endpoint} with {params}')
    r = self.rs.get(
      f'{SPOTIFY_API_URL}{endpoint}',
      headers={ "Authorization": f'Bearer {self.token}' },
      params=params
    )
    res = r.json()
    logger.debug(f' - Got response {json.dumps(res, indent=2)}')
    return res

  def search(self, isrc):
    logger.debug(f'Searching for ISRC [{isrc}] {self.token}')
    res = self.request("search", {
      "q": f"isrc:{isrc}",
      "type": "track"
    })

    if ("error" in res):
      logger.error(f'Failed to search for ISRC: {res["error"]}')
      return False;
  
    return res

