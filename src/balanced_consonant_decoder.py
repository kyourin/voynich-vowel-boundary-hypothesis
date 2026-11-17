import os
import re
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

# 1. Külliyattaki gerçek ünsüz frekans oranlarını (kapasite tavanı için) ve kelime iskeletlerini çıkar
with open(pure_latin_path, "r", encoding="utf-8", errors="ignore") as f:
    latin_words = re.findall(r"[a-z]+", f.read().lower())

word_freq = Counter(latin_words)
latin_c_counts = Counter()
skel_dict = defaultdict(list)

for w, c in word_freq.items():
    if c >= 3 and len(w) >= 3:
        sk = tuple(re.findall(r"[^aeiou]+", w))
        for blk in sk:
            latin_c_counts[blk] += c
        if 2 <= len(sk) <= 5:
            skel_dict[sk].append((w, c))

# Her ünsüz iskeleti için en sık 3 gerçek Latince kelimeyi tut
for sk in skel_dict:
    skel_dict[sk].sort(key=lambda item: item[1], reverse=True)
    skel_dict[sk] = skel_dict[sk][:3]

tot_latin_c = sum(latin_c_counts.values())
max_c_share = {c: (cnt / tot_latin_c) * 1.25 for c, cnt in latin_c_counts.items()}

# 2. Tüm Voynich metnini yükle ve kelime frekanslarını hesapla
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
                if len(words) >= 4:
                    all_paragraphs.append((tag, words))
                    voy_word_freq.update(words)

tot_voy_tokens = sum(voy_word_freq.values())

# 3. Sıfır tahminli 3x tekrar çekirdek anahtarı
CORE_KEY = {
    "qokedy": "r",
    "qokeey": "t",
    "or": "n",
    "qokeedy": "s",
    "ytaiin": "m",
    "qotey": "st",
    "oteey": "p"
}

# 4. Kapasite dengeli (yığılma önleyici) 3 turlu ünsüz çözücü
for rnd in range(1, 4):
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

    added = 0
    for (vw, cv), sc in votes.most_common():
        if vw in CORE_KEY or sc < 400:
            continue
        projected_share = (used_c_tokens[cv] + voy_word_freq[vw]) / tot_voy_tokens
        if projected_share <= max_c_share.get(cv, 0.05):
            CORE_KEY[vw] = cv
            used_c_tokens[cv] += voy_word_freq[vw]
            added += 1

    print(f"[Tur {rnd}/3] Yeni Eklenen Dengeli Anahtar: {added} | Toplam Anahtar: {len(CORE_KEY)}", flush=True)

# 5. f103r Reçete Sayfasında Kapasite Dengeli İskelet + Sözlük Eşleşmeleri
print("\n" + "=" * 94)
print("KAPASİTE DENGELİ ANAHTARLA f103r REÇETE SAYFASI OKUMA DENEMESİ")
print("=" * 94)

for tag, ws in all_paragraphs:
    if tag.startswith("f103r."):
        known_cnt = sum(1 for w in ws[:14] if w in CORE_KEY)
        if known_cnt >= 6:
            mapped = [f"{w}({CORE_KEY.get(w, '?')})" for w in ws[:14]]
            c_only = [CORE_KEY.get(w, "?") for w in ws[:14]]
            
            found_words = []
            for k in range(len(c_only) - 2):
                sub3 = tuple(c_only[k:k+3])
                if "?" not in sub3 and sub3 in skel_dict:
                    best_w, best_cnt = next(iter(skel_dict[sub3]))
                    found_words.append(f"{'-'.join(sub3)} => ('{best_w}', {best_cnt})")
            
            print(f"\n[{tag:<10}] ({known_cnt}/14 bilinen)")
            print(f"  İskelet : {' '.join(mapped)}")
            if found_words:
                print(f"  Adaylar : {' | '.join(found_words[:4])}")
