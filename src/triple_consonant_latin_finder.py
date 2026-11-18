import os
import re
from collections import Counter

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

print("=" * 90)
print("1. LINES IN THE VOYNICH MANUSCRIPT WHERE THE SAME WORD IS REPEATED THREE TIMES IN A ROW")
print("=" * 90)

voy_triples = []
with open(voynich_path, "r", encoding="utf-8", errors="ignore") as f:
    for line in f:
        match = re.match(r"^<([^>]+)>\s+(.*)$", line.strip())
        if match and not line.startswith("#"):
            tag = match.group(1)
            clean = re.sub(r"\[([^:\]]+):[^\]]+\]|<[^>]+>|[!?*%'\"\{\};:-]", "", match.group(2))
            words = [w for w in re.split(r"[.,\s]+", clean) if w and w.isalpha()]

            i = 0
            while i < len(words) - 2:
                if words[i] == words[i + 1] == words[i + 2]:
                    run_len = 3
                    while i + run_len < len(words) and words[i + run_len] == words[i]:
                        run_len += 1
                    w = words[i]
                    voy_triples.append((tag, w, words))
                    highlighted = " ".join(f"[{tok.upper()}]" if tok == w else tok for tok in words)
                    print(f"  [{tag:<13}] ({run_len}x '{w}') -> {highlighted}")
                    i += run_len
                else:
                    i += 1

with open(pure_latin_path, "r", encoding="utf-8", errors="ignore") as f:
    text = re.sub(r"[^a-z\s]", " ", f.read().lower())

words = text.split()

single_word_triples = Counter()
for w in words:
    if len(w) >= 5:
        blocks = re.findall(r"[aeiou]+|[^aeiou]+", w)
        c_blocks = [b for b in blocks if not set(b).issubset(set("aeiou"))]
        for i in range(len(c_blocks) - 2):
            if c_blocks[i] == c_blocks[i + 1] == c_blocks[i + 2]:
                single_word_triples[(w, c_blocks[i])] += 1

print("\n" + "=" * 90)
print("2. WORDS IN LATIN IN WHICH THE SAME CONSONANT IS REPEATED 3 TIMES (v-x-v-x-v-x)")
print("=" * 90)
for (w, x), cnt in single_word_triples.most_common(25):
    print(f"  Word: '{w:<16}' (n={cnt:3d})  -->  Recurring Fixed Consonant (x): '{x}'")

phrase_triples = Counter()

for i in range(len(words) - 2):
    phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
    merged = "".join(words[i:i+3])
    blocks = re.findall(r"[aeiou]+|[^aeiou]+", merged)
    c_blocks = [b for b in blocks if not set(b).issubset(set("aeiou"))]
    for k in range(len(c_blocks) - 2):
        if c_blocks[k] == c_blocks[k + 1] == c_blocks[k + 2]:
            if len(words[i]) >= 2 and len(words[i+1]) >= 2:
                phrase_triples[(c_blocks[k], phrase)] += 1

print("\n" + "=" * 90)
print("3. REPETITIONS OF 'v-x-v-x-v-x' IN SEQUENTIAL 2–3 WORD AUTHENTIC LATIN PHRASES")
print("=" * 90)
for (x, phr), cnt in phrase_triples.most_common(30):
    print(f"  Consonant (x='{x:<2}'): '{phr:<32}' (n={cnt:2d})")
