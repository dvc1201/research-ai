# Plan: WAV → MP3 Batch Converter & Timeline Merger

**Date:** 2026-07-10  
**Status:** Active  
**Platform:** Windows only  
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Overview

Build a Python script that:
1. Reads a single named `.properties` file passed as the only CLI argument (e.g. `yang42.properties`, `chen18.properties`)
2. Parses runtime config (`input_dir`, `output_dir`, `bitrate`) **and** the track timeline (`filename = start_sec`) from that one file
3. Converts each listed WAV file to MP3
4. Assembles all MP3s into one final MP3 at the exact start times defined in the file
5. Inserts the correct amount of silence between tracks so each clip starts at its defined timestamp
6. Names the output MP3 after the input properties file (e.g. `yang42.properties` → `yang42.mp3`)

### Key Design Decisions
- **One file for everything** — `yang42.properties` contains both runtime config keys and the track timeline; no separate `tracklist.properties`
- **Config keys** are the well-known set: `input_dir`, `output_dir`, `bitrate`; all other keys are treated as track entries (`filename = start_sec`)
- **Silence is calculated** as: `silence_duration = start_time[n] - (start_time[n-1] + duration[n-1])`; if this value is negative, the script raises an error (overlapping tracks are not allowed)
- **The first track may start at any time ≥ 0** — a leading silence is inserted before it if `start_sec > 0`
- **Intermediate MP3 files are always deleted** after the final MP3 is exported
- **Output MP3 name is derived from the input properties filename** — `yang42.properties` → `yang42.mp3`
- **Single argument:** `python wav_to_mp3.py yang42.properties`
- **No ordering strategy needed** — order is determined by the float values (start times) after parsing

---

## Phase 1 — Environment & Dependency Setup

### Status: ✅ Complete (2026-07-10)

| Component | Version | Install method |
|---|---|---|
| Python | 3.12.10 | `winget install Python.Python.3.12` |
| FFmpeg | 8.1.2-full_build (Gyan) | `winget install Gyan.FFmpeg` |
| FFprobe | 8.1.2-full_build (Gyan) | bundled with FFmpeg |
| pydub | 0.25.1 | pip into `.venv` |
| tqdm | 4.68.4 | pip into `.venv` |
| Venv | `C:\work\github\research-ai\wav\.venv` | Python 3.12 |
| requirements.txt | `C:\work\github\research-ai\wav\requirements.txt` | `pip freeze` |

> **⚠️ Python 3.13 warning:** `pydub` 0.25.1 uses `audioop` which was removed in Python 3.13. Use Python 3.12 or 3.11.

### Original Tasks (for reference)
1. Install **Python 3.12** (3.10+ required; 3.12 recommended due to `pydub`/`audioop` compatibility)
2. Install **FFmpeg** (Windows):
   - `winget install --id=Gyan.FFmpeg`
   - FFmpeg bin added to user `PATH`: `%LOCALAPPDATA%\...\ffmpeg-8.1.2-full_build\bin`
3. Create a virtual environment: `python -m venv .venv`
4. Install Python libraries: `pip install pydub tqdm`
5. Pin dependencies: `pip freeze > requirements.txt`

### Dependencies
- `pydub` → requires `ffmpeg.exe` and `ffprobe.exe` in PATH (Windows)
- No extra sorting library needed — ordering is determined by sorting float start-time values after parsing

---

## Phase 2 — Project Structure

```
wav\                            ← working directory (existing)
├── wav_to_mp3.py               ← main script
├── yang42.properties           ← example input file (config + tracklist in one)
├── chen18.properties           ← another input file for a different run
├── requirements.txt
├── README.md
└── plan.md                     ← this file
```

> WAV source files live in the directory specified by `input_dir` inside each `.properties` file.  
> The output MP3 is written to `output_dir` with the same stem as the `.properties` file.

---

## Phase 3 — Input File Format (`yang42.properties`)

A single plain Java-style `.properties` file — `key=value` lines, no section headers, `#` for comments. It contains **both** the runtime configuration and the track timeline.

### Parsing Rule
- **Config keys** are matched by name from a fixed set: `input_dir`, `output_dir`, `bitrate`
- Double quotes around values are stripped (e.g. `"G:\My Drive\..."` → `G:\My Drive\...`)
- **Every other key** whose stripped value parses as a float is treated as a track entry: `filename = start_sec`
- Non-float, non-config values cause a parse error
- The output MP3 name is derived from the file stem: `yang42.properties` → `yang42.mp3`

### Example (actual `yang42.properties`)

```properties
input_dir="G:\My Drive\Peter\Taichi\Confucius4"
output_dir="G:\My Drive\Peter\Taichi\Confucius4"
bitrate=192k
# Tracklist
42_00.wav=5.0
42_01.wav=10.0
42_02.wav=15.0
42_03.wav=20.0
```

### Config Keys

