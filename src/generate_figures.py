import re
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

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
latin_path = find_data_file(["medieval_medicine_corpus.txt", "mevieval_medicine_corpus.txt"])

figures_dir = voynich_path.parent.parent / "figures" if voynich_path.parent.name == "data" else voynich_path.parent / "figures"
figures_dir.mkdir(parents=True, exist_ok=True)

with open(latin_path, "r", encoding="utf-8", errors="ignore") as f:
    latin_corpus = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", f.read().lower())).strip()

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

voynich_lines = []
voynich_words = []

with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            text = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            words = [w for w in re.split(r"[.,\s]+", text) if w and w.isalpha()]
            if len(words) > 1:
                voynich_lines.append(words)
                voynich_words.extend(words)

transitions = Counter()
suffix_counts = Counter()
prefix_counts = Counter()

for line in voynich_lines:
    for i in range(len(line)):
        suffix_counts[get_suffix(line[i])] += 1
        prefix_counts[get_prefix(line[i])] += 1
        if i < len(line) - 1:
            transitions[(get_suffix(line[i]), get_prefix(line[i + 1]))] += 1

plt.style.use("seaborn-v0_8-whitegrid")

# Figure 1: Boundary Heatmap
top_suffixes = [s for s, _ in suffix_counts.most_common(12)]
top_prefixes = [p for p, _ in prefix_counts.most_common(12)]

mat_12 = pd.DataFrame(0, index=top_suffixes, columns=top_prefixes)
for (suf, pre), count in transitions.items():
    if suf in top_suffixes and pre in top_prefixes:
        mat_12.loc[suf, pre] = count

total_12 = mat_12.values.sum()
expected_12 = np.outer(mat_12.sum(axis=1) / total_12, mat_12.sum(axis=0) / total_12) * total_12
ratio_matrix = mat_12 / (expected_12 + 1e-9)

plt.figure(figsize=(10, 7))
sns.heatmap(
    ratio_matrix, annot=True, fmt=".2f", cmap="coolwarm", center=1.0, vmin=0.2, vmax=2.5,
    cbar_kws={"label": "Observed / Expected Ratio (1.0 = Random)"}
)
plt.title("Voynich Word-Boundary Transition Ratios (Suffix -> Next Prefix)", fontsize=13, fontweight="bold")
plt.xlabel("Subsequent Word Prefix", fontsize=11)
plt.ylabel("Preceding Word Suffix", fontsize=11)
plt.tight_layout()
plt.savefig(figures_dir / "01_boundary_heatmap.png", dpi=300)
plt.close()

# Figure 2: SVD Scree Plot
active_suffixes = [s for s, c in suffix_counts.items() if c >= 10]
active_prefixes = [p for p, c in prefix_counts.items() if c >= 10]

mat_full = pd.DataFrame(0, index=active_suffixes, columns=active_prefixes)
for (s, p), count in transitions.items():
    if s in active_suffixes and p in active_prefixes:
        mat_full.loc[s, p] = count

P = mat_full.values / mat_full.values.sum()
rp = P.sum(axis=1, keepdims=True)
cp = P.sum(axis=0, keepdims=True)
norm_mat = (P - rp @ cp) / np.sqrt(rp @ cp + 1e-12)

U, S, Vt = np.linalg.svd(norm_mat, full_matrices=False)
var_ratios = (S ** 2) / np.sum(S ** 2) * 100
cum_var = np.cumsum(var_ratios)

plt.figure(figsize=(10, 5.5))
x_axis = range(1, 11)
plt.bar(x_axis, var_ratios[:10], color="#4C72B0", alpha=0.85, label="Individual State Variance (%)")
plt.plot(x_axis, cum_var[:10], color="#C44E52", marker="o", linewidth=2.5, label="Cumulative Explained Variance (%)")
plt.axvline(x=5, color="#2E8B57", linestyle="--", linewidth=2, label="5 Vowel States Boundary (A, E, I, O, U)")
plt.title("Normalized Boundary Variance Explained by Latent States (SVD Scree Plot)", fontsize=12, fontweight="bold")
plt.xlabel("Number of Latent Cipher Tables / States (Dimensions)", fontsize=11)
plt.ylabel("Explained Variance (%)", fontsize=11)
plt.xticks(x_axis)
plt.ylim(0, 105)
plt.legend()
plt.tight_layout()
plt.savefig(figures_dir / "02_svd_5_states_elbow.png", dpi=300)
plt.close()

# Figure 3: Zipf Alignment
voy_counts = Counter(voynich_words)
merged_latin = latin_corpus[:220000].replace(" ", "")
blocks = re.findall(r"[aeiou]+|[^aeiou]+", merged_latin)

raw_consonants = [b for b in re.split(r"[aeiou]+", merged_latin) if b][:len(voynich_words)]
raw_counts = Counter(raw_consonants)

contextual_clusters = []
for i, block in enumerate(blocks):
    if not set(block).issubset(set("aeiou")):
        left_v = blocks[i - 1][-1] if (i - 1 >= 0 and set(blocks[i - 1]).issubset(set("aeiou"))) else "BOS"
        right_v = blocks[i + 1][0] if (i + 1 < len(blocks) and set(blocks[i + 1]).issubset(set("aeiou"))) else "BOS"
        contextual_clusters.append(f"{left_v}_{block}_{right_v}")
        if len(contextual_clusters) >= len(voynich_words):
            break

contextual_counts = Counter(contextual_clusters)

plt.figure(figsize=(10, 5.5))
for label, counts, color in [
    (f"Actual Voynich Words (Unique: {len(voy_counts):,})", voy_counts, "#C44E52"),
    (f"Vowel-Stripped Latin Clusters (Unique: {len(raw_counts):,})", raw_counts, "#8C8C8C"),
    (f"5x5 Vowel-Context Latin Model (Unique: {len(contextual_counts):,})", contextual_counts, "#1E90FF")
]:
    freqs = sorted(counts.values(), reverse=True)
    pcts = [f / sum(freqs) * 100 for f in freqs]
    plt.loglog(range(1, len(pcts) + 1), pcts, linewidth=2.5, label=label, color=color)

plt.title("Zipf's Law Alignment: Voynich Vocabulary vs. 5x5 Vowel-Context Latin", fontsize=12, fontweight="bold")
plt.xlabel("Frequency Rank (Log Scale)", fontsize=11)
plt.ylabel("Relative Frequency (% - Log Scale)", fontsize=11)
plt.grid(True, which="both", alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(figures_dir / "03_zipf_contextual_fit.png", dpi=300)
plt.close()

print("All figures generated successfully in /figures.")
