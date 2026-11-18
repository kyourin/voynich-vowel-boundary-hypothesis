"""
    Evaluates all 348 standalone Zodiac star/nymph labels (folios f70v2 - f73v)
    under the Vowel-Boundary State Hypothesis:
     - Decomposes isolated tokens into Left-Vowel (L), Consonant-Core (C), and
Right-Vowel (R) functional locking structures (L+C+R, L+C, C+R).
     - Identifies iso-skeletal word families shifting across boundary tables.
     - Runs a 1,000-trial frequency-preserving permutation null-control test
against Medieval Ptolemaic/Alfonsine astronomical catalog terminology.
"""

import re
import math
import random
from pathlib import Path
from collections import Counter, defaultdict

REPO_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "ZL3b-n.txt"
LOCAL_FALLBACK_PATH = Path(
    r"ZL3b-n.txt"
)

CORE_KEY = {
    "t": "p", "k": "t", "r": "n", "d": "r", "s": "s",
    "l": "l", "m": "m", "ch": "c", "sh": "s", "f": "f", "p": "b", "n": "n"
}

PREFIX_RE = re.compile(r"^(qo|o|y|a|e)?(.*)$")
SUFFIX_RE = re.compile(r"^(.*?)(eedy|edy|eey|aiin|iin|ain|eol|eor|ol|or|al|ar|dy|ey|y|o|a)?$")

ZODIAC_FOLIOS = {
    "f70v2": ("Pisces",      "Water", ["pisces", "piscium"]),
    "f70v1": ("Aries_1",     "Fire",  ["aries", "arietis"]),
    "f71r":  ("Aries_2",     "Fire",  ["aries", "arietis"]),
    "f71v":  ("Taurus",      "Earth", ["taurus", "tauri", "aldebaran", "pleiades", "hyades"]),
    "f72r1": ("Gemini",      "Air",   ["gemini", "geminorum", "castor", "pollux"]),
    "f72r2": ("Cancer",      "Water", ["cancer", "cancri", "praesepe"]),
    "f72r3": ("Leo",         "Fire",  ["leo", "leonis", "regulus", "deneb"]),
    "f72v3": ("Virgo",       "Earth", ["virgo", "virginis", "spica", "vindemiatrix"]),
    "f72v2": ("Libra",       "Air",   ["libra", "librae", "chelae"]),
    "f72v1": ("Scorpius",    "Water", ["scorpius", "scorpii", "antares", "aculeus"]),
    "f73r":  ("Sagittarius", "Fire",  ["sagittarius", "sagittarii"]),
    "f73v":  ("Capricornus", "Earth", ["capricornus", "capricorni"])
}

GENERAL_ASTRO_TERMS = [
    "stella", "stellae", "stellarum", "sol", "solis", "luna", "lunae",
    "polus", "poli", "pars", "partis", "gradus", "signum", "signa","caput", "capitis", "cauda", "caudae", "cor", "cordis", "ala", "alae",
    "pes", "pedes", "pedis", "manus", "brachium", "humerus", "pectus","venter", "dorsum", "cornu", "cornua", "oculus", "frons", "oris",
    "crus", "genu", "tibia", "ungula", "spina", "collum", "caelum",
    "prima", "secunda", "tertia", "quarta", "quinta", "sexta", "ultima", "media","clara", "clarissima", "lucida", "obscura", "nebulosa", "magna", "parva",
    "australis", "borealis", "septentrionalis", "meridionalis","orientalis", "occidentalis", "antecedens", "sequens", "dexter", "sinister",
    "ignis", "terra", "aer", "aqua", "calida", "frigida", "humida", "sicca",
    "domus", "planeta", "splendor", "lucis", "noctis", "ortus", "occasus", "centrum"
]


def resolve_transcript_path() -> Path:
    if REPO_DATA_PATH.exists():
        return REPO_DATA_PATH
    if LOCAL_FALLBACK_PATH.exists():
        return LOCAL_FALLBACK_PATH
    raise FileNotFoundError(
        f"ZL3b-n.txt not found at {REPO_DATA_PATH} or {LOCAL_FALLBACK_PATH}. "
        "Please place ZL3b-n.txt inside the data/ directory."
    )


