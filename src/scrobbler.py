import logging
import json
import requests

LASTFM_URL = "http://ws.audioscrobbler.com/2.0/"

logger = logging.getLogger(__name__)

class Scrobbler:
  def __init__(self, api_key):
    self.api_key = api_key
    self.last_song = None
    self.last_play = None

  def run(self):
    pass

  def get_token(self):
    pass

  def make_request(self):
    pass

  def now_playing(self, ):
    pass

  def scrobble(self, ):
    pass