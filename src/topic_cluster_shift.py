import re
from pathlib import Path
from collections import Counter

def find_latin_corpus():
    root = Path.cwd()
    if root.name == "src":
        root = root.parent
    for name in ["medieval_corpus.txt", "mevieval_corpus.txt"]:
        for folder in [root / "data", root]:
            target = folder / name
            if target.exists():
                return target
    raise FileNotFoundError("Missing data/medieval_corpus.txt")

latin_path = find_latin_corpus()
with open(latin_path, "r", encoding="utf-8", errors="ignore") as f:
    corpus_text = re.sub(r"\s+", " ", re.sub(r"[^a-z\s]", " ", f.read().lower())).strip()

words = corpus_text.split()

BOTANICAL_KEYS = {"herba", "radix", "folia", "folium", "flos", "semen", "aqua", "oleum", "vinum", "mel", "melle", "decocta", "trita", "morbus", "dolor", "corpus", "sanguis", "febris", "medicina"}
ASTRO_KEYS = {"stella", "stellae", "stellarum", "sol", "luna", "caelum", "caeli", "signum", "signa", "zodiacus", "planetis", "planetae", "aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricornus", "aquarius", "pisces", "cursus", "motus", "orbis"}

botanical_chunks, astro_chunks = [], []

for i in range(0, len(words) - 25, 25):
    chunk = words[i:i + 25]
    chunk_set = set(chunk)
    b_score = len(chunk_set & BOTANICAL_KEYS)
    a_score = len(chunk_set & ASTRO_KEYS)
    if b_score > a_score and b_score >= 1:
        botanical_chunks.append("".join(chunk))
    elif a_score > b_score and a_score >= 1:
        astro_chunks.append("".join(chunk))

def get_cluster_stats(chunks):
    multi_clusters = Counter()
    contextual_clusters = Counter()
    for text in chunks:
        blocks = re.findall(r"[aeiou]+|[^aeiou]+", text)
        for idx, b in enumerate(blocks):
            if not set(b).issubset(set("aeiou")):
                if len(b) >= 2:
                    multi_clusters[b] += 1
                left_v = blocks[idx - 1][-1] if (idx - 1 >= 0 and set(blocks[idx - 1]).issubset(set("aeiou"))) else "BOS"
                right_v = blocks[idx + 1] if (idx + 1 < len(blocks) and set(blocks[idx + 1]).issubset(set("aeiou"))) else "BOS"
                contextual_clusters[f"{left_v}_{b}_{right_v}"] += 1
    return multi_clusters, contextual_clusters

bot_multi, bot_ctx = get_cluster_stats(botanical_chunks)
ast_multi, ast_ctx = get_cluster_stats(astro_chunks)

tot_bot, tot_ast = sum(bot_multi.values()), sum(ast_multi.values())
enrichment = []
for c in set(bot_multi.keys()) | set(ast_multi.keys()):
    if bot_multi[c] + ast_multi[c] >= 30:
        ratio = ((bot_multi[c] + 1) / tot_bot) / ((ast_multi[c] + 1) / tot_ast)
        enrichment.append((c, bot_multi[c], ast_multi[c], ratio))

enrichment.sort(key=lambda x: x[3], reverse=True)
print("Top Botanical Multi-Consonant Clusters:", enrichment[:5])
print("Top Astronomical Multi-Consonant Clusters:", sorted(enrichment, key=lambda x: x[3])[:5])