def decompose_functional_lock(word: str):
    m_pre = PREFIX_RE.match(word)
    v_pre = m_pre.group(1) or ""
    rest = m_pre.group(2)
    if not rest:
        return "VOWEL_BRIDGE", v_pre, "", ""

    m_suf = SUFFIX_RE.match(rest)
    c_body = m_suf.group(1)
    suf = m_suf.group(2) or ""

    if not c_body and suf:
        if suf.startswith("dy"):
            c_body, suf = "d", suf[1:]
        else:
            return "VOWEL_BRIDGE", v_pre, "", suf

    if v_pre and suf:
        return "BILATERAL (L+C+R)", v_pre, c_body, suf
    if v_pre:
        return "LEFT_LOCK (L+C)  ", v_pre, c_body, suf
    if suf:
        return "RIGHT_LOCK (C+R) ", v_pre, c_body, suf
    return "BARE_CORE (C)    ", v_pre, c_body, suf


def extract_voynich_consonants(word: str) -> list:
    w = re.sub(r"^qo", "", word)
    cons_groups = [g for g in re.split(r"[oaeiy]+", w) if g]
    tokens = []
    for g in cons_groups:
        tokens.extend(re.findall(r"ch|sh|cth|ckh|cph|cfh|.", g))
    return tokens


def latin_skeleton(word: str) -> str:
    w = word.lower().replace("qu", "k").replace("x", "ks").replace("z", "s")
    cons = [c for c in w if c not in "aeiouy"]
    dedup = []
    for c in cons:
        if not dedup or dedup[-1] != c:
            dedup.append(c)
    return "".join(dedup)


def build_lexicon_index(terms: list) -> dict:
    idx = defaultdict(list)
    for term in terms:
        sk = latin_skeleton(term)
        if len(sk) >= 2:
            if term not in idx[sk]:
                idx[sk].append(term)
            if len(sk) >= 3 and sk.startswith("s"):
                short_sk = sk[1:]
                if f"*{term}" not in idx[short_sk]:
                    idx[short_sk].append(f"*{term}")
    return idx


def load_zodiac_labels(transcript_path: Path) -> list:
    records = []
    with open(transcript_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^<([^>]+)>\s+(.*)$", line)
            if match:
                tag = match.group(1)
                fol = next(iter(re.split(r"[.,\s]", tag)))
                if fol in ZODIAC_FOLIOS and "@Cc" not in tag:
                    clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
                    ws = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]
                    for w in ws:
                        records.append((fol, w))
    return records


def evaluate_key(multi_cons_records: list, key_map: dict, gen_idx: dict, fol_idx: dict):
    hits = 0
    long_hits = 0
    matched_anchors = []

    for fol, w, v_cons in multi_cons_records:
        mapped = "".join(key_map.get(c, "?") for c in v_cons)
        dedup = "".join(c for i, c in enumerate(mapped) if i == 0 or c != mapped[i - 1])

        cands = list(gen_idx.get(dedup, [])) + list(fol_idx[fol].get(dedup, []))

        if not cands and "k" in v_cons:
            alt_key = dict(key_map)
            alt_key["k"] = key_map.get("ch", "c")
            m2 = "".join(alt_key.get(c, "?") for c in v_cons)
            d2 = "".join(c for i, c in enumerate(m2) if i == 0 or c != m2[i - 1])
            cands = [f"~{t}" for t in (gen_idx.get(d2, []) + fol_idx[fol].get(d2, []))]

        if cands:
            hits += 1
            if len(v_cons) >= 3:
                long_hits += 1
            matched_anchors.append((fol, w, dedup, cands))

    return hits, long_hits, matched_anchors


def calc_z_stats(observed: int, null_dist: list):
    mean = sum(null_dist) / len(null_dist)
    var = sum((x - mean) ** 2 for x in null_dist) / len(null_dist)
    sd = math.sqrt(var) if var > 0 else 1e-9
    z_score = (observed - mean) / sd
    p_val = sum(1 for x in null_dist if x >= observed) / len(null_dist)
    return mean, sd, z_score, p_val


