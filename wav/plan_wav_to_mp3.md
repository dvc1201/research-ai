# Plan: `wav_to_mp3.py` — MP3 assembly & timeline merge

**Date:** 2026-08-27
**Status:** Active
**Platform:** Windows only
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Overview

`wav_to_mp3.py` is the **second stage** of the audio pipeline. It reads a
hand-authored control file, converts the referenced WAVs to MP3 (cached),
assembles them into one timed MP3 with computed silence gaps, and optionally
prepends an intro MP3.

```
control file (manual)            wav_to_mp3.py                    output
──────────────────────   ──────────────────────────────   ──────────────────────
yang85pigua.properties ───────────────────────▶           yang85_pigua.mp3
  form=yang85form.properties                                (+ timeline .txt)
  intro=pigua.mp3
  formlength=480
```

The first stage (`gen_audio.py`) produces the WAVs this script consumes —
see `plan_gen_audio.md`.

## File roles (all manual inputs)

| File | Created | Purpose |
|---|---|---|
| `<name>form.properties` | manually | `wav_filename=weight` pairs (form definition) |
| `<name>_*.properties` | manually | high-level control (paths, `form=`, `intro=`, `formlength=`) |
| intro MP3 (e.g. `pigua.mp3`) | manually | optional audio prepended before the form |

## Usage

```powershell
.\.venv\Scripts\python.exe wav_to_mp3.py <control>.properties [--force] [--cache-dir <path>]
```

- Positional: path to the control `.properties` file.
- `--force`: ignore the MP3 cache and reconvert all WAVs.
- `--cache-dir` (optional): override the default cache location.

## Control file format (modular)

```properties
input_dir=G:\My Drive\Peter\Taichi\Confucius4\yang85\edgetts
output_dir=G:\My Drive\Peter\Taichi\Confucius4\yang85\mp3
bitrate=192k
form=yang85form.properties          # points to form definition
intro=pigua.mp3                     # optional, prepended before form
output_filename=yang85_pigua.mp3    # optional; defaults to <stem>.mp3
formlength=480                      # form seconds, EXCLUDES intro
```

### Config keys

| Key | Required | Description |
|---|---|---|
| `input_dir` | ✅ | Directory containing source WAV files |
| `output_dir` | ✅ | Directory for the final MP3 |
| `bitrate` | ✅ | MP3 bitrate (`192k` used throughout this project) |
| `formlength` | ✅ | Target form duration in seconds (intro excluded) |
| `form` | ❌ | Form definition file, relative to the control file |
| `intro` | ❌ | Intro MP3, relative to the control file |
| `output_filename` | ❌ | Defaults to `<control_stem>.mp3` |
| `cache_dir` | ❌ | Defaults to `<input_dir>/mp3cache` |

### Two modes

- **Modular** — `form=` present: tracks are loaded from the referenced form
  file; track-like lines in the control file are ignored.
- **Legacy unified** — no `form=`: tracks are loaded directly from the
  control file (config + weighted tracks in one file, e.g.
  `yang85.properties`). Still supported for backward compatibility.
  > Note: the even older `yang42.properties` (start-time-based, no
  > `formlength`) is **not** a valid input for the current script.

## Form definition file format

```properties
# Section 1
85_01.wav=10
85_02.wav=5
85_03_lrtail.wav=18
```

- Only `wav_filename=weight` pairs (weight is a relative timing unit).
- Config keys are tolerated but ignored (the form file is expected to be
  clean; tolerance guards against copy/paste leftovers).

## Timing model

For N tracks with weights `w[i]` and total form length `F`:

```
total_weight = Σ w[i]
time_per_weight = F / total_weight
start[i] = Σ w[j] × time_per_weight   (j < i)
```

- Silence before track `i` = `start[i] − (start[i−1] + duration[i−1])`.
- Negative silence (overlap) aborts with a diagnostic.
- `formlength` applies to the **form only**; the intro is prepended and its
  duration is not part of the 480 s (or whatever `formlength` is) target.

## MP3 conversion cache

Conversion is a **one-time** action; merges are repeatable at near-zero cost.

- Location: `<input_dir>/mp3cache/` (dedicated subfolder; confirmed OK to
  live on Google Drive).
- Cache file: `<wav_stem>.mp3`.
- Reconvert a track only when:
  1. the cached MP3 is missing, or
  2. `wav.mtime > cached_mp3.mtime`, or
  3. `--force` is passed.
- Bitrate is always `192k`, so no bitrate key is needed in the cache name.

### Merge flow

```
parse control + tracks
   → ensure_cache (convert missing/stale WAVs only)
   → build_timeline from cache
   → validate_overlap
   → prepend intro (if present)
   → export final MP3
```

No per-run temp directory; nothing is deleted after a run.

## Output

- Final MP3 written to `output_dir/<output_filename>`.
- Companion timeline `.txt` written next to it (filename → start time).
  Start times are in `mm:ss` format (truncated seconds) to match audio player
  displays, and are offset by the intro duration when one is present, so the
  `.txt` file reflects the actual position in the final MP3.

## Error handling

| Scenario | Handling |
|---|---|
| Missing/extra CLI arguments | argparse prints usage, exit code 2 |
| Control file not found | Print error, exit 1 |
| Missing required config key | Report key, exit 1 |
| `formlength` not positive | Report value, exit 1 |
| Invalid bitrate format | Report value, exit 1 |
| Form file not found | Report path, exit 1 |
| Intro file not found | Report path, exit 1 |
| WAV missing from `input_dir` | Report path + track, exit 1 |
| Track overlap | Report both tracks + overlap amount, exit 1 |
| ffmpeg/ffprobe not on PATH | Install hint, exit 1 |
| Corrupted WAV / MP3 | `pydub` exception propagates |

## Testing approach

1. Fresh run (cold cache) → all WAVs converted; output correct.
2. Second run (warm cache) → 0 converted; output identical.
3. Touch one WAV → only that track reconverts.
4. `--force` → all reconvert.
5. Delete cache dir → behaves like fresh run.
6. Legacy unified control file still works.
7. Modular file with `intro=` prepends intro correctly.
