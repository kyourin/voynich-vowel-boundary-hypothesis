# codes/forward_entropy_simulation.py
import re
import math
from collections import Counter

VOYNICH_PATH = r"ZL3b-n.txt"
PURE_LATIN_PATH = r"pure_latin_corpus.txt"

V_STATE_PREFIX = {
    "a": "da", "e": "che", "i": "yai", "o": "qok", "u": "sho",
    "ae": "chee", "oe": "chee", "au": "ota", "ia": "oka", "ie": "she",
    "io": "qot", "iu": "ytai", "ui": "okai", "ei": "tai", "": ""
}

C_BODY_15 = {
    "s": "y",   "t": "dy",  "r": "r",   "n": "n",   "m": "l",
    "c": "k",   "q": "ckh", "k": "ckh", "l": "ol",  "d": "d",
    "p": "p",   "b": "cph", "v": "f",   "g": "cth", "f": "cfh",
    "x": "cph", "h": "h",   "z": "s"
}

def load_voynich_words(path):
    words = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
            if match and not line.startswith("#"):
                tag = match.group(1)
                if "@P" in tag or "+P" in tag or "=P" in tag:
                    clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
                    ws = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]
                    words.extend(ws)
    return words

def calc_h2_entropy(word_list):
    stream = "_" + "_".join(word_list) + "_"
    unigrams = Counter(stream)
    bigrams = Counter(zip(stream[:-1], stream[1:]))
    tot_bi = sum(bigrams.values())
    return -sum((cnt / tot_bi) * math.log2(cnt / unigrams[c1]) for (c1, _), cnt in bigrams.items())

def analyze_corpus_metrics(word_list, sample_n=35000):
    ws = word_list[:sample_n]
    return (
        calc_h2_entropy(ws),
        sum(len(w) for w in ws) / len(ws),
        len(set(ws)),
        sum(1 for a, b in zip(ws[:-1], ws[1:]) if a == b),
        sum(1 for a, b, c in zip(ws[:-2], ws[1:-1], ws[2:]) if a == b == c)
    )

def simulate_unilateral_voynich(latin_words, char_limit=250000):
    cont_text = "".join(latin_words)[:char_limit]
    parts = re.findall(r"[aeiou]+|[^aeiou]+", cont_text)
    synth = []
    for idx, p in enumerate(parts):
        if not any(ch in "aeiou" for ch in p):
            v_raw = parts[idx - 1] if idx > 0 and any(ch in "aeiou" for ch in parts[idx - 1]) else ""
            v_pref = V_STATE_PREFIX.get(v_raw, V_STATE_PREFIX.get(v_raw[-1:] if v_raw else "", ""))
            c_body = "".join(C_BODY_15.get(ch, ch) for ch in p)
            synth.append(v_pref + c_body)
    return synth

if __name__ == "__main__":
    voy_words = load_voynich_words(VOYNICH_PATH)
    with open(PURE_LATIN_PATH, "r", encoding="utf-8", errors="ignore") as f:
        latin_words = re.findall(r"[a-z]+", f.read().lower())

    synth_words = simulate_unilateral_voynich(latin_words)

    v_h2, v_len, v_voc, v_r2, v_r3 = analyze_corpus_metrics(voy_words, 35000)
    l_h2, l_len, l_voc, l_r2, l_r3 = analyze_corpus_metrics(latin_words, 35000)
    s_h2, s_len, s_voc, s_r2, s_r3 = analyze_corpus_metrics(synth_words, 35000)

    print("=" * 94)
    print("GENERATIVE FORWARD SIMULATION: NATURAL LATIN vs. f(V_left, C) vs. ACTUAL VOYNICH")
    print("=" * 94)
    print(f"{'Metric (35,000 Tokens)':<30} | {'Natural Latin':>14} | {'Unilateral f(V,C)':>18} | {'Actual Voynich':>15}")
    print("-" * 94)
    print(f"{'Conditional Entropy H2 (bit)':<30} | {l_h2:14.4f} | {s_h2:18.4f} | {v_h2:15.4f}")
    print(f"{'Mean Word Length':<30} | {l_len:14.2f} | {s_len:18.2f} | {v_len:15.2f}")
    print(f"{'Unique Vocabulary (Vocab)':<30} | {l_voc:14d} | {s_voc:18d} | {v_voc:15d}")
    print(f"{'Adjacent 2x Repetitions':<30} | {l_r2:14d} | {s_r2:18d} | {v_r2:15d}")
    print(f"{'Adjacent 3x Repetitions':<30} | {l_r3:14d} | {s_r3:18d} | {v_r3:15d}")

    print("\nSample Generated Synthetic Voynich Tokens (First 25):")
    print(" ", " ".join(synth_words[:25]))