def main():
    transcript_path = resolve_transcript_path()
    records = load_zodiac_labels(transcript_path)

    lock_counts = Counter()
    skeleton_families = defaultdict(list)
    multi_cons_records = []

    for fol, w in records:
        lock_type, _, _, _ = decompose_functional_lock(w)
        lock_counts[lock_type] += 1

        v_cons = extract_voynich_consonants(w)
        if v_cons:
            m = "".join(CORE_KEY.get(c, "?") for c in v_cons)
            sk = "".join(c for i, c in enumerate(m) if i == 0 or c != m[i - 1])
            sign = ZODIAC_FOLIOS[fol]
            skeleton_families[sk].append((w, sign))
            if len(v_cons) >= 2:
                multi_cons_records.append((fol, w, v_cons))

    total_labels = len(records)
    print("=" * 94)
    print(f"1. ZODIAC STANDALONE STAR-LABEL FUNCTIONAL LOCKING (N = {total_labels} TOKENS)")
    print("=" * 94)
    for ltype, cnt in lock_counts.most_common():
        print(f"  {ltype:<20} : {cnt:>3} ({cnt / total_labels * 100:5.2f}%)")

    print("\n" + "=" * 94)
    print("2. TOP ISO-SKELETAL CONSONANT FAMILIES ACROSS VOWEL BOUNDARY TABLES")
    print("=" * 94)
    for sk, items in sorted(skeleton_families.items(), key=lambda x: len(x[-1]), reverse=True)[:8]:
        unique_forms = sorted(set(item for item in items))
        if len(unique_forms) >= 3:
            print(f"  Skeleton '{sk:<4}' ({len(items):>2}x) -> {', '.join(unique_forms[:7])}")

    gen_idx = build_lexicon_index(GENERAL_ASTRO_TERMS)
    fol_idx = {fol: build_lexicon_index(terms) for fol, (_, _, terms) in ZODIAC_FOLIOS.items()}

    real_hits, real_long, anchors = evaluate_key(multi_cons_records, CORE_KEY, gen_idx, fol_idx)

    random.seed(42)
    n_trials = 1000
    keys_list = list(CORE_KEY.keys())
    vals_list = list(CORE_KEY.values())
    null_hits_dist = []
    null_long_dist = []

    for _ in range(n_trials):
        shuffled_vals = vals_list[:]
        random.shuffle(shuffled_vals)
        null_key = dict(zip(keys_list, shuffled_vals))
        nh, nl, _ = evaluate_key(multi_cons_records, null_key, gen_idx, fol_idx)
        null_hits_dist.append(nh)
        null_long_dist.append(nl)

    m_all, sd_all, z_all, p_all = calc_z_stats(real_hits, null_hits_dist)
    m_lng, sd_lng, z_lng, p_lng = calc_z_stats(real_long, null_long_dist)

    print("\n" + "=" * 94)
    print(f"3. 1,000-TRIAL PERMUTATION NULL-CONTROL BENCHMARK (N = {len(multi_cons_records)} MULTI-CONSONANT LABELS)")
    print("=" * 94)
    print(f"  {'Metric':<36} | {'Real Key':>8} | {'Null Mean (±SD)':>16} | {'Z-Score':>8} | {'Emp. p':>7}")
    print("-" * 94)
    print(f"  {'Astronomical Term Hits (2+ Cons.)':<36} | {real_hits:>8} | {m_all:>6.2f} ± {sd_all:<6.2f}  | {z_all:>+7.2f}σ | {p_all:>7.4f}")
    print(f"  {'High-Confidence Anchors (3+ Cons.)':<36} | {real_long:>8} | {m_lng:>6.2f} ± {sd_lng:<6.2f}  | {z_lng:>+7.2f}σ | {p_lng:>7.4f}")
    print("=" * 94)

    print("\n4. HIGH-CONFIDENCE (3+ CONSONANT) RESOLVED ZODIAC ANCHORS:")
    for fol, w, sk, cands in anchors:
        if len(extract_voynich_consonants(w)) >= 3:
            sign = ZODIAC_FOLIOS[fol][0]
            print(f"  [{fol:<5} | {sign:<11}] {w:<12} ({sk:<4}) => {', '.join(cands[:4])}")


if __name__ == "__main__":
    main()
