import base64
import logging
import json
import jsonschema
import os
import requests
import time

from sample import Sample


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1/"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Track ID log
log_res_formatter = logging.Formatter('%(message)s')

log_res_file_handler = logging.FileHandler("logs/results.log")
log_res_file_handler.setLevel(logging.INFO)
log_res_file_handler.setFormatter(log_res_formatter)

res_logger = logging.getLogger("monitor_id")
res_logger.addHandler(log_res_file_handler)
res_logger.propagate = False

# Track Occurrence log
log_occ_formatter = logging.Formatter('%(message)s')

log_occ_file_handler = logging.FileHandler("logs/occurrences.csv")
log_occ_file_handler.setLevel(logging.INFO)
log_occ_file_handler.setFormatter(log_occ_formatter)

occ_logger = logging.getLogger("occurrences")
occ_logger.addHandler(log_occ_file_handler)
occ_logger.propagate = False


class Album:
  def __init__(self, id, name, artists, album_type, n_tracks):
    self.id = id
    self.name = name
    self.artists = artists
    self.type = album_type
    self.n_tracks = n_tracks

class Occurrence:
  def __init__(self, track_number, album):
    self.track_number = track_number
    self.album = album

class Track:
  def __init__(self, isrc):
    self.isrc = isrc
    self.name = None
    self.artists = None
    self.album_occurrences = []
  
  def add_occurrence(self, album_occurrence):
    existing = next((occ for occ in self.album_occurrences if occ.album.id == album_occurrence.album.id), None)
    if (existing != None):
      return

    self.album_occurrences.append(album_occurrence)


def timecode_from_str(string):
  split = list(map(lambda x: int(x), string.strip("[]").split(":")))
  return split[0] * 60 + split[1]

def compare_tracks(a, b):
  if (a == None or b == None):
    return False

  if (a.isrc == b.isrc):
    return True
  
  return False


class Monitor:
  def __init__(self, fm, client_id, client_secret):
    version = os.environ.get("BUTLER_VERSION")

    logger.info("Initializing Monitor")
    self.debug_i = 0
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


  def run(self, sample):
    album = sample.album
    artist = sample.artist
    isrc = sample.isrc
    rms = sample.rms
    timecode = sample.timecode
    track = sample.track
    track_number = sample.track_number

    # Fingerprinting track info
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

    timecode = timecode_from_str(timecode)
    track = self.get_formats(isrc)
  
    # Compare this track to the last track to determine if it is the same track
    if (not compare_tracks(track, self.last_track) < 0):
      logger.info(
        f'Detected new track [{isrc}] = {req["artist"]} - {req["track"]} '
        f'({req["album"]} : {req["trackNumber"]}) [{timecode}]; {rms}'
      )
    
      for occ in track.album_occurrences:
        occ_logger.info(f"{self.debug_i}; {', '.join(track.artists)}; {track.name}; {timecode}; {occ.track_number}; {occ.album.n_tracks}; {occ.album.name}; {rms}")

      # TODO(aelsen)
      # Return track info with most likely album based on history

      self.fm.run(sample)

    self.last_track = track
    self.last_timecode = timecode
    self.debug_i += 1
  
  def get_formats(self, isrc):
    res = self.search(isrc)
  
    if ("error" in res):
      return

    rec_track = Track(isrc)

    tracks = res["tracks"]["items"]
    logger.info("Got Tracks")
    for track in tracks:
      album = track["album"]
      album_artists = list(map(lambda a: a["name"], album["artists"]))
      album_id = album["id"]
      album_name = album["name"]
      album_type = album["album_type"]
      album_n_tracks = album["total_tracks"]

      track_artists = list(map(lambda a: a["name"], track["artists"]))
      track_name = track["name"]
      track_number = track["track_number"]

      logger.info(f" - {', '.join(track_artists)} - {track_name} - ({track_number}/{album_n_tracks}) {album_name}")
  
      rec_album = Album(album_id, album_name, album_artists, album_type, album_n_tracks)
      rec_occ = Occurrence(track_number, rec_album)

      rec_track.add_occurrence(rec_occ)

      # TODO(aelsen)
      rec_track.name = track_name
      rec_track.artists = track_artists
    
    return rec_track


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
    if (not self.token):
      logger.info(f'No authorization token -- requesting token')
      res = self.request_authorization()
    if (time.time() - self.token_received > self.token_expires_in):
      logger.info(f'Authorization token expired -- refreshing token')
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
    res_logger.info(json.dumps(res, indent=2))
    # validated = jsonschema.validate(res, schema)
    # logger.debug(f' - Validating {validated}')
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

