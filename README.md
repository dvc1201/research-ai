# research-ai

Research on AI topics — currently focused on **WAV → MP3 timeline assembly** for martial arts audio companions.

---

## `wav/` — Audio Timeline Merger

A Python toolbox for converting WAV posture-name clips into a single timed MP3, designed for taiji practice audio guides (Yang-style 85 form).

### Pipeline

Two scripts, three hand-authored input files:

| Stage | Tool | Input (manual) | Output |
|---|---|---|---|
| 1. Synthesis | `gen_audio.py` | `*_mapping.properties` (filename=spoken text) | WAV files (`edgetts/`) |
| 2. Assembly | `wav_to_mp3.py` | control `*.properties` + form `*form*.properties` | final MP3 + timeline `.txt` |

- `*_mapping.properties` — `wav_filename=spoken Chinese text`, hand-edited before synthesis
- `*form*.properties` — `wav_filename=weight` (form definition)
- control `*.properties` — paths, `form=`, `intro=`, `formlength=`, `output_filename=`

### Quickstart

```powershell
# Prerequisites (one-time)
winget install Python.Python.3.12
winget install Gyan.FFmpeg
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Build an MP3 (full form, pigua speed, with intro)
.\.venv\Scripts\python.exe wav_to_mp3.py yang85pigua.properties
```

### Scripts

| Script | Purpose |
|---|---|
| `gen_audio.py` | Reads `*_mapping.properties`, calls Edge-TTS to synthesize clean Mandarin WAV files |
| `wav_to_mp3.py` | Reads a control `.properties` (config + `form=`/`intro=`), converts WAV → MP3 (cached), assembles with silence gaps, exports MP3 + timeline `.txt` |

### `.properties` file format

**Unified format** (all-in-one, for simple use cases):
```properties
input_dir=G:\path\to\wav\files
output_dir=G:\path\to\output
output_filename=yang85_25min.mp3    # optional; defaults to <stem>.mp3
bitrate=192k
formlength=1500                      # total form seconds
# Tracklist: weighted posture entries
85_01.wav=10                         # weight 10  (e.g. 无极势)
85_02.wav=5                          # weight 5   (太极起势)
85_03_lrtail.wav=20                  # weight 20  (揽雀尾)
```

**Modular format** (control file + separate form definition):
```properties
# Control file: yang85pigua.properties
input_dir=G:\path\to\wav\files
output_dir=G:\path\to\output
bitrate=192k
form=yang85form.properties           # points to form definition file
intro=pigua.mp3                      # optional intro MP3 (prepended)
output_filename=yang85_pigua.mp3
formlength=480                       # form duration (excludes intro)
```

```properties
# Form definition file: yang85form.properties
# Section 1
85_01.wav=10
85_02.wav=5
85_03_lrtail.wav=20
# ... more tracks
```

- **Config keys:** `input_dir`, `output_dir`, `output_filename` (opt), `bitrate`, `formlength`, `form` (opt), `intro` (opt), `cache_dir` (opt)
- **Track entries:** `<filename>.wav = <weight>` — relative timing unit
- **`form=`** — path to separate form definition file (relative to control file)
- **`intro=`** — path to intro MP3 file (prepended before form; not counted in formlength)
- Start times are computed at runtime: each track's start = sum of preceding weights × formlength ÷ total_weight
- Edge-TTS audio pipeline: hand-edit `*_mapping.properties` → `gen_audio.py` (WAVs) → hand-edit control + form files → `wav_to_mp3.py` (MP3)

### MP3 conversion cache

WAV → MP3 conversion is a **one-time** action. Converted MP3s are cached in
`<input_dir>/mp3cache/` and reused by every subsequent merge, so building
multiple practice parts costs almost nothing after the first run.

```powershell
.\.venv\Scripts\python.exe wav_to_mp3.py yang85pigua.properties           # cold: converts all
.\.venv\Scripts\python.exe wav_to_mp3.py yang85pigua1.properties          # warm: 0 converted
.\.venv\Scripts\python.exe wav_to_mp3.py yang85pigua.properties --force   # ignore cache
```

### Yang 85-form files

| File | Description |
|---|---|
| `yang85_mapping.properties` | 105 filename → spoken Chinese text pairs (manual, stage 1 input) |
| `yang85form.properties` | Full form definition — 105 `filename=weight` entries |
| `yang85form1.properties` | Form subset — postures 1–30 |
| `yang85form2.properties` | Form subset — postures 29–56 |
| `yang85form3.properties` | Form subset — postures 56–85 |
| `yang85pigua.properties` | Control — full form, pigua speed (480s) |
| `yang85pigua1.properties` | Control — part 1, pigua speed (180s) |
| `yang85pigua2.properties` | Control — part 2, pigua speed (180s) |
| `yang85pigua3.properties` | Control — part 3, pigua speed (180s) |
| `pigua.mp3` | Intro audio (prepended via `intro=`) |
| `yang85.properties` | Legacy unified config (all-in-one) |
| `yang42.properties` | Older test/demo config (not valid input for current script) |

### Practice parts (`docs/`)

Generated practice MP3s (full form + parts at pigua speed) and their timeline
indexes live in `docs/mp3/`. See `docs/README.md` for the overview table.

### Environment

- **Python:** 3.12 — Python 3.13 removed the `audioop` module that `pydub`
  depends on; a fix is in progress ([jiaaro/pydub#881](https://github.com/jiaaro/pydub/pull/881)),
  so stay on 3.12 until a new `pydub` release lands.
- **FFmpeg:** Gyan build 8.1.2
- **Edge-TTS** voice: `zh-CN-YunxiNeural` (male, calm, instructional tone)
- **`requirements.txt`:** `pydub`, `tqdm`, `edge-tts`, `aiohttp` (and transitive deps)
