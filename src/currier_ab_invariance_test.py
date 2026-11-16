import re
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

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

def classify_currier(folio_tag):
    m = re.search(r"f(\d+)", folio_tag.lower())
    if not m:
        return None
    f_num = int(m.group(1))
    # Standard Voynich manuscript section split:
    # Currier A: Herbal A + Pharma (f1-f66, f87-f102)
    # Currier B: Astro/Cosmo + Biological/Balneological + Recipes (f67-f86, f103-f116)
    if (1 <= f_num <= 66) or (87 <= f_num <= 102):
        return "A"
    elif (67 <= f_num <= 86) or (103 <= f_num <= 116):
        return "B"
    return None

lines_A, lines_B = [], []

with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            tag = match.group(1)
            sec = classify_currier(tag)
            if not sec:
                continue
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            words = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]
            if len(words) > 1:
                if sec == "A":
                    lines_A.append(words)
                else:
                    lines_B.append(words)

def get_normalized_matrix(lines, row_labels, col_labels):
    transitions = Counter()
    for line in lines:
        for i in range(len(line) - 1):
            transitions[(get_suffix(line[i]), get_prefix(line[i + 1]))] += 1
    mat = pd.DataFrame(0.0, index=row_labels, columns=col_labels)
    for (s, p), cnt in transitions.items():
        if s in row_labels and p in col_labels:
            mat.loc[s, p] = cnt
    P = mat.values / (mat.values.sum() + 1e-12)
    rp = P.sum(axis=1, keepdims=True)
    cp = P.sum(axis=0, keepdims=True)
    return (P - rp @ cp) / np.sqrt(rp @ cp + 1e-12)

# Use shared boundary vocabulary across both sections
all_lines = lines_A + lines_B
suf_all = Counter(get_suffix(w) for line in all_lines for w in line)
pre_all = Counter(get_prefix(w) for line in all_lines for w in line)

shared_suffixes = [s for s, c in suf_all.items() if c >= 15]
shared_prefixes = [p for p, c in pre_all.items() if c >= 15]

norm_A = get_normalized_matrix(lines_A, shared_suffixes, shared_prefixes)
norm_B = get_normalized_matrix(lines_B, shared_suffixes, shared_prefixes)

U_A, S_A, Vt_A = np.linalg.svd(norm_A, full_matrices=False)
U_B, S_B, Vt_B = np.linalg.svd(norm_B, full_matrices=False)

var_A = (S_A ** 2) / np.sum(S_A ** 2) * 100
var_B = (S_B ** 2) / np.sum(S_B ** 2) * 100

# Subspace Principal Angles & Grassmannian Projection Similarity for Top-5 Dimensions (k=5)
def subspace_similarity(U1, U2, k=5):
    Q1 = U1[:, :k]
    Q2 = U2[:, :k]
    _, sigmas, _ = np.linalg.svd(Q1.T @ Q2)
    sigmas = np.clip(sigmas, 0.0, 1.0)
    angles_deg = np.degrees(np.arccos(sigmas))
    mean_cos = float(np.mean(sigmas))
    return mean_cos, angles_deg

u_sim, u_angles = subspace_similarity(U_A, U_B, k=5)
v_sim, v_angles = subspace_similarity(Vt_A.T, Vt_B.T, k=5)

# Monte Carlo Random Subspace Baseline (1,000 trials)
rng = np.random.default_rng(42)
rand_u_sims, rand_v_sims = [], []
for _ in range(1000):
    R1_u, _ = np.linalg.qr(rng.standard_normal((len(shared_suffixes), 5)))
    R2_u, _ = np.linalg.qr(rng.standard_normal((len(shared_suffixes), 5)))
    _, s_u, _ = np.linalg.svd(R1_u.T @ R2_u)
    rand_u_sims.append(np.mean(s_u))

    R1_v, _ = np.linalg.qr(rng.standard_normal((len(shared_prefixes), 5)))
    R2_v, _ = np.linalg.qr(rng.standard_normal((len(shared_prefixes), 5)))
    _, s_v, _ = np.linalg.svd(R1_v.T @ R2_v)
    rand_v_sims.append(np.mean(s_v))

z_u = (u_sim - np.mean(rand_u_sims)) / np.std(rand_u_sims)
z_v = (v_sim - np.mean(rand_v_sims)) / np.std(rand_v_sims)

print("=" * 78)
print("CURRIER A vs. CURRIER B 5-DIMENSIONAL BOUNDARY SUBSPACE INVARIANCE TEST")
print("=" * 78)
print(f"Currier A Lines: {len(lines_A):,} | Currier B Lines: {len(lines_B):,}")
print(f"Shared Boundary Dimensions: {len(shared_suffixes)} Suffixes x {len(shared_prefixes)} Prefixes\n")

print(f"Currier A Top-5 Cumulative Variance : {np.sum(var_A[:5]):.2f}%  {np.round(var_A[:5], 2)}")
print(f"Currier B Top-5 Cumulative Variance : {np.sum(var_B[:5]):.2f}%  {np.round(var_B[:5], 2)}\n")

print(f"Suffix Subspace (U_5) Cosine Similarity : {u_sim:.4f} (Random Baseline: {np.mean(rand_u_sims):.4f} | Z-Score: +{z_u:.2f}σ)")
print(f"  Principal Angles (Degrees)            : {np.round(u_angles, 1)}°")
print(f"Prefix Subspace (V_5) Cosine Similarity : {v_sim:.4f} (Random Baseline: {np.mean(rand_v_sims):.4f} | Z-Score: +{z_v:.2f}σ)")
print(f"  Principal Angles (Degrees)            : {np.round(v_angles, 1)}°")
print("=" * 78)
