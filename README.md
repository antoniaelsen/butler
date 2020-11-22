# Butler

butler is a collection of scripts for recording, fingerprinting, and scrobbling audio from an audio interface.

It has been tested on a Raspberry Pi 3 running Raspbian (buster), receiving audio from an ATH-LP120USB

## TODO

- [x] Audio fingerprinting
- [ ] ISRC comparisons
- [ ] ISRC lookup of album
- [x] Scrobbling
  - [x] Last FM request formatting
  - [x] Signature
  - [x] Redirect to browser
  - [x] User agent
- [ ] Detect audio levels, trigger fingerprinting on new song
- [x] Logging
- [x] Configuration files
  - [ ] Interface configuration
  - [ ] Scrobbling configuration
- [ ] Reporting
- [ ] Make service agnostic

## About

Fingerprinter passes information to the scrobbler; track, artist, album, timecode, and ISRC.

The fingerprinter may have correctly identified the track and artist, but the album returned by the fingerprinter may not correspond to the album being sampled from.

A monitor tracks the fingerprinted songs, using their ISRC to look up their possible track permutations.


## Author

Antonia Elsen
haebou @ github