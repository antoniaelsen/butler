import logging
import hashlib
import json
import os
import requests
import time


LASTFM_API_URL = "http://ws.audioscrobbler.com/2.0/"
LASTFM_AUTH_URL = "http://www.last.fm/api/auth/"

logger = logging.getLogger(__name__)

def timecode_from_str(string):
  split = list(map(lambda x: int(x), string.strip("[]").split(":")))
  return split[0] * 60 + split[1]


class Scrobbler:
  def __init__(self, api_key, secret, session = None):
    version = os.environ.get("BUTLER_VERSION")

    logger.info("Initializing scrobbler")
    logger.debug(f' - API key: {api_key}')
    logger.debug(f" - Secret: {secret}")
    logger.debug(f" - Session: {session}")

    self.api_key = api_key
    self.secret = secret
    self.session = session

    self.rs = requests.Session();
    self.rs.headers["User-Agent"] = f"Butler/{version}"

    self.last_track = None
    self.last_timecode = 0

  def run(self, sample):
    # TODO(aelsen): move now playing / scrobble decision logic to monitor
    # TODO(aelsen): set 'now playing' immediately,
    #   scrobble if played for longer than x secs
    album = sample.album
    artist = sample.artist
    timecode = sample.timecode
    track = sample.track
    track_number = sample.track_number
    isrc = sample.isrc

    req = {
      "album": album,
      "artist": artist,
      "track": track,
      "trackNumber": track_number,
      "timecode": timecode
    }

    logger.info(
      f'Analyzing playback of {req["artist"]} - {req["track"]} '
      f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
    )

    timecode = timecode_from_str(timecode)
    track = isrc

    if (self.last_track != track):
      logger.info(
        f'Detected new track {req["artist"]} - {req["track"]} '
        f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
      )
      self.now_playing(req)
      self.scrobble(req)

    else:
      if (self.last_timecode - timecode > 30):
        logger.info(
          f'Detected new playback of {req["artist"]} - {req["track"]} '
          f'({req["album"]} : {req["trackNumber"]}) [{timecode}]'
        )
        self.scrobble(req)


    self.last_track = track
    self.last_timecode = timecode

  def now_playing(self, req):
    res = self.request("POST", "track.updateNowPlaying", req, True)
    if ("error" in res):
      logger.error(f'Failed to list track as "Now Playing": {res["message"]}')
      return

    logger.info(
      f'Updated "Now Playing" with {req["artist"]} - {req["track"]} '
      f'({req["album"]} : {req["trackNumber"]})'
    )

  def scrobble(self, req):
    ts = time.time()
    _req = req.copy()
    _req["timestamp"] = ts

    res = self.request("POST", "track.scrobble", _req, True)

    if ("error" in res):
      logger.warn(f'Failed to scrobble track: {res["message"]}')
      return

    ignored = res["scrobbles"]["@attr"]["ignored"]
    if (ignored > 0):
      logger.warn(f'Scrobbled track was ignored: {res}')
    else:
      logger.info(
        f'Scrobbled {req["artist"]} - {req["track"]} '
        f'({req["album"]} : {req["trackNumber"]}) @ {ts}'
      )

  # -----

  def authenticate(self):
    logger.debug("Authenticating...")
    res = self.get_token()
    if ("error" in res):
      logger.error(f'Failed to get token: {res["message"]}')
      return False

    token = res["token"]

    self.request_authorization(token)

    res = self.get_session(token)
    if ("error" in res):
      logger.error(f'Failed to get session: {res["message"]}')
      return False

    self.session = res["session"]["key"]

    logger.info(f'Authenticated user {res["session"]["user"]}')
    return True

  def get_session(self, token):
    req = self.sign_parameters("auth.getSession", {
      "api_key": self.api_key,
      "token": token
    })
    return self.request("GET", "auth.getSession", req)

  def get_token(self):
    req = self.sign_parameters("auth.getToken", {
      "api_key": self.api_key
    })
    return self.request("GET", "auth.getToken", req)

  def request(self, method, api_method, req, authenticated = False):
    base = {
      "method": api_method,
      "format": "json"
    }

    _req = req.copy()
    if (authenticated):
      if (not self.session):
        rc = self.authenticate()

      _req["api_key"] = self.api_key
      _req["sk"] = self.session
      _req = self.sign_parameters(api_method, _req)

    _req = { **base, **_req }

    logger.debug(
        f'Making {"AUTHENTICATED " if authenticated else ""}{method} '
        f'request to {LASTFM_API_URL} with req {_req}'
    )
    r = self.rs.request(method, LASTFM_API_URL, params=_req)
    res = r.json()

    logger.debug(f'Request {r.url} response {json.dumps(res, indent=2)}')

    return res

  def request_authorization(self, token):
    params = {
      "api_key": self.api_key,
      "token": token
    }
    url = f'{LASTFM_AUTH_URL}?'
    for i, (k, v) in enumerate(params.items()):
      url += f'{"&" if (i > 0) else ""}{k}={v}'

    logger.warn(f'Please navigate to {url} to authenticate this application.')
    input("Press Enter to continue...")

  def sign_parameters(self, api_method, params):
    _params = params.copy()
    sig = self.signature(api_method, _params)
    _params["api_sig"] = sig
    return _params

  def signature(self, api_method, params):
    sig = ""
    _params = {
      **{ "method": api_method },
      **params
    }

    logger.debug(f'Generating API signature with keys {sorted(params.items())}')
    for k, v in sorted(_params.items()):
      sig += f'{k}{v}'
    sig += self.secret

    return hashlib.md5(sig.encode('utf-8')).hexdigest()
