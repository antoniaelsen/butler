# Butler

butler is a collection of scripts for recording, fingerprinting, and scrobbling audio from an audio interface.

It has been tested on a Raspberry Pi 3 running Raspbian (buster), receiving audio from an ATH-LP120USB

## TODO

- [x] Audio fingerprinting
- [ ] ISRC comparisons
- [x] Scrobbling
  - [x] Last FM request formatting
  - [x] Signature
  - [x] Redirect to browser
  - [x] User agent
- [ ] Detect audio levels, trigger fingerprinting on new song
- [x] Logging
- [ ] Database
- [ ] Containerize
- [x] Configuration files
  - [ ] Interface configuration
  - [ ] Scrobbling configuration
- [ ] Reporting
- [ ] Validating and parsing JSON
- [ ] Make service agnostic

## About

Fingerprinter passes information to the scrobbler; track, artist, album, timecode, and ISRC.

The fingerprinter may have correctly identified the track and artist, but the album returned by the fingerprinter may not correspond to the album being sampled from.

A monitor tracks the fingerprinted songs, using their ISRC to look up their possible track permutations.

## Configuration

- FINGERPRINT_API_KEY - [audd.io](audd.io) API key ($5/month)
- LASTFM_API_KEY
- LASTFM_SECRET
- LASTFM_SESSION_KEY


## Author

Antonia Elsen
haebou @ github