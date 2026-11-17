import os
import re
import math
import random
import numpy as np
from collections import Counter, defaultdict

def find_data(filename):
    search_dirs = [
        ".",
        "data",
        "../data",
        "03_REPRODUCIBILITY",
        "../03_REPRODUCIBILITY",
        os.path.dirname(os.path.abspath(__file__)),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"),
    ]
    for d in search_dirs:
        candidate = os.path.join(d, filename)
        if os.path.exists(candidate):
            return candidate
    for root, _, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)
    raise FileNotFoundError(f"Required data file '{filename}' not found in repository paths.")

voynich_path = find_data("ZL3b-n.txt")
pure_latin_path = find_data("pure_latin_corpus.txt")

PROPER_NOUN_BLACKLIST = {
    "italia", "italiae", "romae", "romam", "romano", "romani", "caesar", "caesaris",
    "catonis", "cato", "mucianus", "muciani", "menelai", "menelaus", "epigene",
    "susiane", "caucasi", "titen", "tuder", "pago", "alexandria", "graeci", "graecis",
    "aegypto", "aegypti", "syria", "syriae", "gallia", "hispania", "africa", "creta",
    "rhodo", "cypro", "ponti", "asia", "asiae", "europa", "theophrastus", "hippocrates",
    "galenus", "plinius", "celsus", "varro", "vergilius", "cicero", "augustus", "nero"
}

MEDICAL_BOTANICAL_TERMS = {
    "semen", "seminis", "seminum", "urticae", "urtica", "oleo", "oleum", "olei",
    "cera", "cerae", "ceram", "sucum", "sucus", "suci", "adipe", "adeps", "adipem",
    "cicutae", "cicuta", "laser", "laseris", "susino", "susinum", "foliis", "folia",
    "rapum", "rapi", "lini", "linum", "cinis", "cineris", "teporem", "tepore",
    "utile", "utilis", "salutare", "auxilia", "auxilium", "ovorum", "ova", "ovis",
    "ramis", "rami", "radice", "radix", "radicis", "herba", "herbae", "herbam",
    "aqua", "aquae", "aquam", "vino", "vinum", "vini", "melle", "mel", "mellis",
    "salicis", "salix", "sapa", "sapae", "pomo", "pomum", "caput", "capitis",
    "capita", "pedes", "pedis", "macula", "maculae", "macie", "dolor", "dolorem",
    "sanat", "sanari", "utatur", "medicina", "medicamenta", "unguentum", "potio",
    "potione", "cocta", "coctum", "trita", "tritum", "misce", "miscetur", "sitis"
}

with open(pure_latin_path, "r", encoding="utf-8", errors="ignore") as f:
    raw_tokens = re.findall(r"[A-Za-z]+", f.read())

cap_counts = Counter()
low_counts = Counter()
for tok in raw_tokens:
    w_low = tok.lower()
    if tok.isupper():
        cap_counts[w_low] += 1
    else:
        low_counts[w_low] += 1

latin_words = [
    tok.lower() for tok in raw_tokens
    if tok.lower() not in PROPER_NOUN_BLACKLIST
    and not (cap_counts[tok.lower()] > low_counts[tok.lower()] * 2 and len(tok) >= 4)
]

word_freq = Counter(latin_words)
bigram_freq = Counter(zip(latin_words[:-1], latin_words[1:]))
tot_words = sum(word_freq.values())

latin_c_counts = Counter()
skel_dict = defaultdict(list)
cseq_to_words = defaultdict(list)

for w, c in word_freq.items():
    if c >= 2:
        sk = tuple(re.findall(r"[^aeiou]+", w))
        for blk in sk:
            latin_c_counts[blk] += c
        if 1 <= len(sk) <= 6:
            cseq_to_words[sk].append((w, c))
        if c >= 3 and len(w) >= 3 and 2 <= len(sk) <= 5:
            skel_dict[sk].append((w, c))

for sk in skel_dict:
    skel_dict[sk].sort(key=lambda item: item[-1], reverse=True)
    skel_dict[sk] = skel_dict[sk][:3]

for sk in cseq_to_words:
    cseq_to_words[sk].sort(key=lambda item: item[-1], reverse=True)
    cseq_to_words[sk] = cseq_to_words[sk][:6]

tot_latin_c = sum(latin_c_counts.values())
max_c_share = {c: (cnt / tot_latin_c) * 1.25 for c, cnt in latin_c_counts.items()}

def bigram_logp(w1, w2):
    c1 = word_freq[w1]
    c12 = bigram_freq[(w1, w2)]
    if c12 > 0:
        return math.log((c12 + 0.5) / (c1 + 10.0)) + 2.5
    return math.log(0.05 / (c1 + 50.0))

all_paragraphs = []
voy_word_freq = Counter()

with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            tag = match.group(1)
            if "@P" in tag or "+P" in tag or "=P" in tag:
                clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
                words = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]
                if len(words) >= 3:
                    all_paragraphs.append((tag, words))
                    voy_word_freq.update(words)

tot_voy_tokens = sum(voy_word_freq.values())

CORE_KEY = {
    "qokedy": "r",
    "qokeey": "t",
    "or": "n",
    "qokeedy": "s",
    "ytaiin": "m",
    "qotey": "st",
    "oteey": "p"
}

