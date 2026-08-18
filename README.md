# research-ai

Research on AI topics — currently focused on **WAV → MP3 timeline assembly** for martial arts audio companions.

---

## `wav/` — Audio Timeline Merger

A Python toolbox for converting WAV posture-name clips into a single timed MP3, designed for taiji practice audio guides (Yang-style 85 form).

### Quickstart

```powershell
# Prerequisites (one-time)
winget install Python.Python.3.12
winget install Gyan.FFmpeg
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Build an MP3
.\.venv\Scripts\python.exe wav_to_mp3.py yang85edgetts.properties
```

### Scripts

| Script | Purpose |
|---|---|
| `wav_to_mp3.py` | Reads a `.properties` file (config + weighted tracklist), converts WAV → MP3, assembles with silence gaps, exports MP3 + timeline `.txt` |
| `gen_mapping.py` | Reads a form `.properties`, generates `_mapping.properties` (filename → spoken Chinese text) |
| `gen_audio.py` | Reads `_mapping.properties`, calls Edge-TTS to synthesize clean Mandarin WAV files |
| `gen_edgetts.py` | Legacy: original combined script (superseded by the two-step pipeline above) |

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

- **Config keys:** `input_dir`, `output_dir`, `output_filename` (opt), `bitrate`, `formlength`, `form` (opt), `intro` (opt)
- **Track entries:** `<filename>.wav = <weight>` — relative timing unit
- **`form=`** — path to separate form definition file (relative to control file)
- **`intro=`** — path to intro MP3 file (prepended before form; not counted in formlength)
- Start times are computed at runtime: each track's start = sum of preceding weights × formlength ÷ total_weight
- Edge-TTS audio pipeline: `gen_mapping.py` → (edit `_mapping.properties`) → `gen_audio.py` → update `input_dir` → `wav_to_mp3.py`

### Yang 85-form files

| File | Description |
|---|---|
| `yang85.properties` | Original unified config (Confucius4 TTS) — all-in-one |
| `yang85edgetts.properties` | Unified config pointing to Edge-TTS audio |
| `yang85form.properties` | **Form definition** — track weights only (modular) |
| `yang85pigua.properties` | **Control file** — uses `form=` + `intro=` (modular) |
| `yang85_mapping.properties` | 105 filename → spoken Chinese text pairs |
| `yang42.properties` | Older test/demo config |

### Environment

- **Python:** 3.12 (3.13 incompatible — `audioop` removed)
- **FFmpeg:** Gyan build 8.1.2
- **Edge-TTS** voice: `zh-CN-YunxiNeural` (male, calm, instructional tone)
- **`requirements.txt`:** `pydub`, `tqdm`, `edge-tts`, `aiohttp` (and transitive deps)
