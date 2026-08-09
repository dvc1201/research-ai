# gen_mapping.py — Extract filenames and derive spoken text from a form .properties file
#
# Reads <form>.properties (e.g. yang85.properties) and writes a companion
# <form>_mapping.properties where each line is:
#   <wav_filename>=<spoken Chinese text>
#
# You can manually review/edit the mapping file before passing it to gen_audio.py.
#
# Usage: python gen_mapping.py yang85.properties
# Output: yang85_mapping.properties


import sys
from collections import OrderedDict
from pathlib import Path

# ---------------------------------------------------------------------------
# posture name map — 85 keys (YY = posture number, zero-padded)
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
# Configuration keys (lines to skip when extracting track filenames)
# ---------------------------------------------------------------------------

CONFIG_KEYS = {"input_dir", "output_dir", "output_filename", "bitrate", "formlength"}

# Chinese digits for sub-part suffixes
NUM_MAP = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_track_filenames(properties_path: Path) -> list[str]:
    """Return ordered list of WAV filenames from a form .properties file."""
    filenames: list[str] = []
    with open(properties_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.partition("=")[0].strip()
            if key in CONFIG_KEYS:
                continue
            filenames.append(key)
    return filenames


def derive_text(filename: str) -> str:
    """Derive the spoken Chinese text for a given WAV filename."""
    stem = Path(filename).stem
    parts = stem.split("_")
    posture_num = parts[1]

    text = NAME_MAP[posture_num]

    # trailing digit preceded by a letter → sub-part suffix
    if len(stem) >= 2 and stem[-1].isdigit() and stem[-2].isalpha():
        text += f" {NUM_MAP[stem[-1]]}"

    return text


def write_mapping(
    mapping: "OrderedDict[str, str]",
    output_path: Path,
    source_file: str,
) -> None:
    """Persist the filename→spoken_text mapping as a .properties file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            f"# Audio mapping — generated from {source_file}\n"
            f"# Format: <wav_filename>=<spoken text>\n"
            f"# Edit the right-hand side to adjust pronunciation.\n\n"
        )
        for filename, text in mapping.items():
            f.write(f"{filename}={text}\n")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage:   python gen_mapping.py <form>.properties")
        print("Example: python gen_mapping.py yang85.properties")
        sys.exit(1)

    source_path = Path(sys.argv[1])
    if not source_path.is_file():
        print(f"Error: {source_path} not found")
        sys.exit(1)

    filenames = extract_track_filenames(source_path)
    print(f"Found {len(filenames)} track entries in {source_path.name}")

    mapping: "OrderedDict[str, str]" = OrderedDict()
    for fn in filenames:
        mapping[fn] = derive_text(fn)

    # output name:  yang85.properties  →  yang85_mapping.properties
    out_name = source_path.stem + "_mapping.properties"
    out_path = source_path.parent / out_name

    write_mapping(mapping, out_path, source_path.name)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()