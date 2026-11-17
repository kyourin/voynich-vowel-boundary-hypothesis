import os
import re
import math
import random
import numpy as np
from collections import Counter, defaultdict

VOYNICH_PATH = r"ZL3b-n.txt"
PURE_LATIN_PATH = r"pure_latin_corpus.txt"
OUTPUT_TXT_PATH = r"voynich_full_decoded_latin.txt"

PREFIX_RE = re.compile(r"^(qo|o|y|a|e)?(.*)$")
SUFFIX_RE = re.compile(r"^(.*?)(eedy|edy|eey|aiin|iin|ain|eol|eor|ol|or|al|ar|dy|ey|y|o|a)?$")

STRICT_BOUNDARY_WORDS = {
    "daiin", "dain", "aiin", "ol", "or", "al", "ar",
    "dy", "y", "o", "s", "r", "l", "d"
}

JOINED_CLUSTER_SPLITS = {
    "mc": ["m", "c"], "ms": ["m", "s"], "mv": ["m", "v"], "md": ["m", "d"],
    "mpr": ["m", "pr"], "mr": ["m", "r"], "mf": ["m", "f"], "mt": ["m", "t"],
    "sd": ["s", "d"], "sm": ["s", "m"], "sn": ["s", "n"], "sv": ["s", "v"],
    "sf": ["s", "f"], "tc": ["t", "c"], "rp": ["r", "p"], "sl": ["s", "l"],
    "spr": ["s", "pr"], "tpr": ["t", "pr"], "sts": ["s", "ts"],
    "nts": ["nt", "s"], "rf": ["r", "f"], "sr": ["s", "r"],
    "tm": ["t", "m"], "tv": ["t", "v"], "tf": ["t", "f"]
}

GEO_AND_PROPER_STOPWORDS = {
    "italia", "italiae", "italiam", "asia", "asiae", "asiam", "asiamque",
    "parma", "parmae", "roma", "romae", "romam", "romani", "romano",
    "gallia", "galliae", "syria", "syriae", "aegypto", "aegypti", "graeci",
    "graecia", "africa", "hispania", "creta", "ponti", "europa", "marcio",
    "marcius", "caesar", "cato", "catonis", "plinius", "galenus", "ascanium",
    "sma", "ems", "md", "poeta", "cottae", "tusci", "ionicae", "actiaci",
    "scite", "iudicavi", "audacia", "stulte", "amici", "mensa", "cenae"
}

MED_BOT_TERMS = {
    "oleris", "vineae", "urinae", "vino", "vinum", "vini", "resina", "illita",
    "lintea", "adipe", "immaturae", "ascalia", "acaciae", "ustione", "potui",
    "musti", "aqua", "aquae", "oleum", "oleo", "melle", "mel", "cera", "radix",
    "folia", "semen", "herba", "flos", "sucus", "cortex", "cinis", "sal", "aceto",
    "balneum", "balneo", "corpus", "caput", "venter", "sanguis", "dolor", "tumor",
    "curatio", "medicina", "sanat", "utile", "coquitur", "teritur", "bibitur", "fiet",
    "cerati", "scillae", "casia", "mulsi", "lenti", "taeda", "satureia",
    "pomi", "inguina", "anguium", "ostrea", "cinerem", "igni", "ignem",
    "pota", "sebo", "tepida", "alluitur", "arbuti", "erucae", "ervi", "apium", "lauri"
}


def decompose_voynich_word(w):
    m_pre = PREFIX_RE.match(w)
    v_pre, rest = m_pre.group(1) or "", m_pre.group(2)
    if not rest:
        return v_pre, "", ""
    m_suf = SUFFIX_RE.match(rest)
    c_body, suf = m_suf.group(1), m_suf.group(2) or ""
    if not c_body and suf:
        if suf.startswith(("dy", "eedy", "edy", "eey", "eol", "eor", "ey")):
            c_body = "d" if suf.startswith("dy") else ""
    return v_pre, c_body, suf

def load_voynich_corpora(path):
    line_paragraphs = []
    full_paragraphs = []
    body_freq = Counter()

    cur_tag = None
    cur_words = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
            if match and not line.startswith("#"):
                tag = match.group(1)
                if "@P" in tag or "+P" in tag or "=P" in tag:
                    cleaned = re.sub(r"\[([^:\]]+):[^\]]+\]", r"\1", match.group(2))
                    cleaned = re.sub(r"<[^>]+>|[!?*%'\"\{\};:-]", "", cleaned)
                    ws = [w for w in re.split(r"[.,\s]+", cleaned) if w and w.isalpha()]
                    if not ws:
                        continue
                    if len(ws) >= 3:
                        line_paragraphs.append((tag, ws))
                    for w in ws:
                        _, cb, _ = decompose_voynich_word(w)
                        if cb:
                            body_freq[cb] += 1

                    if "@P" in tag:
                        if cur_tag and cur_words:
                            full_paragraphs.append((cur_tag, cur_words))
                        cur_tag = tag
                        cur_words = list(ws)
                    else:
                        cur_words.extend(ws)

    if cur_tag and cur_words:
        full_paragraphs.append((cur_tag, cur_words))

    return line_paragraphs, full_paragraphs, body_freq

