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
    scores_by_id = {}

    for entry in entries:
        emb = entry.get("embedding")
        if not emb:
            continue
        score = cosine_similarity(embedding, emb)
        entity_id = entry.get("id")
        if entity_id:
            if entity_id not in scores_by_id or score > scores_by_id[entity_id][0]:
                scores_by_id[entity_id] = (score, entry)
        elif score > best_score:
            best_score = score
            best = entry

    if scores_by_id:
        for score, entry in scores_by_id.values():
            if score > best_score:
                best_score = score
                best = entry

    return best, best_score
