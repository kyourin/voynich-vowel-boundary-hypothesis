import re
from pathlib import Path
from collections import Counter
import numpy as np

def find_voynich():
    root = Path.cwd()
    if root.name == "src":
        root = root.parent
    for folder in [root / "data", root]:
        target = folder / "ZL3b-n.txt"
        if target.exists():
            return target
    raise FileNotFoundError("Missing data/ZL3b-n.txt")

voynich_path = find_voynich()

SUFFIXES = sorted(["eedy", "aiin", "iin", "edy", "ody", "ey", "dy", "ol", "or", "ar", "al", "am", "om", "in", "y", "m", "n", "s", "r", "l"], key=len, reverse=True)

def get_suffix(word):
    for s in SUFFIXES:
        if word.endswith(s) and len(word) > len(s):
            return s
    return word[-1]

labels, mid_para, end_para, active_para = [], [], [], []

with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            tag = match.group(1)
            text = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            words = [w for w in re.split(r"[.,\s]+", text) if w and w.isalpha()]
            if not words:
                continue

            if "@L" in tag:
                labels.extend(words)
            elif "@P" in tag:
                if active_para:
                    end_para.append(active_para[-1])
                    mid_para.extend(active_para[:-1])
                active_para = list(words)
            elif "+P" in tag:
                active_para.extend(words)

if active_para:
    end_para.append(active_para[-1])
    mid_para.extend(active_para[:-1])

groups = [
    ("Standalone Labels (@L)", labels),
    ("Mid-Paragraph Tokens", mid_para),
    ("Paragraph-Final Tokens", end_para)
]

for name, items in groups:
    lengths = [len(w) for w in items]
    counts = Counter(get_suffix(w) for w in items)
    top5 = [(s, f"{cnt / len(items) * 100:.1f}%") for s, cnt in counts.most_common(5)]
    print(f"[{name}] Count: {len(items):,} | Mean Len: {np.mean(lengths):.2f} (±{np.std(lengths):.2f}) | Top 5: {top5}")
