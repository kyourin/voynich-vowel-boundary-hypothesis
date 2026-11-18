import os
import re
import math
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

pure_latin_path = find_data("pure_latin_corpus.txt")

with open(pure_latin_path, "r", encoding="utf-8", errors="ignore") as f:
    latin_words = re.findall(r"[a-z]+", f.read().lower())

word_freq = Counter(latin_words)
bigram_freq = Counter(zip(latin_words[:-1], latin_words[1:]))
tot_words = sum(word_freq.values())

cseq_to_words = defaultdict(list)
for w, cnt in word_freq.items():
    if cnt >= 2:
        c_blocks = tuple(re.findall(r"[^aeiou]+", w))
        if 1 <= len(c_blocks) <= 6:
            cseq_to_words[c_blocks].append((w, cnt))

for sk in cseq_to_words:
    cseq_to_words[sk].sort(key=lambda item: item[-1], reverse=True)
    cseq_to_words[sk] = cseq_to_words[sk][:6]

def bigram_logp(w1, w2):
    c1 = word_freq[w1]
    c12 = bigram_freq[(w1, w2)]
    if c12 > 0:
        return math.log((c12 + 0.5) / (c1 + 10.0)) + 2.5
    return math.log(0.05 / (c1 + 50.0))

def restore_latin_sentence(c_list):
    n = len(c_list)
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

    return " ".join(reversed(words_out))

TARGET_SKELETONS = [
    ("f103r.36,+P0", "chedy okeedy qokeedy qokeey shdy otey qokeey", ["s", "c", "s", "t", "s", "n", "t"]),
    ("f103r.39,+P0", "ykeedy qokeey lsheey qotal shedy oteey", ["s", "t", "r", "r", "p", "p"]),
    ("f103r.4,+P0 ", "ychedy qokedy okedy qokeey okey chdar ol", ["t", "r", "n", "t", "r", "n", "m"]),
    ("f103r.10,+P0", "daiin ol oain okeol chol okam chety shedy otaiin shedy teolshy oteedy sor ain", ["s", "m", "v", "m", "t", "l", "l", "p", "s", "p", "r", "s", "m", "l"]),
    ("f103r.43,+P0", "tar cheal ol sheey qotal sheal qokal sheedy", ["s", "c", "m", "m", "r", "r", "s", "n"]),
    ("f103r.46,+P0", "chol keey qokeey cheol chorol shedy qokeey qokeey ol loiin", ["t", "p", "t", "n", "t", "p", "t", "t", "m", "n"]),
    ("f103r.9,+P0 ", "ar cheal okeey shey lkaiin shey ... otaiin shedy otey l dy", ["s", "c", "t", "x", "s", "x", "s", "p", "n", "s", "t"]),
    ("f103r.32,+P0", "okeey shedy qokedy qokal ... otedy shcthy oraiin", ["t", "p", "r", "s", "m", "n", "m"])
]

print("=" * 94)
print("f103r PRESCRIPTION LINES — VITERBI VOWEL AND GRAMMAR RESTORATION")
print("=" * 94)

for tag, voy_str, c_seq in TARGET_SKELETONS:
    restored = restore_latin_sentence(c_seq)
    print(f"\n[{tag}]")
    print(f"  Voynich  : {voy_str}")
    print(f"  Ünsüzler : {' - '.join(c_seq)}")
    print(f"  Latince  : {restored}")
