import re
import math
import random
from pathlib import Path
from collections import Counter
import numpy as np

def find_data_file(candidates):
    root = Path.cwd()
    if root.name == "src":
        root = root.parent
    for name in candidates:
        for folder in [root / "data", root]:
            target = folder / name
            if target.exists():
                return target
    raise FileNotFoundError(f"Missing required file: {candidates}")

voynich_path = find_data_file(["ZL3b-n.txt"])
latin_path = find_data_file(["medieval_corpus.txt", "mevieval_corpus.txt"])

def compute_entropies(words):
    text = " ".join(words)
    n = len(text)
    h0 = math.log2(len(set(text)))
    c1 = Counter(text)
    h1 = -sum((cnt / n) * math.log2(cnt / n) for cnt in c1.values())
    bigrams = Counter(text[i:i + 2] for i in range(n - 1))
    unigrams_prefix = Counter(text[:-1])
    h2 = 0.0
    for bg, bg_cnt in bigrams.items():
        p_xy = bg_cnt / (n - 1)
        p_y_given_x = bg_cnt / unigrams_prefix[bg]
        h2 -= p_xy * math.log2(p_y_given_x)
    lengths = [len(w) for w in words]
    return h0, h1, h2, np.mean(lengths), np.std(lengths), len(set(words))

voynich_words = []
with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            voynich_words.extend([w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()])

with open(latin_path, "r", encoding="utf-8", errors="ignore") as f:
    raw_latin = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", f.read().lower())).strip()

latin_words = raw_latin.split()[:len(voynich_words)]

STATE_PREFIXES = {
    "a": ["da", "sa", "cha", "sha", "a"],
    "e": ["qoke", "che", "she", "oke", "ote"],
    "i": ["dai", "sai", "qoki", "chi", "i"],
    "o": ["qoko", "cho", "sho", "oko", "oto"],
    "u": ["qoku", "chu", "shu", "oku", "o"],
    "BOS": ["y", "o", "d", "s", "k"]
}

STATE_SUFFIXES = {
    "a": ["ar", "al", "am", "an", "a"],
    "e": ["edy", "eedy", "ey", "er", "e"],
    "i": ["aiin", "iin", "in", "ir", "i"],
    "o": ["ol", "or", "om", "on", "o"],
    "u": ["y", "dy", "hy", "ky", "ry"],
    "BOS": ["y", "am", "ol", "aiin", "dy"]
}

CORE_GLYPHS = ["k", "t", "p", "f", "ch", "sh", "l", "r", "c", "o", "e", "ee", "ii", "d", "s"]

def forward_encrypt_latin(latin_text, target_token_count, seed=42):
    rng = random.Random(seed)
    merged = latin_text.replace(" ", "")
    blocks = re.findall(r"[aeiou]+|[^aeiou]+", merged)
    cipher_book = {}
    encrypted_tokens = []
    for i, block in enumerate(blocks):
        if not set(block).issubset(set("aeiou")):
            left_v = blocks[i - 1][-1] if (i - 1 >= 0 and set(blocks[i - 1]).issubset(set("aeiou"))) else "BOS"
            right_v = blocks[i + 1] if (i + 1 < len(blocks) and set(blocks[i + 1]).issubset(set("aeiou"))) else "BOS"
            triple = (left_v, block, right_v)
            if triple not in cipher_book:
                pre = rng.choice(STATE_PREFIXES.get(left_v, STATE_PREFIXES["BOS"]))
                suf = rng.choice(STATE_SUFFIXES.get(right_v, STATE_SUFFIXES["BOS"]))
                n_cores = min(2, max(0, len(block) - 1))
                core = "".join(rng.choice(CORE_GLYPHS) for _ in range(n_cores))
                cipher_book[triple] = f"{pre}{core}{suf}"
            encrypted_tokens.append(cipher_book[triple])
            if len(encrypted_tokens) >= target_token_count:
                break
    return encrypted_tokens

synthetic_voynich_words = forward_encrypt_latin(raw_latin[:350000], len(voynich_words))

results = [
    ("Plain Medieval Latin (Input)", compute_entropies(latin_words)),
    ("Actual Voynich (ZL3b-n Target)", compute_entropies(voynich_words)),
    ("Vowel-Boundary Cipher (Output)", compute_entropies(synthetic_voynich_words))
]

for name, (h0, h1, h2, m_len, s_len, uniq) in results:
    print(f"{name:<32} | H0: {h0:5.2f} | H1: {h1:5.2f} | H2: {h2:6.3f} | Mean Len: {m_len:5.2f} (±{s_len:4.2f}) | Unique: {uniq:6,}")
