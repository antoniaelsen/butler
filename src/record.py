import pyaudio
import wave

# TODO
# - Logging
# - Load config yaml / json for
#   - interface name, interface configuration
# - Chunk size calculation

INTERFACE_NAME = "USB AUDIO CODEC"
INTERFACE_INDEX = 0
CHUNK = 256
CHANNELS = 2
SAMPLE_FORMAT = pyaudio.paInt16
SAMPLE_RATE = 44100
RECORD_SECONDS = 10
OUTPUT_FILENAME = "output.wav"

frames = []
interfaces = {}
p = pyaudio.PyAudio()

print("Audio devices:")
for i in range(p.get_device_count()):
    name = p.get_device_info_by_index(i).get("name")
    interfaces[i] = name
    print(f'- [{i}]: {name}')

    if (INTERFACE_NAME in name):
        INTERFACE_INDEX = i

stream = p.open(
    format=SAMPLE_FORMAT,
    channels=CHANNELS,
    rate=SAMPLE_RATE,
    input=True,
    input_device_index=0,
    frames_per_buffer=CHUNK)

print(f'Recording...')
print(f' - Input device: [{INTERFACE_INDEX}] "{interfaces[INTERFACE_INDEX]}"')
print(f" - Sample Rate: {SAMPLE_RATE} kHz")
print(f" - Chunk Size: {CHUNK} samples")
print(f" - Recording time: {RECORD_SECONDS} secs")

section = int(SAMPLE_RATE / CHUNK * RECORD_SECONDS)
for i in range(0, section):
    data = stream.read(CHUNK)
    frames.append(data)

print(f'- recording finished')

stream.stop_stream()
stream.close()
p.terminate()

print(f'Saving recording')
output = wave.open(OUTPUT_FILENAME, 'wb')

output.setnchannels(CHANNELS)
output.setsampwidth(p.get_sample_size(SAMPLE_FORMAT))
output.setframerate(SAMPLE_RATE)

output.writeframes(b''.join(frames))
output.close()
print(f' - file saved')