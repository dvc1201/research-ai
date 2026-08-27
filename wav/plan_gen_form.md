# Plan: `gen_form.py` — MP3 assembly & timeline merge

**Date:** 2026-08-27
**Status:** Planned
**Platform:** Windows only
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Purpose

`gen_form.py` assembles named MP3 posture files into a single timed MP3 with
computed silence gaps between cues. It is the second stage of the MP3-native
pipeline: `gen_audio.py` produces the MP3 clips, `gen_form.py` merges them
into a practice audio with an optional intro.

No WAV-to-MP3 conversion and no caching are performed — the source files
are already MP3 at whatever bitrate the generator produced (the pipeline does
not normalize bitrate at the source stage). The only encode step is the
single final export: the merged audio is decoded in memory and re-encoded
once as MP3 at a fixed 192 kbps.

## CLI

```powershell
.\.venv\Scripts\python.exe gen_form.py <control>.properties
```

- One positional argument: the control file.
- No flags.

## Inputs (all hand-authored)

| File | Purpose |
|---|---|
| Control file `<name>_*.properties` | Paths and assembly settings (below) |
| Form definition `<name>form.properties` | Ordered `mp3_filename=weight` pairs |
| Intro MP3 (optional) | Audio prepended before the merged form |

## Control file format

```properties
input_dir=G:\My Drive\Peter\Taichi\yang85\edgetts
output_dir=G:\My Drive\Peter\Taichi\yang85\mp3
form=yang85form.properties           # form definition, relative to CWD
intro=pigua.mp3                      # optional intro, relative to CWD
output_filename=yang85_pigua.mp3     # mandatory output name
formlength=480                       # target form seconds (intro excluded)
```

### Keys

| Key | Required | Meaning |
|---|---|---|
| `input_dir` | Yes | Directory containing the source MP3 files |
| `output_dir` | Yes | Directory for the merged output MP3 |
| `form` | Yes | Form definition file path (relative to CWD) |
| `output_filename` | Yes | Output MP3 filename — no fallback |
| `formlength` | Yes | Target form duration in seconds, intro excluded |
| `intro` | No | Intro MP3 path (relative to CWD) |

- Relative paths are resolved against the current working directory.
- Values may be quoted (`"..."`); surrounding quotes are stripped.
- `bitrate` is not a control-file key; the output is always encoded at
  a fixed 192 kbps.
- No other keys are read; a non-recognised key in the control file is
  ignored.

## Form definition format

```properties
# Section 1
85_01.mp3=10
85_02.mp3=5
85_03_lrtail.mp3=18
```

- Each line is `filename=weight`; the key is the MP3 filename in `input_dir`.
- The weight is a relative timing unit (any non-negative number).
- Blank lines and `#` comments are ignored.
- Files are processed in declaration order.
- A duplicate filename aborts the run.
- A weight that is not a number, or is negative, aborts the run.
- At least one track with a non-zero total weight is required (the weights
  must not sum to zero).

## Timing model

Given N tracks with weights `w[i]` and target form length `F`:

```
total_weight    = sum(w[i])
time_per_weight = F / total_weight
start[i]        = sum(w[j] for j < i) * time_per_weight
```

- `start[0]` is 0 by definition.
- The gap (silence) before track `i` is
  `start[i] − (start[i−1] + duration[i−1])`; a negative value means the
  tracks overlap and the run aborts.
- `formlength` covers the form only. The intro is prepended before `start[0]`
  and does not count toward `F`.

## Processing flow

1. Parse the control file into a config dict and validate the required keys.
2. Parse the form definition into an ordered track list (filename, weight).
3. Compute `start_sec` for every track from the weights and `formlength`.
4. Verify every referenced MP3 exists in `input_dir`; abort on the first
   missing file.
5. Load each MP3, record its duration, and validate no overlaps.
6. Build the timeline: insert silence of the computed gap length before each
   clip, then append the clip.
7. If `intro` is present, load it and prepend it to the timeline.
8. Export the assembled audio as MP3 (constant 192 kbps) to
   `output_dir/<output_filename>`.
9. Write a companion timeline file `output_dir/<output_filename>.txt`.
10. Print a summary of the assembled timeline.

## Output

### MP3

One merged MP3 at `output_dir/<output_filename>`, encoded at 192 kbps.

### Timeline `.txt`

Written next to the MP3, same stem, `.txt` extension:

```
# Timeline for yang85_pigua.mp3
# Format: filename  start_time

85_01.mp3  0:07
85_02.mp3  0:12
```

- `start_time` uses `mm:ss` (seconds truncated to whole values).
- All start times include the intro offset, so they reflect the actual
  position in the final MP3.

## Console summary

```
Timeline assembled:
  [0:07]  85_01.mp3               (w:  10  clip: 1.9s  gap:  0.0s)
  [0:12]  85_02.mp3               (w:   5  clip: 2.3s  gap:  3.6s)
  ...
Total duration: 487.0s  (8:07)
Total weight: 875
Form length (target): 480s
Output: ...\yang85_pigua.mp3
```

- `clip` is the measured duration of the MP3.
- `gap` is the silence inserted before the clip.
- `Total duration` includes the intro.

## Error handling

| Scenario | Handling |
|---|---|
| Wrong argument count | Print usage, exit 1 |
| Control file not found | Print error, exit 1 |
| Required key missing | Print the missing key, exit 1 |
| `formlength` not a positive number | Print error, exit 1 |
| Form file not found | Print path, exit 1 |
| Intro file not found | Print path, exit 1 |
| Duplicate track filename | Print filename, exit 1 |
| Non-numeric or negative weight | Print line info, exit 1 |
| Total weight is zero | Print error, exit 1 |
| MP3 missing from `input_dir` | Print path and track, exit 1 |
| Track overlap | Print both tracks and overlap amount, exit 1 |
| ffmpeg/ffprobe missing | Print install hint, exit 1 |
| Corrupted MP3 | Exception propagates |

## Environment

- Python 3.12 (see project README).
- `pydub` (with `ffmpeg`/`ffprobe` on PATH).
- FFmpeg is located via the standard Gyan build path and prepended to PATH at
  startup.

## Acceptance criteria

- Running `gen_form.py yang85pigua.properties` produces `yang85_pigua.mp3`
  and `yang85_pigua.txt` in `output_dir`.
- The first track in the `.txt` starts at the intro duration (or `0:00` when
  no intro is given).
- Timeline times are in `mm:ss` and match the actual MP3 positions.
- The merged form duration matches `formlength` (within clip-duration
  rounding), excluding the intro.