| Key | Type | Description |
|---|---|---|
| `input_dir` | path | Directory containing the source WAV files |
| `output_dir` | path | Directory where the output MP3 is written |
| `bitrate` | str | MP3 encoding bitrate (`128k`, `192k`, `320k`) |

### Track Entries

| Element | Description |
|---|---|
| Key | WAV filename (basename only, no path) |
| Value | Start time in seconds as a float (position in the final MP3) |

### Rules
- Values **must be unique** (two tracks cannot share the same start time)
- The first track (lowest start time) **may start at any value ≥ 0** — leading silence is prepended automatically
- Track entries are **sorted by value (start time)** after parsing — insertion order in the file does not matter
- Each track's `start_sec` must be ≥ `start_sec[n-1] + duration[n-1]` after sorting (no overlap); this check runs after conversion when exact durations are known
- File-existence checks and basic validation (`start_sec ≥ 0`, uniqueness, config completeness) happen after parsing, before any conversion begins

> The output filename is always `<stem>.mp3` — e.g. `yang42.properties` → `yang42.mp3`.  
> Intermediate per-file MP3s are always deleted after export.

---

## Phase 4 — Script Design (`wav_to_mp3.py`)

### 4.1 CLI Interface

```
python wav_to_mp3.py yang42.properties
python wav_to_mp3.py chen18.properties
```

Single positional argument only. No flags. Usage error if argument is missing or file not found.  
The output MP3 name is derived from the stem of the argument: `yang42.properties` → `yang42.mp3`.

### 4.2 Silence Calculation Algorithm

For each track `n` (0-indexed), silence inserted **before** the clip:

$$\text{silence\_before}[n] = \begin{cases} \text{start\_sec}[0] & n = 0 \text{ (leading silence, may be 0)} \\ \text{start\_sec}[n] - \left(\text{start\_sec}[n-1] + \text{duration}[n-1]\right) & n > 0 \end{cases}$$

- If `silence_before[n] < 0` → **abort**: tracks overlap, cannot build timeline
- If `silence_before[n] = 0` → no silence inserted (back-to-back or first track at 0)
- If `silence_before[n] > 0` → insert `pydub.AudioSegment.silent(duration=silence_before[n] * 1000)` ms

### 4.3 Core Functions

```python
CONFIG_KEYS = {'input_dir', 'output_dir', 'bitrate'}

def parse_properties(properties_path: Path) -> tuple[dict, list[Track]]:
    """
    Parse <name>.properties line by line.
    - Ignore blank lines and #-comments.
    - Strip surrounding double quotes from values (e.g. "path with spaces").
    - Keys in CONFIG_KEYS → config dict (as strings).
    - Other keys whose stripped value parses as float → Track(name, start_sec).
    - Non-float, non-config keys → ValueError with line info.
    - Tracks are sorted by start_sec ascending.
    - Injects 'output_name' = stem + '.mp3' into config.
    Returns (config, tracks).
    """

def validate_ffmpeg() -> None:
    """Check ffmpeg.exe and ffprobe.exe are on PATH; abort with install hint if not."""

def validate_tracks(tracks: list[Track], input_dir: Path) -> None:
    """
    For each track:
      - Assert the WAV file exists in input_dir
      - Assert start_sec >= 0.0
      - Assert no overlap: start_sec[n] >= start_sec[n-1] + duration[n-1]
        (Overlap check happens after conversion, when durations are known.)
    Raise ValueError with a descriptive message on first failure.
    """

def convert_wav_to_mp3(wav_path: Path, temp_dir: Path, bitrate: str) -> Path:
    """
    Convert a single WAV to MP3 using pydub.
    Writes to temp_dir/<stem>.mp3; returns the MP3 path.
    """

def build_timeline(
    tracks: list[Track],
    temp_dir: Path,
) -> AudioSegment:
    """
    Build the final AudioSegment by:
      1. Loading each MP3 from temp_dir in sorted track order
      2. Calculating silence_before for each track
      3. Appending silence + clip in order
    Return the complete assembled AudioSegment.
    """

def export_final(audio: AudioSegment, output_path: Path, bitrate: str) -> None:
    """Export the assembled AudioSegment to MP3 at output_path."""

def cleanup_temp_dir(temp_dir: Path) -> None:
    """Delete the entire temp directory and all intermediate MP3s."""

def main() -> None:
    """
    Orchestration:
      1. Parse sys.argv[1] as <name>.properties path
      2. parse_properties → config dict + sorted list of Track
         (output_name = stem + '.mp3' derived automatically)
      3. validate_ffmpeg → validate_tracks (file existence only)
      4. Create temp/ directory in output_dir
      5. Convert each WAV → MP3 in temp/ (with tqdm progress bar)
      6. Full overlap validation (durations now known)
      7. build_timeline → export_final to output_dir/<output_name>
      8. cleanup_temp_dir (always)
      9. Print summary: track list, silence gaps, total duration
    """
```

