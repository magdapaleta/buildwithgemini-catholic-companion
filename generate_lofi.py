import numpy as np
import wave
import struct

sample_rate = 44100
duration = 45.0  # 45 seconds of audio
num_samples = int(sample_rate * duration)

# Lo-fi Chord Progression (Key of Eb Major / C minor chill: Abmaj7 - Gm7 - Fm7 - Bb7)
# Frequencies in Hz
chords = [
    [207.65, 261.63, 311.13, 392.00],  # Abmaj7: Ab3, C4, Eb4, G4
    [196.00, 233.08, 293.66, 349.23],  # Gm7: G3, Bb3, D4, F4
    [174.61, 207.65, 261.63, 311.13],  # Fm7: F3, Ab3, C4, Eb4
    [233.08, 293.66, 349.23, 415.30],  # Bb7: Bb3, D4, F4, Ab4
]

bpm = 75
beat_sec = 60.0 / bpm
chord_dur = beat_sec * 4  # 4 beats per chord

t = np.linspace(0, duration, num_samples, endpoint=False)
audio_left = np.zeros(num_samples)
audio_right = np.zeros(num_samples)

# Vinyl / Tape crackle / warmth noise
np.random.seed(42)
crackle = np.random.normal(0, 0.015, num_samples)
# Filter crackle softly
b, a = [0.05], [1.0, -0.95]
from scipy.signal import lfilter
try:
    crackle_filtered = lfilter(b, a, crackle)
except:
    crackle_filtered = crackle * 0.5

audio_left += crackle_filtered
audio_right += crackle_filtered

# Generate Rhodes/Electric Piano Chords with warm low-pass harmonics
for i in range(num_samples):
    cur_time = t[i]
    chord_idx = int((cur_time / chord_dur) % len(chords))
    notes = chords[chord_idx]
    
    # Envelope per chord bar (soft attack, sustained, gentle decay)
    bar_pos = (cur_time % chord_dur) / chord_dur
    env = np.sin(np.pi * np.clip(bar_pos * 1.05, 0, 1)) ** 0.8
    
    # Slight detune / vibrato (tape wow and flutter)
    wow = 1.0 + 0.003 * np.sin(2 * np.pi * 0.4 * cur_time)
    
    sig = 0.0
    for n in notes:
        freq = n * wow
        # Fundamental + gentle 2nd and 3rd harmonics
        sig += 0.45 * np.sin(2 * np.pi * freq * cur_time)
        sig += 0.20 * np.sin(2 * np.pi * freq * 2 * cur_time)
        sig += 0.08 * np.sin(2 * np.pi * freq * 3 * cur_time)
    
    # Stereo panning width
    audio_left[i] += sig * env * 0.22
    audio_right[i] += sig * env * 0.24

# Lo-fi Drum Beat (Boom-bap chill kick, rimshot snare, shuffly hi-hat)
sixteenth = beat_sec / 4.0
for beat in range(int(duration / sixteenth)):
    beat_t = beat * sixteenth
    idx = int(beat_t * sample_rate)
    step = beat % 16
    
    # Kick on steps 0, 10
    if step in [0, 10] and idx + int(0.25 * sample_rate) < num_samples:
        k_len = int(0.25 * sample_rate)
        kt = np.linspace(0, 0.25, k_len)
        k_pitch = 110.0 * np.exp(-kt * 22) + 45.0
        phase = 2 * np.pi * np.cumsum(k_pitch) / sample_rate
        k_env = np.exp(-kt * 14)
        kick = 0.4 * np.sin(phase) * k_env
        audio_left[idx:idx+k_len] += kick
        audio_right[idx:idx+k_len] += kick
        
    # Snare / Rimshot on steps 4, 12
    if step in [4, 12] and idx + int(0.2 * sample_rate) < num_samples:
        s_len = int(0.2 * sample_rate)
        st = np.linspace(0, 0.2, s_len)
        s_env = np.exp(-st * 24)
        snare = 0.22 * np.random.normal(0, 1, s_len) * s_env + 0.15 * np.sin(2 * np.pi * 180 * st) * s_env
        audio_left[idx:idx+s_len] += snare * 0.9
        audio_right[idx:idx+s_len] += snare * 1.1

    # Hi-hat on every 2 steps (8th notes with subtle swing)
    if step % 2 == 0 and idx + int(0.08 * sample_rate) < num_samples:
        h_len = int(0.08 * sample_rate)
        ht = np.linspace(0, 0.08, h_len)
        h_env = np.exp(-ht * 55)
        hat = 0.09 * np.random.normal(0, 1, h_len) * h_env
        audio_left[idx:idx+h_len] += hat * 1.05
        audio_right[idx:idx+h_len] += hat * 0.95

# Normalize audio
max_val = max(np.max(np.abs(audio_left)), np.max(np.abs(audio_right)))
if max_val > 0:
    audio_left = (audio_left / max_val) * 0.85
    audio_right = (audio_right / max_val) * 0.85

# Convert to 16-bit PCM WAV
wav_file = "lofi_background.wav"
with wave.open(wav_file, "w") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    interleaved = np.empty((num_samples * 2,), dtype=np.int16)
    interleaved[0::2] = (audio_left * 32767).astype(np.int16)
    interleaved[1::2] = (audio_right * 32767).astype(np.int16)
    wf.writeframes(interleaved.tobytes())

print(f"Generated upbeat chill lo-fi background track: {wav_file} ({duration}s)")
