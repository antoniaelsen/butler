import logging
import pyaudio
import wave


FRAME_SIZE = 256
RECORD_SECONDS = 15
SAMPLE_FORMATS = {
    8: pyaudio.paInt8,
    16: pyaudio.paInt16,
    24: pyaudio.paInt24,
    32: pyaudio.paInt32,
}

logger = logging.getLogger(__name__)


class Sampler:
  def __init__(
      self,
      interface_name,
      channels = 2,
      sample_format = 16,
      sample_rate = 44100,
      sample_duration=RECORD_SECONDS
    ):
    logger.debug("Initializing sampler")
    self.channels = channels
    self.interface_name = interface_name
    self.sample_duration = sample_duration
    self.sample_format = SAMPLE_FORMATS[sample_format]
    self.sample_rate = sample_rate

    self.p = pyaudio.PyAudio()
    self.frames = []
    self.interfaces = {}
    self.interface_index = None

    self.init()
    logger.debug(f' - Input device: [{self.interface_index}] "{self.interfaces[self.interface_index]}"')
    logger.debug(f" - Sample Format: {self.sample_format}")
    logger.debug(f" - Sample Rate: {self.sample_rate} kHz")
    logger.debug(f" - Frame Size: {FRAME_SIZE} samples")
    logger.debug(f" - Recording time: {self.sample_duration} secs")

  def __del__(self):
    self.p.terminate()

  def init(self):
    logger.debug("Initializing interfaces...")
    logger.debug(" - audio devices:")
    for i in range(self.p.get_device_count()):
      name = self.p.get_device_info_by_index(i).get("name")
      self.interfaces[i] = name
      logger.debug(f'   - [{i}]: {name}')

      if (self.interface_name in name):
        self.interface_index = i

    if (self.interface_index == None):
      logger.critical(f'Failed to find audio input device "{self.interface_name}"')
      return 1

    return 0

  def record(self):
    logger.info(f'Recording sample...')

    self.frames.clear()
    stream = self.p.open(
        channels=self.channels,
        format=self.sample_format,
        frames_per_buffer=FRAME_SIZE,
        input=True,
        input_device_index=0,
        rate=self.sample_rate
    )

    for i in range(0, int(self.sample_rate / FRAME_SIZE * self.sample_duration)):
        data = stream.read(FRAME_SIZE)
        self.frames.append(data)

    stream.stop_stream()
    stream.close()

    logger.info('Successfully recorded sample')

  def save(self, filename):
    output = wave.open(filename, 'wb')

    output.setnchannels(self.channels)
    output.setsampwidth(self.p.get_sample_size(self.sample_format))
    output.setframerate(self.sample_rate)

    output.writeframes(b''.join(self.frames))
    output.close()
    logger.debug(f'Sample file saved')

