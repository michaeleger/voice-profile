# voice-profile

Measure how each speaker in a podcast recording actually sounds, and get concrete EQ, de-esser and loudness settings to fix it.

## Why

Mixing a remote interview usually means guessing: is the guest boomy or is the room boxy? Is that harshness sibilance or presence? voice-profile measures each speaker separately (using the transcript's timings), compares their spectrum to a typical voice, and writes plain recommendations such as "HPF 85 Hz, -2 dB bell at 160 Hz, de-esser 6.8 kHz at -31 dBFS". It also detects when Riverside's Magic Audio has already processed the track, so you don't stack EQ on EQ.

Built for the [Eager to Be Healthy](https://www.eagertobehealthy.com) podcast.

## What it does

- Per speaker (with an aligned transcript) or whole file:
  - integrated loudness (LUFS), true peak (4x oversampled), loudness range (LRA, via ffmpeg ebur128)
  - noise floor, speech RMS, clipped samples, digital-silence fraction
  - band energy and deviation from a voice reference: rumble <80 Hz, boom 80-200, mud 200-500, boxy 500-1k, 1-2k, presence 2-5k, sibilance 5-9k, air 10k+
  - peak frequencies (boom, mud, presence, sibilance) and sibilance percentiles
- Writes `metrics.json`, `spectrum.png`, one WAV per speaker, `recommendations.md` and `recommendations.json`.

**Status:** alpha. It works and is used per episode, but the rules are tuned on a small number of sessions.

## Requirements

- Linux or macOS, Python 3.10+
- `ffmpeg` on your PATH (needed for LRA)
- Python packages: numpy, scipy, librosa, matplotlib, soundfile, pyloudnorm

## Install

```bash
git clone https://github.com/michaeleger/voice-profile.git
cd voice-profile
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ffmpeg -version        # make sure it's installed (sudo apt install ffmpeg / brew install ffmpeg)
bin/voice-profile --help
```

Optional: `ln -s "$PWD/bin/voice-profile" ~/.local/bin/voice-profile` to run it from anywhere.

## Usage

```bash
# Per speaker, using a Riverside aligned transcript (JSON with word timings)
bin/voice-profile analyze EXPORT.wav --speakers aligned_transcript.json --out out/EPISODE

# Whole file (no speaker split)
bin/voice-profile analyze EXPORT.wav --out out/EPISODE

# Re-run only the recommendation rules on existing metrics
bin/voice-profile recommend out/EPISODE/metrics.json
```

`analyze` runs `recommend` automatically (`--no-recommend` skips it). Output defaults to `out/<wav name>`.

## The rules (`voice_profile/recommend.py`)

- High-pass at 80-90 Hz, always.
- Boom more than 1.5 dB over reference: -2 dB bell at the boom peak.
- Boxy more than 1 dB over: -1.5 dB at 700 Hz.
- Presence more than 4 dB over: -1.5 dB (or -2 dB if more than 5) at the presence peak.
- De-esser at 6.5-7 kHz, threshold at sibilance p95. Add a narrow de-esser at the loudest sibilance frequency if sibilance is more than 6 dB over.
- Loudness target -16 LUFS, limiter at -1 dBTP.
- Magic Audio detection (2 of 3: true digital silence in gaps, a hard ceiling near -2 dBTP, rumble already cut): if detected, turn Magic Audio off before manual EQ.

Edit the thresholds in `recommend.py` to suit your own voice and room.

## Limitations

- The reference voice curve is generic. It is a starting point, not a target.
- Getting audio out of Riverside is manual: its API gives no download URL, so download the WAV and the aligned transcript from the dashboard.
- No sample audio is included in this repo (it would be real guests' voices). Use your own recording.
- No automated tests yet.

## License

MIT. See [LICENSE](LICENSE).
