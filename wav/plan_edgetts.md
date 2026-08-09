# Plan: Regenerate Yang 85 Audio with Edge-TTS

**Date:** 2026-08-09  
**Status:** Implemented  
**Platform:** Windows only  
**Working directory:** `c:\work\github\research-ai\wav\`

---

## Overview

Two-step pipeline:
1. **`gen_mapping.py`** — reads `<form>.properties`, derives spoken Chinese text for each filename, writes `<form>_mapping.properties`
2. **`gen_audio.py`** — reads `*_mapping.properties` (filename=spoken text pairs), calls Edge-TTS, writes real WAV files

This split lets you edit/verify the mapping by hand before burning API calls. The original single-script `gen_edgetts.py` is superseded.

---

## Phase 1 — Install edge-tts

```powershell
.\.venv\Scripts\python.exe -m pip install edge-tts
```

Library: [edge-tts](https://github.com/rany2/edge-tts) — uses Microsoft's free TTS endpoint. `pip freeze > requirements.txt` afterwards.

---

## Phase 2 — Mapping: filename → spoken text

The script reads track entries from `yang85.properties`. For each `filename.wav`, it derives the spoken Chinese text:

| Filename | Spoken text | |
|---|---|---|
| `85_01.wav` | `无极势` | |
| `85_02.wav` | `太极起势` | |
| `85_03_lrtail.wav` | `揽雀尾` | |
| `85_09_knee1.wav` | `搂膝拗步 一` | |
| `85_09_knee2.wav` | `搂膝拗步 二` | |
| `85_09_knee3.wav` | `搂膝拗步 三` | |
| `85_17_monkey3.wav` | `倒撵猴 三` | |
| `85_52_jadelady4.wav` | `玉女穿梭 四` | |
| `...` | `...` | |
| `85_85_close.wav` | `收势` | |

**Derivation rules:**
1. Parse the filename: `85_XX[_suffix].wav`
2. Look up the Chinese posture name from `XX` (no `第N式` prefix — the sequence order is already known)
3. **If any digit exists after character 5** (i.e. in the suffix after `85_XX`) → pronounce that digit as Chinese number. Otherwise no sub-part suffix. E.g. `85_09_knee2` has `2` after char 5 → `二`; `85_01` has nothing after char 5 → no suffix.
4. Final spoken text: `<name>[ 数字]`

A hardcoded dictionary maps 85 posture numbers to their traditional Chinese names. Multi-part postures (knee1/2/3, monkey1/2/3, wave1/2/3, etc.) share the same `XX` key — the sub-part digit comes from the filename suffix, not the map. The full list produces **105 WAV files** (85 postures, 20 of which are multi-part).

---

## Phase 3 — Script: `gen_edgetts.py`

```python
import asyncio
import edge_tts
import re
from pathlib import Path

VOICE = "zh-CN-YunxiNeural"          # male Mandarin, natural cadence
# VOICE = "zh-CN-XiaoxiaoNeural"     # alternative: female
RATE = "-10%"                         # slightly slower for clarity
OUTPUT_DIR = Path(r"G:\My Drive\Peter\Taichi\Confucius4\yang85\edgetts")

NAME_MAP = {
    "01": "无极势",
    "02": "太极起势",
    "03": "揽雀尾",
    "04": "单鞭",
    # ... all 85 entries
    "85": "收势",
}

async def generate(text: str, out_path: Path):
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(out_path))

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # read yang85.properties, extract track filenames
    # for each: derive spoken text, call generate()
```

---

## Phase 4 — Speech text derivation logic

**Rule:** Look at the filename stem after the 5th character (i.e. after `85_XX`). If any digit exists in that suffix, it's the sub-part number.

| Filename | Stem | Suffix (after `85_XX`) | Contains digit? | Spoken text |
|---|---|---|---|---|
| `85_01.wav` | `85_01` | _(empty)_ | No | `无极势` |
| `85_02.wav` | `85_02` | _(empty)_ | No | `太极起势` |
| `85_09_knee1.wav` | `85_09_knee1` | `_knee1` | Yes → `1` | `搂膝拗步 一` |
| `85_09_knee2.wav` | `85_09_knee2` | `_knee2` | Yes → `2` | `搂膝拗步 二` |
| `85_17_monkey3.wav` | `85_17_monkey3` | `_monkey3` | Yes → `3` | `倒撵猴 三` |
| `85_52_jadelady4.wav` | `85_52_jadelady4` | `_jadelady4` | Yes → `4` | `玉女穿梭 四` |

**Algorithm:**
```python
NUM_MAP = {"1": "一", "2": "二", "3": "三", "4": "四"}

def derive_text(filename: str) -> str:
    stem = Path(filename).stem                    # e.g. "85_09_knee2"
    parts = stem.split("_")
    posture_num = parts[1]                        # e.g. "09"
    text = NAME_MAP[posture_num]
    # check for any digit after the 5th character (after "85_XX")
    suffix = stem[5:]                             # e.g. "_knee2" or "" for "85_01"
    for ch in suffix:
        if ch.isdigit():
            text += f" {NUM_MAP[ch]}"
            break
    return text
```

---

## Phase 5 — Voice selection

| Voice | Gender | Character |
|---|---|---|
| `zh-CN-YunxiNeural` | Male | Warm, natural, good for instruction |
| `zh-CN-YunjianNeural` | Male | Sport/narration style |
| `zh-CN-XiaoxiaoNeural` | Female | Clear, bright |
| `zh-CN-XiaoyiNeural` | Female | Softer, conversational |

Recommendation: **Yunxi** for taiji instruction (calm, deliberate pacing).

Rate `-10%` gives slightly slower delivery appropriate for practice.

---

## Phase 6 — Integration

After generation, update `yang85.properties`:

```properties
input_dir=G:\My Drive\Peter\Taichi\Confucius4\yang85\edgetts
```

Then re-run `wav_to_mp3.py` — it picks up the new files with identical filenames. No other changes needed.

---

## Phase 7 — Validation

1. Listen to 3–5 samples (especially multi-part ones)
2. Adjust `RATE` if too fast/slow
3. Check all 105 files exist in `edgetts\`
4. Run `wav_to_mp3.py` with new `input_dir` — verify the full timeline still assembles

---

## Estimated Effort

| Phase | Time |
|---|---|
| 1 — Install edge-tts | 5 min |
| 2–3 — Build name map + script | 30 min |
| 4–5 — Multi-part logic + voice tuning | 15 min |
| 6 — Integration test | 10 min |
| **Total** | **~1 hour** |