for rnd in range(1, 5):
    votes = Counter()
    for tag, ws in all_paragraphs:
        for L in (3, 4):
            for i in range(len(ws) - L + 1):
                win = ws[i:i+L]
                unks = [idx for idx, w in enumerate(win) if w not in CORE_KEY]
                if len(unks) == 1:
                    u_idx = next(iter(unks))
                    u_w = win[u_idx]
                    for sk, w_list in skel_dict.items():
                        if len(sk) == L:
                            if all(sk[p] == CORE_KEY[win[p]] for p in range(L) if p != u_idx):
                                _, top_freq = next(iter(w_list))
                                votes[(u_w, sk[u_idx])] += top_freq

    used_c_tokens = Counter()
    for vw, cv in CORE_KEY.items():
        used_c_tokens[cv] += voy_word_freq[vw]

    for (vw, cv), sc in votes.most_common():
        if vw in CORE_KEY or sc < 250:
            continue
        projected_share = (used_c_tokens[cv] + voy_word_freq[vw]) / tot_voy_tokens
        if projected_share <= max_c_share.get(cv, 0.05):
            CORE_KEY[vw] = cv
            used_c_tokens[cv] += voy_word_freq[vw]

def restore_latin_segment(c_list):
    n = len(c_list)
    if n == 0:
        return []
    dp = [{} for _ in range(n + 1)]
    first_dict = next(iter(dp))
    first_dict["<BOS>"] = (0.0, None, -1)

    for i in range(n):
        if not dp[i]:
            continue
        for L in range(1, min(6, n - i + 1)):
            sub_sk = tuple(c_list[i:i + L])
            if sub_sk in cseq_to_words:
                for cand_w, w_cnt in cseq_to_words[sub_sk]:
                    unigram_bonus = math.log((w_cnt + 1.0) / tot_words)
                    for prev_w, (prev_sc, _, _) in dp[i].items():
                        sc = prev_sc + bigram_logp(prev_w, cand_w) + 0.35 * unigram_bonus + (L * 0.8)
                        if cand_w not in dp[i + L]:
                            dp[i + L][cand_w] = (sc, prev_w, i)
                        else:
                            old_sc, _, _ = dp[i + L][cand_w]
                            if sc > old_sc:
                                dp[i + L][cand_w] = (sc, prev_w, i)

        if all(not dp[i + step] for step in range(1, min(6, n - i + 1))):
            raw_tok = f"[{c_list[i]}]"
            for prev_w, (prev_sc, _, _) in dp[i].items():
                sc = prev_sc - 8.0
                if raw_tok not in dp[i + 1]:
                    dp[i + 1][raw_tok] = (sc, prev_w, i)
                else:
                    old_sc, _, _ = dp[i + 1][raw_tok]
                    if sc > old_sc:
                        dp[i + 1][raw_tok] = (sc, prev_w, i)

    best_last_w = None
    best_final_sc = -1e18
    for w, (sc, _, _) in dp[n].items():
        if sc > best_final_sc:
            best_final_sc = sc
            best_last_w = w

    words_out = []
    cur_i = n
    cur_w = best_last_w
    while cur_i > 0 and cur_w != "<BOS>":
        words_out.append(cur_w)
        _, prev_w, prev_i = dp[cur_i][cur_w]
        cur_w = prev_w
        cur_i = prev_i

    return list(reversed(words_out))

f103r_lines = [(tag, ws) for tag, ws in all_paragraphs if tag.startswith("f103r.")]

def score_key_on_f103r(key_map):
    med_hits = 0
    valid_words = 0
    raw_penalties = 0
    bigram_matches = 0

    for _, ws in f103r_lines:
        c_seq = [key_map.get(w, "?") for w in ws]
        cur_seg = []
        for c in c_seq:
            if c != "?":
                cur_seg.append(c)
            else:
                if cur_seg:
                    restored = restore_latin_segment(cur_seg)
                    for idx, rw in enumerate(restored):
                        if rw.startswith("["):
                            raw_penalties += 1
                        else:
                            valid_words += 1
                            if rw in MEDICAL_BOTANICAL_TERMS:
                                med_hits += 1
                            if idx > 0 and not restored[idx-1].startswith("["):
                                if bigram_freq[(restored[idx-1], rw)] > 0:
                                    bigram_matches += 1
                    cur_seg = []
        if cur_seg:
            restored = restore_latin_segment(cur_seg)
            for idx, rw in enumerate(restored):
                if rw.startswith("["):
                    raw_penalties += 1
                else:
                    valid_words += 1
                    if rw in MEDICAL_BOTANICAL_TERMS:
                        med_hits += 1
                    if idx > 0 and not restored[idx-1].startswith("["):
                        if bigram_freq[(restored[idx-1], rw)] > 0:
                            bigram_matches += 1

    return med_hits, bigram_matches, valid_words, raw_penalties

if __name__ == "__main__":
    real_med, real_bg, real_val, real_pen = score_key_on_f103r(CORE_KEY)
    rng = random.Random(2026)
    keys_list = list(CORE_KEY.keys())
    vals_list = list(CORE_KEY.values())

    null_med_scores, null_bg_scores, null_pen_scores = [], [], []
    for _ in range(25):
        shuffled_vals = list(vals_list)
        rng.shuffle(shuffled_vals)