> **Intermediate MP3s** are written to `<output_dir>/temp/`. This directory is created at startup and deleted entirely after the final MP3 is exported, regardless of success or failure.

### 4.4 Console Summary Output (on success)

```
Timeline assembled:
  [  5.000s]  42_00.wav          (duration: 4.2s,  silence before:  5.0s)
  [ 10.000s]  42_01.wav          (duration: 3.8s,  silence before:  0.8s)
  [ 15.000s]  42_02.wav          (duration: 4.5s,  silence before:  1.2s)
  [ 20.000s]  42_03.wav          (duration: 5.1s,  silence before:  0.5s)

Total duration: 25.1s
Output: G:\My Drive\Peter\Taichi\Confucius4\yang42.mp3
```

---

## Phase 5 — Error Handling

| Scenario | Handling |
|---|---|
| Missing CLI argument | Print usage hint and exit with code 1 |
| `.properties` file not found | Clear message with the attempted path; exit 1 |
| `.properties` file has a non-float, non-config key | Report the offending line; exit 1 |
| `input_dir` or `output_dir` key missing | Report the missing key; exit 1 |
| Duplicate start times | Report the conflicting filenames and shared start time; exit 1 |
| `ffmpeg.exe` / `ffprobe.exe` not in PATH | Print Windows install instructions; exit 1 |
| WAV file not found in `input_dir` | Abort before conversion starts; name the missing file |
| Tracks overlap (`silence_before < 0`) | Abort; report which two tracks conflict and the overlap amount |
| `start_sec` of any track is negative | Abort; report the offending filename and value |
| Corrupted WAV file | Catch `pydub` exception; log and abort |
| Output directory doesn't exist | Auto-create with `Path.mkdir(parents=True, exist_ok=True)` |
| Disk space exhaustion | Catch `OSError`; log and abort with cleanup attempt |

---

## Phase 6 — Testing Approach

1. **`test_properties_parsing.py`**
   - Write a temp `.properties` file with config keys + track entries; assert both are parsed correctly
   - Assert track entries are sorted by start_sec regardless of file order
   - Assert first track may have start_sec > 0 (leading silence scenario)
   - Test duplicate start times raise `ValueError`
   - Test a non-float non-config key raises `ValueError`
   - Test missing `input_dir` / `output_dir` raises appropriate error
   - Test missing file raises `FileNotFoundError`

2. **`test_silence_calculation.py`**
   - Given a parsed track list and known MP3 durations, assert silence values are correct
   - Assert leading silence is correctly calculated when first `start_sec > 0`
   - Test overlap detection raises `ValueError`

3. **`test_conversion.py`**
   - Generate a synthetic 1-second WAV via `pydub`; convert; assert valid MP3 output

4. **`test_timeline_build.py`**
   - Build a 3-track timeline with known start times; assert final duration matches expected

5. **Integration test**
   - Place real WAV files and a `yang42.properties` in `tests\fixtures\`
   - Run `main()` end-to-end; assert `yang42.mp3` exists, duration matches expected, and intermediate MP3s are deleted

---

## Phase 7 — README

Content:
- Prerequisites: Python 3.10+, FFmpeg on Windows PATH
- Installation (`pip install -r requirements.txt`)
- `.properties` file format: config keys + track entries in one file
- Example `yang42.properties`
- Running: `python wav_to_mp3.py yang42.properties`
- Troubleshooting: FFmpeg PATH, overlap errors, bitrate options

---

## Task Dependency Graph

```
Phase 1 (Setup)
    └─→ Phase 2 (Structure)
            └─→ Phase 3 (unified .properties file format)
                    └─→ Phase 4 (Script implementation)
                            ├─→ Phase 5 (Error handling — built into Phase 4)
                            └─→ Phase 6 (Tests)
                                    └─→ Phase 7 (README)
```

---

## Risks

- **FFmpeg PATH on Windows:** `pydub` silently falls back to a broken state if `ffprobe` is missing even when `ffmpeg` is present — validate both explicitly at startup.
- **MP3 frame boundary timing:** MP3 encoding introduces small frame-level timing drift (~26ms per frame); for precise start times, verify silence padding accounts for this or use lossless intermediate (keep WAV, only encode at the final export step).
- **Large files in RAM:** `pydub` holds the entire assembled `AudioSegment` in memory before export; for very long timelines (>30 min), memory usage may be significant on Windows.

---

## Estimated Effort

| Phase | Time |
|---|---|
| 1 — Setup | 0.5h |
| 2 — Structure | 0.25h |
| 3 — Unified .properties format | 0.25h |
| 4 — Script implementation | 3–4h |
| 5 — Error handling | 0.5h |
| 6 — Tests | 2h |
| 7 — README | 0.5h |
| **Total** | **~7–8h** |