def load_clean_latin(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_toks = re.findall(r"[A-Za-z]+", f.read())

    cap_freq = Counter()
    low_freq = Counter()
    for t in raw_toks:
        wl = t.lower()
        if t.isupper():
            cap_freq[wl] += 1
        else:
            low_freq[wl] += 1

    clean_words = [
        t.lower() for t in raw_toks
        if t.lower() not in GEO_AND_PROPER_STOPWORDS
        and low_freq[t.lower()] >= cap_freq[t.lower()]
    ]

    word_freq = Counter(clean_words)
    bigram_freq = Counter(zip(clean_words[:-1], clean_words[1:]))

    cont_latin = "".join(clean_words[:250000])
    lat_c_stream = [blk for blk in re.findall(r"[^aeiou]+", cont_latin)]
    lat_c_freq = Counter(lat_c_stream)

    lat_bg = Counter(zip(lat_c_stream[:-1], lat_c_stream[1:]))
    tot_lbg = sum(lat_bg.values())
    lat_bg_logp = {k: math.log((v + 0.2) / (tot_lbg + 1000.0)) for k, v in lat_bg.items()}

    cseq_to_words = defaultdict(list)
    for w, cnt in word_freq.items():
        if cnt >= 2 and len(w) >= 2:
            sk = tuple(re.findall(r"[^aeiou]+", w))
            if 1 <= len(sk) <= 5:
                cseq_to_words[sk].append((w, cnt))

    for k in cseq_to_words:
        cseq_to_words[k].sort(key=lambda x: x[-1], reverse=True)
        cseq_to_words[k] = cseq_to_words[k][:8]

    return clean_words, word_freq, bigram_freq, lat_c_freq, lat_bg_logp, cseq_to_words


def train_body_and_vowel_maps(line_paragraphs, body_freq, lat_c_freq, lat_bg_logp, cseq_to_words, seed=2026):
    top_50_bodies = [b for b, _ in body_freq.most_common(50)]
    b2idx = {b: i for i, b in enumerate(top_50_bodies)}
    top_50_latin_c = [c for c, _ in lat_c_freq.most_common(50)]

    voy_bg = Counter()
    tot_vbg = 0
    for _, ws in line_paragraphs:
        idxs = [b2idx[decompose_voynich_word(w)] for w in ws if decompose_voynich_word(w) in b2idx]
        for a, b in zip(idxs[:-1], idxs[1:]):
            voy_bg[(a, b)] += 1
            tot_vbg += 1
    voy_bg_prob = {k: v / max(1, tot_vbg) for k, v in voy_bg.items()}

    rng = random.Random(seed)
    assign = list(range(50))

    def score_50(asg):
        return sum(
            vp * lat_bg_logp.get((top_50_latin_c[asg[vi]], top_50_latin_c[asg[vj]]), -15.0)
            for (vi, vj), vp in voy_bg_prob.items()
        )

    cur_sc = score_50(assign)
    best_asg = list(assign)
    best_sc = cur_sc

    for step in range(1, 70001):
        temp = max(0.00005, 0.06 * ((1.0 - step / 70000) ** 2))
        i, j = rng.sample(range(50), 2)
        assign[i], assign[j] = assign[j], assign[i]
        n_sc = score_50(assign)
        if n_sc > cur_sc or rng.random() < math.exp((n_sc - cur_sc) / temp):
            cur_sc = n_sc
            if n_sc > best_sc:
                best_sc = n_sc
                best_asg = list(assign)
        else:
            assign[i], assign[j] = assign[j], assign[i]

    body_to_latin_50 = {top_50_bodies[i]: top_50_latin_c[best_asg[i]] for i in range(50)}

    # Önek ve sonek ünlü ipuçlarını hizala
    pre_v_votes = defaultdict(Counter)
    suf_v_votes = defaultdict(Counter)

    for _, ws in line_paragraphs[:1500]:
        c_list, meta = [], []
        for w in ws:
            vp, cb, sf = decompose_voynich_word(w)
            if cb in body_to_latin_50:
                c_list.append(body_to_latin_50[cb])
                meta.append((vp, sf))
        i = 0
        while i < len(c_list):
            matched = False
            for L in (4, 3, 2):
                if i + L > len(c_list):
                    continue
                sub = tuple(c_list[i:i+L])
                if sub in cseq_to_words:
                    best_w, cnt = next(iter(cseq_to_words[sub]))
                    v_parts = re.findall(r"[aeiou]+", best_w)
                    if len(v_parts) >= L:
                        for step in range(L):
                            vp, sf = meta[i + step]
                            if step == 0 and best_w in "aeiou":
                                pre_v_votes[vp][best_w] += cnt
                            suf_v_votes[sf][v_parts[step][-1]] += cnt
                    i += L
                    matched = True
                    break
            if not matched:
                i += 1

    pre_v_map = {vp: (next(iter(cnts.most_common(1))) if cnts else "") for vp, cnts in pre_v_votes.items()}
    suf_v_map = {sf: (next(iter(cnts.most_common(1))) if cnts else "") for sf, cnts in suf_v_votes.items()}

    # 120 gövdeye genişletme
    top_120_bodies = [b for b, _ in body_freq.most_common(120)]
    top_120_latin_c = [c for c, _ in lat_c_freq.most_common(120)]
    b120_to_idx = {b: i for i, b in enumerate(top_120_bodies)}

    bg_120 = Counter()
    tot_120 = 0
    for _, ws in line_paragraphs:
        idxs = [b120_to_idx[decompose_voynich_word(w)] for w in ws if decompose_voynich_word(w) in b120_to_idx]
        for a, b in zip(idxs[:-1], idxs[1:]):
            bg_120[(a, b)] += 1
            tot_120 += 1
    prob_120 = {k: v / max(1, tot_120) for k, v in bg_120.items()}

