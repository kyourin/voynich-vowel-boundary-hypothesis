import re
import math
from pathlib import Path
from collections import Counter, defaultdict
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

PREFIXES = sorted(["qok", "qot", "qo", "ch", "sh", "ok", "ot", "o", "y", "d", "s", "l", "r"], key=len, reverse=True)
SUFFIXES = sorted(["eedy", "aiin", "iin", "edy", "ody", "ey", "dy", "ol", "or", "ar", "al", "am", "om", "in", "y"], key=len, reverse=True)

def get_prefix(word):
    for p in PREFIXES:
        if word.startswith(p) and len(word) > len(p):
            return p
    return word

def get_suffix(word):
    for s in SUFFIXES:
        if word.endswith(s) and len(word) > len(s):
            return s
    return word[-1]

# EXTRACT CONSECUTIVE WORD TRIPLETS (Word_{i-1}, Word_i, Word_{i+1})
voynich_lines = []
with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            words = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]
            if len(words) >= 3:
                voynich_lines.append(words)

# Group (Suffix_{i-1}, Prefix_{i+1}) pairs conditioned on the exact fixed middle word Word_i
conditioned_pairs = defaultdict(list)
for line in voynich_lines:
    for i in range(1, len(line) - 1):
        w_prev, w_mid, w_next = line[i - 1], line[i], line[i + 1]
        conditioned_pairs[w_mid].append((get_suffix(w_prev), get_prefix(w_next)))

# Filter to middle words occurring >= 15 times so conditional distributions are statistically stable
valid_groups = {w: pairs for w, pairs in conditioned_pairs.items() if len(pairs) >= 15}
total_triplets = sum(len(pairs) for pairs in valid_groups.values())

# COMPUTE CONDITIONAL MUTUAL INFORMATION I(S_{i-1}; P_{i+1} | W_i)
def compute_cmi(groups_dict):
    total_n = sum(len(v) for v in groups_dict.values())
    cmi_bits = 0.0
    per_word_mi = {}

    for w_mid, pairs in groups_dict.items():
        n_w = len(pairs)
        p_w = n_w / total_n
        joint = Counter(pairs)
        s_counts = Counter(s for s, _ in pairs)
        p_counts = Counter(p for _, p in pairs)

        mi_w = 0.0
        for (s, p), cnt in joint.items():
            p_sp = cnt / n_w
            p_s = s_counts[s] / n_w
            p_p = p_counts[p] / n_w
            mi_w += p_sp * math.log2(p_sp / (p_s * p_p))

        per_word_mi[w_mid] = (n_w, mi_w)
        cmi_bits += p_w * mi_w

    return cmi_bits, per_word_mi

observed_cmi, per_word_stats = compute_cmi(valid_groups)

# EXACT WITHIN-GROUP PERMUTATION BASELINE (1,000 SHUFFLES)
rng = np.random.default_rng(42)
null_cmis = []

# Pre-extract arrays for fast permutation
pre_arrays = {}
for w_mid, pairs in valid_groups.items():
    s_arr = [s for s, _ in pairs]
    p_arr = np.array([p for _, p in pairs])
    pre_arrays[w_mid] = (s_arr, p_arr)

for _ in range(1000):
    shuffled_groups = {}
    for w_mid, (s_arr, p_arr) in pre_arrays.items():
        p_perm = rng.permutation(p_arr)
        shuffled_groups[w_mid] = list(zip(s_arr, p_perm))
    null_val, _ = compute_cmi(shuffled_groups)
    null_cmis.append(null_val)

null_mean = float(np.mean(null_cmis))
null_std = float(np.std(null_cmis))
excess_cmi = observed_cmi - null_mean
z_score = excess_cmi / (null_std + 1e-12)
p_val = np.mean([1.0 if x >= observed_cmi else 0.0 for x in null_cmis])

print("=" * 82)
print("SECOND-ORDER BOUNDARY CONDITIONAL MUTUAL INFORMATION TEST")
print("Metric: I(Suffix_{i-1} ; Prefix_{i+1} | Middle_Word_i)")
print("=" * 82)
print(f"Evaluated Triplets (Middle Word >= 15 occ.) : {total_triplets:,} across {len(valid_groups)} unique middle words")
print(f"Observed Conditional Mutual Info (CMI)      : {observed_cmi:.5f} bits")
print(f"Shuffled Null Baseline (1,000 permutations) : {null_mean:.5f} ± {null_std:.5f} bits")
print(f"Excess Information Passing Through Word_i   : +{excess_cmi:.5f} bits")
print(f"Statistical Significance                    : Z = +{z_score:.2f}σ (empirical p = {p_val:.4f})")
print("-" * 82)
print("Top 12 High-Frequency Middle Words & Their Excess Boundary MI:")

top_mid = sorted(per_word_stats.items(), key=lambda x: x[1][0], reverse=True)[:12]
for w_mid, (cnt, mi_val) in top_mid:
    print(f"  Middle Word: '{w_mid:<8}' (n = {cnt:4d}) -> Local Boundary MI: {mi_val:.4f} bits")
print("=" * 82)
