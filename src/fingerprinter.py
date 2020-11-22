import logging
import json
import requests


logger = logging.getLogger(__name__)

class Fingerprinter:
  def __init__(self, api_key):
    self.api_key = api_key
  
  def run(self, filename):
    logger.debug('Fingerprinting')    

    file = open(filename, 'rb')

    files = {
        'file': file,
    }
    data = {
        'api_token': self.api_key,
        'files': files,
        'return': 'spotify',
    }

    raw = requests.post('https://api.audd.io/', data=data, files=files)
    res = raw.json()
  
    file.close()
  
    logger.debug(f'Fingerprint response {json.dumps(res, indent=2)}');
  
    if (res["status"] != "success"):
      logger.error(f'Failed to fingerprint sample');

    return res
