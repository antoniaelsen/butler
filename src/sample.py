class Sample:
  def __init__(self, json = None):
    self.rms = None

    self.album = None
    self.artist = None
    self.isrc = None
    self.timecode = None
    self.track = None
    self.track_number = None

    if (json):
      self.from_json(json)

  def from_json(self, json):
    spotify = json["spotify"]

    self.album = json["album"]
    self.album_n_tracks = spotify["album"]["total_tracks"]
    self.artist = json["artist"]
    self.timecode = json["timecode"]
    self.track = json["title"]
    self.track_number = spotify["track_number"]
    self.isrc = spotify["external_ids"]["isrc"]

