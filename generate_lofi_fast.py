import numpy as np
import wave

sample_rate = 22050
duration = 45.0
num_samples = int(sample_rate * duration)
t = np.linspace(0, duration, num_samples, endpoint=False)

bpm = 80
beat_dur = 60.0 / bpm
bar_dur = beat_dur * 4

# 4 warm jazzy chords: Fmaj7 (F3, A3, C4, E4), Dm7 (D3, F3, A3, C4), Gm7 (G3, Bb3, D4, F4), C7 (C3, E3, G3, Bb3)
chord_freqs = [
    [174.61, 220.00, 261.63, 329.63],
    [146.83, 174.61, 220.00, 261.63],
    [196.00, 233.08, 293.66, 349.23],
    [130.81, 164.81, 196.00, 233.08],
]

audio = np.zeros(num_samples, dtype=np.float32)

# Generate chords in vectorized chunks
for bar_idx in range(int(duration / bar_dur) + 1):
    bar_start_t = bar_idx * bar_dur
    bar_end_t = min(bar_start_t + bar_dur, duration)
    start_idx = int(bar_start_t * sample_rate)
    end_idx = int(bar_end_t * sample_rate)
    if start_idx >= num_samples:
        break
    
    t_chunk = t[start_idx:end_idx]
    chunk_len = len(t_chunk)
    chord = chord_freqs[bar_idx % len(chord_freqs)]
    
    # Envelope with soft attack and decay
    t_rel = (t_chunk - bar_start_t) / bar_dur
    env = np.sin(np.pi * np.clip(t_rel, 0, 1)) ** 0.8
    
    chord_sig = np.zeros(chunk_len, dtype=np.float32)
    for f in chord:
        # fundamental + soft harmonics
        chord_sig += 0.35 * np.sin(2 * np.pi * f * t_chunk)
        chord_sig += 0.15 * np.sin(2 * np.pi * f * 2 * t_chunk)
        chord_sig += 0.05 * np.sin(2 * np.pi * f * 3 * t_chunk)
        
    audio[start_idx:end_idx] += chord_sig * env * 0.45

# Add gentle drum groove (kick on 1, 3&, snare on 2, 4)
for b in range(int(duration / beat_dur)):
    bt = b * beat_dur
    idx = int(bt * sample_rate)
    step = b % 4
    
    # Kick on step 0 and 2.5
    if step == 0 and idx + int(0.18 * sample_rate) < num_samples:
        k_len = int(0.18 * sample_rate)
        kt = np.linspace(0, 0.18, k_len)
        kick = 0.45 * np.sin(2 * np.pi * 65 * np.exp(-kt * 18) * kt) * np.exp(-kt * 16)
        audio[idx:idx+k_len] += kick
        
    # Snare on steps 1 and 3
    if step in [1, 3] and idx + int(0.15 * sample_rate) < num_samples:
        s_len = int(0.15 * sample_rate)
        st = np.linspace(0, 0.15, s_len)
        snare = (0.2 * np.random.normal(0, 1, s_len) + 0.15 * np.sin(2 * np.pi * 190 * st)) * np.exp(-st * 28)
        audio[idx:idx+s_len] += snare

# Add soft tape hiss / vinyl warmth
audio += np.random.normal(0, 0.008, num_samples)

# Normalize
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = (audio / max_val) * 0.82

with wave.open("lofi_track.wav", "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes((audio * 32767).astype(np.int16).tobytes())

print("Fast vectorized lo-fi audio generated: lofi_track.wav")
