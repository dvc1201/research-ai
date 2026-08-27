# Forms

Hand-authored form definitions and assembly/control files for the audio
timeline pipeline. Each subdirectory holds the files for one taiji form.

## Directory layout

```
forms/
├── yang85/          # Yang-style 85 form (active)
│   ├── yang85_edge.tts              # Generation control — Edge-TTS, yunxi voice, -10% rate
│   ├── yang85_mapping.properties     # 105 mp3_filename=spoken Chinese text pairs
│   ├── yang85form.properties         # Full form definition — 105 mp3_filename=weight entries
│   ├── yang85form1.properties        # Form subset — postures 1–30
│   ├── yang85form2.properties        # Form subset — postures 29–56
│   ├── yang85form3.properties        # Form subset — postures 56–85
│   ├── yang85pigua.properties        # Assembly control — full form, pigua speed (480 s)
│   ├── yang85pigua1.properties       # Assembly control — part 1, pigua speed (180 s)
│   ├── yang85pigua2.properties       # Assembly control — part 2, pigua speed (180 s)
│   ├── yang85pigua3.properties       # Assembly control — part 3, pigua speed (180 s)
│   └── yang85_22min.properties       # Assembly control — full form, normal speed (1320 s)
└── yang42/          # Yang-style 42 form (legacy, unified format)
    └── yang42.properties             # Legacy unified config + absolute-start-time tracks
```

## Yang 85 form

The primary form used by the pipeline. Synthesis is performed via
`gen_audio.py yang85_edge.tts`, assembly via `gen_form.py yang85pigua.properties` (or
one of the part/speed variants).

| File | Type | Description |
|---|---|---|
| `yang85_edge.tts` | `.tts` control | Edge-TTS generator, yunxi voice, -10% rate |
| `yang85_mapping.properties` | mapping | 105 `mp3_filename=spoken Chinese text` pairs |
| `yang85form.properties` | form definition | Full form — 105 `mp3_filename=weight` entries |
| `yang85form1.properties` | form definition | Subset — postures 1–30 |
| `yang85form2.properties` | form definition | Subset — postures 29–56 |
| `yang85form3.properties` | form definition | Subset — postures 56–85 |
| `yang85pigua.properties` | assembly control | Full form, pigua speed (480 s) |
| `yang85pigua1.properties` | assembly control | Part 1, pigua speed (180 s) |
| `yang85pigua2.properties` | assembly control | Part 2, pigua speed (180 s) |
| `yang85pigua3.properties` | assembly control | Part 3, pigua speed (180 s) |
| `yang85_22min.properties` | assembly control | Full form, normal speed (1320 s) |

The intro MP3s (`pigua.mp3`, `normal.mp3`) live in `wav/`.

## Yang 42 form (legacy)

A legacy single-file format where config keys and absolute-start-time tracks
coexist in one `.properties` file. This format is not used by the current
`gen_form.py` pipeline. It remains for reference only.

| File | Type | Description |
|---|---|---|
| `yang42.properties` | legacy unified | Config + `filename=start_sec` tracks in one file |

## Form definition format

```properties
# Section 1
85_01.mp3=10
85_02.mp3=5
85_03_lrtail.mp3=18
```

- `filename=weight` pairs; weight is a relative timing unit.
- Blank lines and `#` comments are ignored.
- Files are processed in declaration order.

## Assembly control format

```properties
input_dir=G:\path\to\edgetts
output_dir=G:\path\to\mp3
form=yang85form.properties
intro=pigua.mp3
output_filename=yang85_pigua.mp3
formlength=480
```

See the root `README.md` for a full description of each key.

## Generation control format (`.tts`)

```properties
tts_class=EdgeTTS
mapping_file=yang85_mapping.properties
output_dir=G:\path\to\edgetts
tts.voice=zh-CN-YunxiNeural
tts.rate=-10%
```

Paths are resolved relative to the current working directory (typically
`wav/`).