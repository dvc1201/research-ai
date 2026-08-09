# gen_edgetts.py — Regenerate Yang 85 posture audio using Microsoft Edge-TTS
#
# Reads yang85.properties, extracts all track filenames, synthesizes clean
# Mandarin speech for each posture name, writes WAV files to edgetts/.
# Usage: python gen_edgetts.py

import asyncio
import os
import sys
from pathlib import Path

# -- ensure ffmpeg is on PATH (for pydub conversion) --
_FFMPEG_BIN = (
    Path(os.environ["LOCALAPPDATA"])
    / "Microsoft" / "WinGet" / "Packages"
    / "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    / "ffmpeg-8.1.2-full_build" / "bin"
)
os.environ["PATH"] = str(_FFMPEG_BIN) + os.pathsep + os.environ["PATH"]

import edge_tts
from pydub import AudioSegment

# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------

VOICE = "zh-CN-YunxiNeural"
RATE = "-10%"                           # slightly slower for clarity
PROPERTIES_PATH = Path(__file__).parent / "yang85.properties"
OUTPUT_DIR = Path(r"G:\My Drive\Peter\Taichi\Confucius4\yang85\edgetts")

# Chinese number mapping for sub-part digits
NUM_MAP = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "7": "七"}

# ---------------------------------------------------------------------------
# posture name map — 85 keys, traditional Yang-style names
# ---------------------------------------------------------------------------

NAME_MAP: dict[str, str] = {
    "01": "无极势",
    "02": "太极起势",
    "03": "揽雀尾",
    "04": "单鞭",
    "05": "提手上势",
    "06": "白鹤亮翅",
    "07": "搂膝拗步",
    "08": "手挥琵琶",
    "09": "搂膝拗步",
    "10": "手挥琵琶",
    "11": "搂膝拗步",
    "12": "搬拦捶",
    "13": "如封似闭",
    "14": "十字手",
    "15": "抱虎归山",
    "16": "肘底看捶",
    "17": "倒撵猴",
    "18": "斜飞式",
    "19": "提手上势",
    "20": "白鹤亮翅",
    "21": "搂膝拗步",
    "22": "海底针",
    "23": "扇通背",
    "24": "撇身捶",
    "25": "搬拦捶",
    "26": "揽雀尾",
    "27": "单鞭",
    "28": "云手",
    "29": "单鞭",
    "30": "高探马",
    "31": "左右分脚",
    "32": "转身左蹬脚",
    "33": "搂膝拗步",
    "34": "进步栽捶",
    "35": "翻身撇身捶",
    "36": "搬拦捶",
    "37": "右蹬脚",
    "38": "左打虎",
    "39": "右打虎",
    "40": "右蹬脚",
    "41": "双峰贯耳",
    "42": "左蹬脚",
    "43": "转身右蹬脚",
    "44": "搬拦捶",
    "45": "如封似闭",
    "46": "十字手",
    "47": "抱虎归山",
    "48": "斜单鞭",
    "49": "野马分鬃",
    "50": "揽雀尾",
    "51": "单鞭",
    "52": "玉女穿梭",
    "53": "揽雀尾",
    "54": "单鞭",
    "55": "云手",
    "56": "单鞭",
    "57": "下势",
    "58": "金鸡独立",
    "59": "倒撵猴",
    "60": "斜飞式",
    "61": "提手上势",
    "62": "白鹤亮翅",
    "63": "搂膝拗步",
    "64": "海底针",
    "65": "扇通背",
    "66": "转身白蛇吐信",
    "67": "搬拦捶",
    "68": "揽雀尾",
    "69": "单鞭",
    "70": "云手",
    "71": "单鞭",
    "72": "高探马穿掌",
    "73": "十字腿",
    "74": "指裆捶",
    "75": "揽雀尾",
    "76": "单鞭",
    "77": "下势",
    "78": "上步七星",
    "79": "退步跨虎",
    "80": "转身摆莲",
    "81": "弯弓射虎",
    "82": "搬拦捶",
    "83": "如封似闭",
    "84": "十字手",
    "85": "合太极",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def extract_track_filenames(properties_path: Path) -> list[str]:
    """Parse yang85.properties and return the ordered list of WAV filenames."""
    filenames: list[str] = []
    with open(properties_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.partition("=")[0].strip()
            if key in {"input_dir", "output_dir", "output_filename", "bitrate", "formlength"}:
                continue
            filenames.append(key)
    return filenames


def derive_text(filename: str) -> str:
    """Derive the spoken Chinese text from a filename like '85_09_knee2.wav'."""
    stem = Path(filename).stem                      # e.g. "85_09_knee2"
    parts = stem.split("_")
    posture_num = parts[1]                          # e.g. "09"
    text = NAME_MAP[posture_num]

    # trailing digit + preceding letter  →  sub-part number
    # "85_09_knee2" → yes (letter 'e' before '2')
    # "85_01"       → no  (digit '0' before '1')
    # "85_78_7star" → no  (letter 'r' before ending, no trailing digit)
    if len(stem) >= 2 and stem[-1].isdigit() and stem[-2].isalpha():
        text += f" {NUM_MAP[stem[-1]]}"
    return text


async def generate_one(text: str, out_path: Path) -> None:
    """Synthesise *text* into a WAV file at *out_path* using edge-tts."""
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    # edge-tts writes MP3 regardless of extension — convert to real WAV
    tmp = str(out_path) + ".tmp.mp3"
    await communicate.save(tmp)
    audio = AudioSegment.from_mp3(tmp)
    audio.export(out_path, format="wav")
    os.remove(tmp)


async def generate_all(filenames: list[str]) -> None:
    """Generate all 105 WAV files, max 5 in parallel."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sem = asyncio.Semaphore(5)                      # limit concurrency

    async def _worker(filename: str) -> None:
        async with sem:
            text = derive_text(filename)
            out_path = OUTPUT_DIR / filename
            print(f"  {filename:<28} → {text}")
            await generate_one(text, out_path)

    tasks = [_worker(fn) for fn in filenames]
    await asyncio.gather(*tasks)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

async def main() -> None:
    if not PROPERTIES_PATH.is_file():
        print(f"Error: {PROPERTIES_PATH} not found")
        return

    filenames = extract_track_filenames(PROPERTIES_PATH)
    print(f"Generating {len(filenames)} WAV files with"
          f" voice={VOICE} rate={RATE} …\n")

    await generate_all(filenames)

    print(f"\nDone.  Files written to {OUTPUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())