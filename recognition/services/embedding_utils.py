import numpy as np


def cosine_similarity(a, b):
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def best_match(embedding, entries):
    best = None
    best_score = 0.0
    for entry in entries:
        emb = entry.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(embedding, emb)
        if score > best_score:
            best_score = score
            best = entry
    return best, best_score
