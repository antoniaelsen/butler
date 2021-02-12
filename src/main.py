import argparse
import logging
import json
import os
import sys
from time import sleep

import audioop
import wave

from fingerprinter import Fingerprinter
from monitor import Monitor
from sampler import Sampler
from scrobbler import Scrobbler
from sample import Sample


FINGERPRINT_API_KEY = os.environ.get("FINGERPRINT_API_KEY")
LASTFM_API_KEY = os.environ.get("LASTFM_API_KEY")
LASTFM_SECRET = os.environ.get("LASTFM_SECRET")
LASTFM_SESSION_KEY = os.environ.get("LASTFM_SESSION_KEY")
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

SAMPLE_FILENAME = "sample.wav"
SAMPLE_DURATION_SEC = 10
SAMPLE_PERIOD_SEC = 45
SAMPLE_THRESHOLD_RMS = 100


# Log Init
log_format = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
logging.basicConfig(
  datefmt='%Y-%m-%d_%I:%M:%S',
  format=log_format,
  level=logging.DEBUG,
  handlers=[
      logging.FileHandler("logs/debug.log"),
      logging.StreamHandler()
  ]
)

logger = logging.getLogger("main")

# Sample log
log_samp_formatter = logging.Formatter('%(message)s')

log_samp_file_handler = logging.FileHandler("logs/samples.csv")
log_samp_file_handler.setLevel(logging.INFO)
log_samp_file_handler.setFormatter(log_samp_formatter)

samp_logger = logging.getLogger("samples")
samp_logger.addHandler(log_samp_file_handler)
samp_logger.propagate = False


class App:
  def __init__(self, mode = None):
    self.config = None
    self.debug_i = -1
    self.fingerprint_counter = 0
    self.fingerprint_limit = 0
    self.mode = mode
    self.sample_duration = 0
    self.sample_period = 0
    self.sample_threshold = 100

    # Version
    version = "0.1.0"
    with open("version.txt") as f:
      version = f.read()
    os.environ["BUTLER_VERSION"] = version
  
      # Config
    config = {}
    with open("config.json") as f:
      raw_config = f.read()
      self.config = json.loads(raw_config)

  def init(self):
    rc = 0

    config_a = self.config.get("app", {})
    config_f = self.config.get("fingerprinting", {})
    config_i = self.config.get("interface", {})
    config_s = self.config.get("sampling", {})

    self.mode = self.mode or config_a.get("mode", "record")
    self.sample_threshold = config_a.get("threshold", SAMPLE_THRESHOLD_RMS)

    self.fingerprint_limit = config_f.get("limit", self.fingerprint_limit)

    self.sample_duration = config_s.get("length", SAMPLE_DURATION_SEC)
    self.sample_period = config_s.get("period", SAMPLE_PERIOD_SEC)

    if (self.mode == "record"):

      self.sampler = Sampler(
        interface_name = config_i.get("name"),
        sample_duration = self.sample_duration,
        channels = config_i.get("channels"),
        sample_format = config_i.get("sample_format"),
        sample_rate = config_i.get("sample_rate"),
      )
      rc = self.sampler.init()
  
    if (rc > 0):
      logger.critical('Failed to initialize sampler')
      exit()
  
    self.fp = Fingerprinter(FINGERPRINT_API_KEY)
    self.fm = Scrobbler(LASTFM_API_KEY, LASTFM_SECRET, LASTFM_SESSION_KEY)
    self.mn = Monitor(self.fm, SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)


  def run(self):
    self.init()

    while(True):
      self.debug_i += 1
      sample = Sample()

      if (self.mode == "record"):
        logger.info(f'Recording sample')
        self.sampler.record()
        self.sampler.save(SAMPLE_FILENAME)
      
      # Calculate RMS
      wav = wave.open(SAMPLE_FILENAME)
      frames = wav.readframes(256)
      rms = audioop.rms(frames, 2)
      wav.close()
      sample.rms = rms
      
      msg = f'{self.debug_i}; {rms};'

      if (sample.rms < self.sample_threshold):
        samp_logger.info(msg)
        continue

      # Fingerprint
      if (self.fingerprint_counter >= self.fingerprint_limit - 1):
        logger.error(f'Fingerprinting count ({self.fingerprint_counter + 1}) exceeded limit ({self.fingerprint_limit})')
        continue

      res = self.fp.run(SAMPLE_FILENAME)
      self.fingerprint_counter += 1

      status = res.get("status") == "success"
      result = res.get("result")

      if (not status):
        logger.error(f'Failed to fingerprint sample')
    
      elif (not result):
        logger.info('No track detected by fingerprinter')
        samp_logger.info(msg)

      else:
        # Scrobble
        sample.from_json(result)
        msg = f"{self.debug_i}; {rms}; {sample.artist}; {sample.track}; {sample.timecode}; {sample.track_number}; {sample.album_n_tracks}; {sample.album}"
        samp_logger.info(msg)
        logger.info(msg)

        self.mn.run(sample)

      logger.info(f'Sleeping for {self.sample_period - self.sample_duration} sec')
      sleep(self.sample_period - self.sample_duration)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Process some integers.')
  parser.add_argument('--mode', nargs=1, help='mode - record | sample')
  args = parser.parse_args()

  app = App(mode=args.mode[0])
  app.run()